#!/bin/bash
# Ultra-lightweight ECS deployment (<300MB image)
# Uses API-based models instead of local ML libraries

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="rag-app-ultralight"
IMAGE_TAG=${IMAGE_TAG:-latest}
ECS_CLUSTER="rag-cluster"
ECS_SERVICE="rag-app-service"
TASK_DEFINITION="rag-app-ultralight"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Ultra-Lightweight ECS Deployment${NC}"
echo -e "${GREEN}  Target: <300MB Docker image${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Prerequisites check
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }
echo "✅ Prerequisites met"
echo ""

# Create ECR repository
echo -e "${YELLOW}Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &>/dev/null || \
aws ecr create-repository \
    --repository-name $ECR_REPOSITORY \
    --region $AWS_REGION \
    --encryption-configuration encryptionType=AES256 \
    --image-scanning-configuration scanOnPush=true

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
echo "✅ ECR: $ECR_URI"
echo ""

# Docker login
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI
echo "✅ Logged in"
echo ""

# Build ultra-lightweight image
echo -e "${YELLOW}Building ultra-lightweight image...${NC}"
echo -e "${BLUE}This uses Alpine Linux + API-based models${NC}"
echo -e "${BLUE}Target size: <300MB (vs 1.2GB standard)${NC}"
echo ""

docker build \
    -f Dockerfile.ultralight \
    -t $ECR_REPOSITORY:$IMAGE_TAG \
    -t $ECR_URI:$IMAGE_TAG \
    -t $ECR_URI:ultralight \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    .

echo "✅ Image built"

# Check image size
IMAGE_SIZE=$(docker images $ECR_REPOSITORY:$IMAGE_TAG --format "{{.Size}}")
echo ""
echo -e "${GREEN}📦 Image size: $IMAGE_SIZE${NC}"

# Verify size is under target
SIZE_MB=$(docker images $ECR_REPOSITORY:$IMAGE_TAG --format "{{.Size}}" | grep -oE '[0-9]+' | head -1)
if [ "$SIZE_MB" -gt 300 ]; then
    echo -e "${YELLOW}⚠️  Warning: Image is ${SIZE_MB}MB (target: <300MB)${NC}"
    echo "Consider:"
    echo "  - Removing more dependencies"
    echo "  - Using --squash flag"
    echo "  - Checking .dockerignore"
else
    echo -e "${GREEN}✅ Size target met! (${SIZE_MB}MB < 300MB)${NC}"
fi
echo ""

# Push to ECR
echo -e "${YELLOW}Pushing to ECR...${NC}"
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:ultralight
echo "✅ Pushed to ECR"
echo ""

# Update task definition
echo -e "${YELLOW}Registering task definition...${NC}"

# Create task definition for ultra-lightweight
cat > /tmp/task-def-ultralight.json <<EOF
{
  "family": "$TASK_DEFINITION",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/rag-app-task-role",
  "containerDefinitions": [
    {
      "name": "rag-app",
      "image": "$ECR_URI:$IMAGE_TAG",
      "essential": true,
      "portMappings": [{"containerPort": 5001}],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "STORAGE_BACKEND", "value": "s3"},
        {"name": "EMBEDDING_PROVIDER", "value": "openai"},
        {"name": "EMBEDDING_MODEL", "value": "text-embedding-3-small"},
        {"name": "LLM_PROVIDER", "value": "groq"},
        {"name": "RETRIEVAL_MODE", "value": "semantic"},
        {"name": "LOG_LEVEL", "value": "WARNING"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:rag-app/secret-key"},
        {"name": "GROQ_API_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:rag-app/groq-api-key"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:rag-app/openai-api-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/rag-app-ultralight",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5001/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 40
      }
    }
  ]
}
EOF

TASK_REVISION=$(aws ecs register-task-definition \
    --cli-input-json file:///tmp/task-def-ultralight.json \
    --region $AWS_REGION \
    --query 'taskDefinition.revision' \
    --output text)

rm /tmp/task-def-ultralight.json

echo "✅ Task definition registered: $TASK_DEFINITION:$TASK_REVISION"
echo ""

# Update service
echo -e "${YELLOW}Updating ECS service...${NC}"

if aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION \
    --query 'services[0].status' \
    --output text 2>/dev/null | grep -q "ACTIVE"; then
    
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --task-definition $TASK_DEFINITION:$TASK_REVISION \
        --force-new-deployment \
        --region $AWS_REGION \
        --output json > /dev/null
    
    echo "✅ Service updated"
else
    echo "⚠️  Service doesn't exist. Create it first."
fi
echo ""

# Wait for deployment
echo -e "${YELLOW}Waiting for deployment...${NC}"
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image: $ECR_URI:$IMAGE_TAG"
echo "Size: $IMAGE_SIZE"
echo "Architecture: Alpine + API-based models"
echo ""
echo "⚠️  Important: This image requires:"
echo "  - OPENAI_API_KEY or COHERE_API_KEY"
echo "  - API costs: ~\$0.10-0.20 per 1M tokens"
echo ""
echo "Trade-off:"
echo "  ✅ 75% smaller image (300MB vs 1.2GB)"
echo "  ✅ Faster deployments"
echo "  ❌ Requires API calls for embeddings"
echo "  ❌ Small ongoing API costs"
echo ""
