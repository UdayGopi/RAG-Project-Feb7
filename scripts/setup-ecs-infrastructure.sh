#!/bin/bash
# Setup ECS Fargate infrastructure (VPC, Security Groups, IAM, etc.)

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="rag-app"

echo "🚀 Setting up ECS Fargate infrastructure..."
echo "Region: $AWS_REGION"
echo ""

# ==================== 1. Create VPC (if needed) ====================
echo "Step 1: Checking VPC..."

VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=$PROJECT_NAME-vpc" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --region $AWS_REGION 2>/dev/null)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo "Creating VPC..."
    VPC_ID=$(aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16 \
        --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=$PROJECT_NAME-vpc}]" \
        --region $AWS_REGION \
        --query 'Vpc.VpcId' \
        --output text)
    
    # Enable DNS
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $AWS_REGION
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support --region $AWS_REGION
fi

echo "✅ VPC: $VPC_ID"

# ==================== 2. Create Internet Gateway ====================
echo "Step 2: Checking Internet Gateway..."

IGW_ID=$(aws ec2 describe-internet-gateways \
    --filters "Name=tag:Name,Values=$PROJECT_NAME-igw" \
    --query 'InternetGateways[0].InternetGatewayId' \
    --output text \
    --region $AWS_REGION 2>/dev/null)

if [ "$IGW_ID" == "None" ] || [ -z "$IGW_ID" ]; then
    echo "Creating Internet Gateway..."
    IGW_ID=$(aws ec2 create-internet-gateway \
        --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=$PROJECT_NAME-igw}]" \
        --region $AWS_REGION \
        --query 'InternetGateway.InternetGatewayId' \
        --output text)
    
    aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID --region $AWS_REGION
fi

echo "✅ Internet Gateway: $IGW_ID"

# ==================== 3. Create Subnets ====================
echo "Step 3: Creating subnets..."

# Subnet 1
SUBNET1_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone ${AWS_REGION}a \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-subnet-1}]" \
    --region $AWS_REGION \
    --query 'Subnet.SubnetId' \
    --output text 2>/dev/null || \
    aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-subnet-1" --query 'Subnets[0].SubnetId' --output text --region $AWS_REGION)

# Subnet 2
SUBNET2_ID=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone ${AWS_REGION}b \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=$PROJECT_NAME-subnet-2}]" \
    --region $AWS_REGION \
    --query 'Subnet.SubnetId' \
    --output text 2>/dev/null || \
    aws ec2 describe-subnets --filters "Name=tag:Name,Values=$PROJECT_NAME-subnet-2" --query 'Subnets[0].SubnetId' --output text --region $AWS_REGION)

echo "✅ Subnets: $SUBNET1_ID, $SUBNET2_ID"

# ==================== 4. Create Security Group ====================
echo "Step 4: Creating security group..."

SG_ID=$(aws ec2 create-security-group \
    --group-name $PROJECT_NAME-sg \
    --description "Security group for RAG app" \
    --vpc-id $VPC_ID \
    --region $AWS_REGION \
    --query 'GroupId' \
    --output text 2>/dev/null || \
    aws ec2 describe-security-groups --filters "Name=group-name,Values=$PROJECT_NAME-sg" --query 'SecurityGroups[0].GroupId' --output text --region $AWS_REGION)

# Allow HTTP from anywhere (for ALB)
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 5001 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION 2>/dev/null || true

echo "✅ Security Group: $SG_ID"

# ==================== 5. Create ECS Cluster ====================
echo "Step 5: Creating ECS cluster..."

aws ecs create-cluster \
    --cluster-name rag-cluster \
    --region $AWS_REGION \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
    2>/dev/null || echo "Cluster already exists"

echo "✅ ECS Cluster: rag-cluster"

# ==================== 6. Create IAM Roles ====================
echo "Step 6: Creating IAM roles..."

# Task Execution Role
cat > /tmp/ecs-task-execution-role.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
    --role-name ecsTaskExecutionRole \
    --assume-role-policy-document file:///tmp/ecs-task-execution-role.json \
    2>/dev/null || echo "Execution role already exists"

aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    2>/dev/null || true

# Task Role (for S3, Secrets Manager)
cat > /tmp/rag-task-role.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
    --role-name rag-app-task-role \
    --assume-role-policy-document file:///tmp/rag-task-role.json \
    2>/dev/null || echo "Task role already exists"

# Attach S3 policy
cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-rag-documents",
        "arn:aws:s3:::your-rag-documents/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name rag-app-task-role \
    --policy-name S3Access \
    --policy-document file:///tmp/s3-policy.json \
    2>/dev/null || true

echo "✅ IAM Roles created"

# ==================== 7. Create CloudWatch Log Group ====================
echo "Step 7: Creating CloudWatch log group..."

aws logs create-log-group \
    --log-group-name /ecs/rag-app \
    --region $AWS_REGION \
    2>/dev/null || echo "Log group already exists"

echo "✅ CloudWatch Log Group: /ecs/rag-app"

# ==================== Summary ====================
echo ""
echo "=========================================="
echo "✅ Infrastructure setup complete!"
echo "=========================================="
echo ""
echo "Resources created:"
echo "  VPC ID: $VPC_ID"
echo "  Subnets: $SUBNET1_ID, $SUBNET2_ID"
echo "  Security Group: $SG_ID"
echo "  ECS Cluster: rag-cluster"
echo ""
echo "Next steps:"
echo "1. Update ecs/service-definition.json with:"
echo "   - subnets: $SUBNET1_ID, $SUBNET2_ID"
echo "   - securityGroups: $SG_ID"
echo ""
echo "2. Store secrets in AWS Secrets Manager:"
echo "   aws secretsmanager create-secret --name rag-app/groq-api-key --secret-string 'your_key'"
echo "   aws secretsmanager create-secret --name rag-app/secret-key --secret-string 'your_secret'"
echo "   aws secretsmanager create-secret --name rag-app/jwt-secret --secret-string 'your_jwt_secret'"
echo ""
echo "3. Run deployment:"
echo "   bash scripts/deploy-ecs.sh"
echo ""
