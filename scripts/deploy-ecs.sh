#!/bin/bash
# ECS Fargate Deployment Script
# Builds, pushes, and deploys Docker image to ECS

set -e  # Exit on error

# ==================== Configuration ====================
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="rag-app"
IMAGE_TAG=${IMAGE_TAG:-latest}
ECS_CLUSTER="rag-cluster"
ECS_SERVICE="rag-app-service"
TASK_DEFINITION="rag-app-production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ECS Fargate Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ==================== Prerequisites Check ====================
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Install: https://aws.amazon.com/cli/${NC}"
    exit 1
fi
echo "✅ AWS CLI found"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Install: https://docker.com${NC}"
    exit 1
fi
echo "✅ Docker found"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi
echo "✅ AWS credentials configured"
echo "   Account ID: $AWS_ACCOUNT_ID"
echo "   Region: $AWS_REGION"
echo ""

# ==================== Create ECR Repository ====================
echo -e "${YELLOW}Step 1: Creating/verifying ECR repository...${NC}"

if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &> /dev/null; then
    echo "Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository \
        --repository-name $ECR_REPOSITORY \
        --region $AWS_REGION \
        --encryption-configuration encryptionType=AES256 \
        --image-scanning-configuration scanOnPush=true \
        --tags Key=Project,Value=RAG-App Key=Environment,Value=Production
    echo "✅ ECR repository created"
else
    echo "✅ ECR repository already exists"
fi

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
echo "   ECR URI: $ECR_URI"
echo ""

# ==================== Docker Login ====================
echo -e "${YELLOW}Step 2: Logging into ECR...${NC}"

aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI
echo "✅ Logged into ECR"
echo ""

# ==================== Build Docker Image ====================
echo -e "${YELLOW}Step 3: Building Docker image (optimized)...${NC}"
echo "This may take 3-5 minutes..."

# Build with default Dockerfile (full app). Use -f Dockerfile.ultralight for small image.
docker build \
    -f Dockerfile \
    -t $ECR_REPOSITORY:$IMAGE_TAG \
    -t $ECR_URI:$IMAGE_TAG \
    -t $ECR_URI:production \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "none") \
    .

echo "✅ Docker image built"

# Show image size
IMAGE_SIZE=$(docker images $ECR_REPOSITORY:$IMAGE_TAG --format "{{.Size}}")
echo "   Image size: $IMAGE_SIZE"
echo ""

# ==================== Scan Image (Optional) ====================
echo -e "${YELLOW}Step 4: Security scan (optional, skip with Ctrl+C)...${NC}"
sleep 2

# Uncomment to enable local scanning with trivy
# if command -v trivy &> /dev/null; then
#     trivy image --severity HIGH,CRITICAL $ECR_REPOSITORY:$IMAGE_TAG
# fi

# ==================== Push to ECR ====================
echo -e "${YELLOW}Step 5: Pushing image to ECR...${NC}"

docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:production

echo "✅ Image pushed to ECR"
echo "   URI: $ECR_URI:$IMAGE_TAG"
echo ""

# ==================== Register Task Definition ====================
echo -e "${YELLOW}Step 6: Registering ECS task definition...${NC}"

# Update task definition with actual values
TASK_DEF_FILE="ecs/task-definition.json"

if [ ! -f "$TASK_DEF_FILE" ]; then
    echo -e "${RED}❌ Task definition not found: $TASK_DEF_FILE${NC}"
    exit 1
fi

# Create temporary task definition with updated values
TEMP_TASK_DEF=$(mktemp)
cat $TASK_DEF_FILE | \
    sed "s|YOUR_ACCOUNT_ID|$AWS_ACCOUNT_ID|g" | \
    sed "s|YOUR_REGION|$AWS_REGION|g" | \
    sed "s|YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/rag-app:latest|$ECR_URI:$IMAGE_TAG|g" \
    > $TEMP_TASK_DEF

# Register task definition
TASK_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file://$TEMP_TASK_DEF \
    --region $AWS_REGION \
    --query 'taskDefinition.revision' \
    --output text)

rm $TEMP_TASK_DEF

echo "✅ Task definition registered"
echo "   Family: $TASK_DEFINITION"
echo "   Revision: $TASK_REVISION"
echo ""

# ==================== Update ECS Service ====================
echo -e "${YELLOW}Step 7: Updating ECS service...${NC}"

# Check if service exists
if aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text 2>/dev/null | grep -q "ACTIVE"; then
    
    echo "Updating existing service..."
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --task-definition $TASK_DEFINITION:$TASK_REVISION \
        --force-new-deployment \
        --region $AWS_REGION \
        --output json > /dev/null
    
    echo "✅ Service updated"
else
    echo "Service doesn't exist. Creating new service..."
    echo "Please create the service using:"
    echo "  aws ecs create-service --cli-input-json file://ecs/service-definition.json"
fi
echo ""

# ==================== Wait for Deployment ====================
echo -e "${YELLOW}Step 8: Waiting for deployment to complete...${NC}"
echo "This may take 2-5 minutes..."

aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

echo "✅ Deployment complete!"
echo ""

# ==================== Get Service Info ====================
echo -e "${YELLOW}Step 9: Getting service information...${NC}"

# Get load balancer URL
LB_DNS=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].loadBalancers[0].targetGroupArn' \
    --output text 2>/dev/null | \
    xargs -I {} aws elbv2 describe-target-groups --target-group-arns {} --region $AWS_REGION --query 'TargetGroups[0].LoadBalancerArns[0]' --output text 2>/dev/null | \
    xargs -I {} aws elbv2 describe-load-balancers --load-balancer-arns {} --region $AWS_REGION --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null)

# Get running tasks count
RUNNING_COUNT=$(aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].runningCount' \
    --output text)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service: $ECS_SERVICE"
echo "Cluster: $ECS_CLUSTER"
echo "Running Tasks: $RUNNING_COUNT"
echo "Image: $ECR_URI:$IMAGE_TAG"
echo ""

if [ ! -z "$LB_DNS" ] && [ "$LB_DNS" != "None" ]; then
    echo "Load Balancer: http://$LB_DNS"
    echo "Health Check: http://$LB_DNS/health"
else
    echo "⚠️  Load balancer not configured"
fi

echo ""
echo "Useful commands:"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE"
echo "  aws ecs list-tasks --cluster $ECS_CLUSTER --service-name $ECS_SERVICE"
echo "  aws logs tail /ecs/rag-app --follow"
echo ""

# ==================== Cleanup Old Images ====================
echo -e "${YELLOW}Cleaning up old ECR images (keeping last 5)...${NC}"

aws ecr list-images \
    --repository-name $ECR_REPOSITORY \
    --region $AWS_REGION \
    --query 'imageIds[?type(imageTag)!=`string`]' \
    --output json | \
    jq -r '.[] | .imageDigest' | \
    tail -n +6 | \
    xargs -I {} aws ecr batch-delete-image \
        --repository-name $ECR_REPOSITORY \
        --region $AWS_REGION \
        --image-ids imageDigest={} 2>/dev/null || true

echo "✅ Cleanup complete"
echo ""
echo -e "${GREEN}All done! 🚀${NC}"
