#!/bin/bash
# Build ultra-lightweight Docker image (<300MB)

set -e

echo "🚀 Building ultra-lightweight Docker image"
echo "Target: <300MB"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
IMAGE_NAME="rag-app"
TAG="ultralight"

echo -e "${YELLOW}Step 1: Building image...${NC}"

# Build with ultra-light Dockerfile
docker build \
    -f Dockerfile.ultralight \
    -t $IMAGE_NAME:$TAG \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    .

echo -e "${GREEN}✅ Build complete${NC}"
echo ""

# Show image size
echo -e "${YELLOW}Step 2: Checking image size...${NC}"

SIZE=$(docker images $IMAGE_NAME:$TAG --format "{{.Size}}")
SIZE_MB=$(docker images $IMAGE_NAME:$TAG --format "{{.Size}}" | sed 's/MB//' | awk '{print int($1)}')

echo "Image: $IMAGE_NAME:$TAG"
echo "Size: $SIZE"

if [ "$SIZE_MB" -lt 300 ]; then
    echo -e "${GREEN}✅ SUCCESS! Image is under 300MB${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: Image is larger than 300MB${NC}"
fi

echo ""

# Detailed breakdown
echo -e "${YELLOW}Step 3: Image analysis...${NC}"

docker history $IMAGE_NAME:$TAG --no-trunc | head -20

echo ""
echo "Layers summary:"
docker history $IMAGE_NAME:$TAG --format "{{.Size}}\t{{.CreatedBy}}" | head -10

echo ""

# Test run (optional)
echo -e "${YELLOW}Step 4: Testing image (optional, Ctrl+C to skip)...${NC}"
sleep 2

echo "Starting container for health check..."

# Create test env file
cat > /tmp/test.env <<EOF
GROQ_API_KEY=test_key
OPENAI_API_KEY=test_key
SECRET_KEY=test_secret
STORAGE_BACKEND=local
VECTOR_STORE=local
EMBEDDING_PROVIDER=openai
EOF

# Start container
CONTAINER_ID=$(docker run -d \
    --name rag-test \
    --env-file /tmp/test.env \
    -p 5002:5001 \
    $IMAGE_NAME:$TAG)

echo "Container started: $CONTAINER_ID"
echo "Waiting 10 seconds for startup..."
sleep 10

# Test health endpoint
if curl -f http://localhost:5002/health 2>/dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed (might need valid API keys)${NC}"
fi

# Cleanup
docker stop rag-test >/dev/null 2>&1
docker rm rag-test >/dev/null 2>&1
rm /tmp/test.env

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Build Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Image: $IMAGE_NAME:$TAG"
echo "Size: $SIZE"
echo ""
echo "To run locally:"
echo "  docker run -p 5001:5001 --env-file .env.ultralight $IMAGE_NAME:$TAG"
echo ""
echo "To push to ECR:"
echo "  export AWS_REGION=us-east-1"
echo "  export AWS_ACCOUNT_ID=\$(aws sts get-caller-identity --query Account --output text)"
echo "  aws ecr get-login-password --region \$AWS_REGION | docker login --username AWS --password-stdin \$AWS_ACCOUNT_ID.dkr.ecr.\$AWS_REGION.amazonaws.com"
echo "  docker tag $IMAGE_NAME:$TAG \$AWS_ACCOUNT_ID.dkr.ecr.\$AWS_REGION.amazonaws.com/rag-app:ultralight"
echo "  docker push \$AWS_ACCOUNT_ID.dkr.ecr.\$AWS_REGION.amazonaws.com/rag-app:ultralight"
echo ""
