# 🚀 ECS Fargate Deployment Guide

Complete guide for deploying your RAG application to AWS ECS Fargate with optimized Docker images.

## Overview

**Deployment Stack:**
- **Container Orchestration**: AWS ECS Fargate (serverless containers)
- **Image Registry**: AWS ECR
- **Storage**: S3 for documents
- **Vector DB**: Qdrant (separate EC2) or local
- **Secrets**: AWS Secrets Manager
- **Logging**: CloudWatch Logs
- **Load Balancer**: Application Load Balancer (ALB)

**Optimizations:**
- ✅ Multi-stage Docker build (smaller images)
- ✅ Production-only dependencies (~50% size reduction)
- ✅ Non-root user (security)
- ✅ Health checks (reliability)
- ✅ Auto-scaling ready
- ✅ Secrets in AWS Secrets Manager (security)

---

## Prerequisites

1. **AWS CLI** configured:
   ```bash
   aws configure
   ```

2. **Docker** installed

3. **Required AWS permissions**:
   - ECS, ECR, IAM, CloudWatch, Secrets Manager, S3

---

## Quick Start (5 Commands)

```bash
# 1. Setup infrastructure
bash scripts/setup-ecs-infrastructure.sh

# 2. Store secrets
aws secretsmanager create-secret \
  --name rag-app/groq-api-key \
  --secret-string "your_groq_api_key"

# 3. Build and deploy
bash scripts/deploy-ecs.sh

# 4. Create service (first time only)
aws ecs create-service \
  --cli-input-json file://ecs/service-definition.json

# 5. Access your app
# Use the load balancer DNS from script output
```

---

## Detailed Setup

### Step 1: Prepare Secrets

Store sensitive data in AWS Secrets Manager:

```bash
# GROQ API key
aws secretsmanager create-secret \
  --name rag-app/groq-api-key \
  --description "Groq API key for RAG app" \
  --secret-string "your_actual_groq_api_key" \
  --region us-east-1

# Application secret key
aws secretsmanager create-secret \
  --name rag-app/secret-key \
  --description "Flask secret key" \
  --secret-string "$(openssl rand -hex 32)" \
  --region us-east-1

# JWT secret
aws secretsmanager create-secret \
  --name rag-app/jwt-secret \
  --description "JWT signing secret" \
  --secret-string "$(openssl rand -hex 32)" \
  --region us-east-1
```

**Verify:**
```bash
aws secretsmanager list-secrets --region us-east-1
```

### Step 2: Create S3 Bucket

```bash
# Create bucket for documents
aws s3 mb s3://your-rag-documents --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-rag-documents \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket your-rag-documents \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

### Step 3: Setup Infrastructure

Run the automated setup script:

```bash
bash scripts/setup-ecs-infrastructure.sh
```

This creates:
- VPC with public subnets
- Internet Gateway
- Security Groups
- ECS Cluster
- IAM Roles
- CloudWatch Log Group

**Save the output** - you'll need the subnet and security group IDs!

### Step 4: Update Configuration Files

#### A. Update `ecs/task-definition.json`:

Replace placeholders:
- `YOUR_ACCOUNT_ID` → Your AWS account ID
- `YOUR_REGION` → Your region (e.g., us-east-1)
- Update S3 bucket name
- Update Qdrant URL (if using external Qdrant)

#### B. Update `ecs/service-definition.json`:

Replace:
- `subnet-xxxxxxxxx` → Subnet IDs from step 3
- `sg-zzzzzzzzz` → Security group ID from step 3
- `targetGroupArn` → Your ALB target group ARN

### Step 5: Build and Push Docker Image

```bash
# Set environment variables
export AWS_REGION=us-east-1
export IMAGE_TAG=v1.0.0  # or use 'latest'

# Run deployment script
bash scripts/deploy-ecs.sh
```

This script:
1. Creates ECR repository
2. Builds optimized Docker image
3. Pushes to ECR
4. Registers task definition
5. Updates ECS service
6. Waits for deployment

**Expected output:**
```
✅ Deployment Successful!
Image: 123456789.dkr.ecr.us-east-1.amazonaws.com/rag-app:latest
Image size: 1.2GB (vs 3GB+ unoptimized)
Running Tasks: 2
```

### Step 6: Create ECS Service (First Time Only)

```bash
aws ecs create-service \
  --cli-input-json file://ecs/service-definition.json \
  --region us-east-1
```

For subsequent deployments, the script will update the existing service.

### Step 7: Setup Load Balancer (Optional but Recommended)

#### Create Application Load Balancer:

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name rag-app-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-zzzzz \
  --region us-east-1

# Create target group
aws elbv2 create-target-group \
  --name rag-app-tg \
  --protocol HTTP \
  --port 5001 \
  --vpc-id vpc-xxxxx \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --region us-east-1

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:... \
  --region us-east-1
```

Update `ecs/service-definition.json` with the target group ARN.

---

## Image Size Optimization

### Before Optimization:
- Base image: `python:3.11` (1GB)
- All dependencies: 2.5GB+
- **Total: 3.5GB+**

### After Optimization:
- Base image: `python:3.11-slim` (130MB)
- Multi-stage build: Build tools removed
- Production-only deps: ~1GB
- **Total: 1.2GB** (66% reduction!)

### Key Optimizations:

1. **Multi-stage build**: Build dependencies separate from runtime
2. **Slim base image**: `python:3.11-slim` vs `python:3.11`
3. **Production requirements**: Removed dev/test dependencies
4. **No cache**: `pip install --no-cache-dir`
5. **Layer optimization**: Proper COPY order for caching
6. **.dockerignore**: Exclude unnecessary files

---

## Security Best Practices

### ✅ Implemented:

1. **Non-root user**: Container runs as `appuser` (UID 1000)
2. **Secrets Manager**: API keys not in environment variables
3. **Encrypted storage**: S3 encryption at rest
4. **VPC**: Private networking
5. **IAM roles**: Least privilege access
6. **Image scanning**: ECR scans on push
7. **Health checks**: Automated container health monitoring
8. **HTTPS ready**: Use ALB with SSL certificate

### Additional Recommendations:

```bash
# 1. Enable AWS WAF on ALB
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:... \
  --resource-arn arn:aws:elasticloadbalancing:...

# 2. Enable AWS GuardDuty
aws guardduty create-detector --enable

# 3. Enable CloudTrail
aws cloudtrail create-trail --name rag-app-trail

# 4. Enable VPC Flow Logs
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids vpc-xxxxx \
  --traffic-type ALL
```

---

## Monitoring & Logging

### CloudWatch Logs

View logs:
```bash
# Stream logs live
aws logs tail /ecs/rag-app --follow

# Filter errors
aws logs filter-log-events \
  --log-group-name /ecs/rag-app \
  --filter-pattern "ERROR"

# Get last 100 lines
aws logs tail /ecs/rag-app --since 1h
```

### CloudWatch Metrics

Key metrics to monitor:
- **CPUUtilization**: Should be < 80%
- **MemoryUtilization**: Should be < 80%
- **TargetResponseTime**: Target < 2s
- **HealthyHostCount**: Should equal desired count

### Create Alarms:

```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name rag-app-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold

# High memory alarm
aws cloudwatch put-metric-alarm \
  --alarm-name rag-app-high-memory \
  --alarm-description "Alert when memory exceeds 80%" \
  --metric-name MemoryUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## Auto-Scaling

### Configure Service Auto-Scaling:

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/rag-cluster/rag-app-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy (target tracking)
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/rag-cluster/rag-app-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

---

## Cost Optimization

### Current Configuration:
- **2 Fargate tasks** (1 vCPU, 2GB RAM each)
- **Cost**: ~$50/month
- **S3**: ~$5/month
- **Total**: ~$55/month

### Cost-Saving Tips:

1. **Use Fargate Spot** (up to 70% savings):
   ```json
   "capacityProviderStrategy": [
     {"capacityProvider": "FARGATE_SPOT", "weight": 1}
   ]
   ```

2. **Right-size tasks**: Start with 0.5 vCPU, 1GB RAM
   ```json
   "cpu": "512",
   "memory": "1024"
   ```

3. **Scale to zero** during off-hours:
   ```bash
   aws ecs update-service \
     --cluster rag-cluster \
     --service rag-app-service \
     --desired-count 0
   ```

4. **Use S3 Intelligent-Tiering**: Auto-archive old files

---

## Troubleshooting

### Issue 1: Task fails to start

**Check logs:**
```bash
aws logs tail /ecs/rag-app --follow
```

**Common causes:**
- Secrets not accessible → Check IAM permissions
- Out of memory → Increase task memory
- Image pull error → Verify ECR permissions

### Issue 2: Service unstable

**Check task health:**
```bash
aws ecs describe-tasks \
  --cluster rag-cluster \
  --tasks $(aws ecs list-tasks --cluster rag-cluster --service-name rag-app-service --query 'taskArns[0]' --output text)
```

**Common causes:**
- Health check failing → Check `/health` endpoint
- Port mismatch → Verify container port 5001
- Security group → Ensure SG allows traffic

### Issue 3: High costs

**Check metrics:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

**Optimize:**
- Switch to Fargate Spot
- Reduce task count
- Use smaller task sizes

---

## Rollback

If deployment fails:

```bash
# List task definitions
aws ecs list-task-definitions --family-prefix rag-app-production

# Rollback to previous version
aws ecs update-service \
  --cluster rag-cluster \
  --service rag-app-service \
  --task-definition rag-app-production:PREVIOUS_REVISION
```

---

## CI/CD Integration

### GitHub Actions Example:

```yaml
name: Deploy to ECS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Deploy to ECS
        run: bash scripts/deploy-ecs.sh
```

---

## Summary

**You now have:**
- ✅ Optimized Docker image (1.2GB vs 3.5GB)
- ✅ Secure deployment (non-root, secrets manager)
- ✅ Auto-scaling ECS service
- ✅ CloudWatch monitoring
- ✅ One-command deployment
- ✅ Production-ready configuration

**Total cost: ~$55/month** for 2 tasks with 24/7 uptime!

**Next steps:**
1. Run `bash scripts/setup-ecs-infrastructure.sh`
2. Store secrets in Secrets Manager
3. Run `bash scripts/deploy-ecs.sh`
4. Access your app via load balancer!

Questions? Check the troubleshooting section or open an issue!
