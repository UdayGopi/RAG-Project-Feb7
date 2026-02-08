# 🚀 Deployment Guide

Complete guide for deploying the RAG application to various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [AWS Deployment](#aws-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Scaling & Optimization](#scaling--optimization)

---

## Prerequisites

### Required
- Python 3.9+
- pip or conda
- Git

### For Cloud Deployment
- AWS Account (for S3, EC2, Lambda)
- AWS CLI configured
- Docker (optional, but recommended)

### For Production
- Domain name (optional)
- SSL certificate
- Load balancer (for high traffic)

---

## Local Development

### 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd Rag-Project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:

```env
# Minimum required configuration
GROQ_API_KEY=your_actual_api_key_here
SECRET_KEY=your_random_secret_key

# Use local storage for development
STORAGE_BACKEND=local
```

### 3. Initialize Database

```bash
python -c "from app import app; app.run(debug=False, port=5001)"
# Press Ctrl+C after server starts (database will be created)
```

### 4. Run Development Server

```bash
# Standard Flask
python app.py

# With auto-reload
FLASK_DEBUG=1 python app.py
```

Access at: `http://localhost:5001`

---

## AWS Deployment

### Architecture Overview

```
┌─────────────┐      ┌──────────┐      ┌─────────────┐
│   Users     │─────>│   ALB    │─────>│  EC2/ECS    │
└─────────────┘      └──────────┘      │  (App)      │
                                        └──────┬──────┘
                                               │
                     ┌─────────────────────────┼─────────┐
                     │                         │         │
                  ┌──▼───┐                 ┌──▼──┐  ┌──▼───┐
                  │  S3  │                 │ RDS │  │Lambda│
                  │(Docs)│                 │(DB) │  │(Opt) │
                  └──────┘                 └─────┘  └──────┘
```

### Option 1: EC2 Deployment (Recommended for starting)

#### Step 1: Create S3 Bucket

```bash
# Create bucket for documents
aws s3 mb s3://your-rag-documents --region us-east-1

# Enable versioning (recommended)
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

#### Step 2: Create IAM Role

Create IAM role with this policy:

```json
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
```

#### Step 3: Launch EC2 Instance

```bash
# Launch Ubuntu instance (t3.medium recommended)
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --iam-instance-profile Name=RAGAppRole \
  --user-data file://scripts/ec2-user-data.sh
```

#### Step 4: Setup on EC2

SSH into instance:

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Nginx
sudo apt install nginx -y

# Clone repository
git clone <your-repo> /home/ubuntu/rag-app
cd /home/ubuntu/rag-app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server

# Configure environment
cp .env.example .env
nano .env  # Edit configuration
```

Edit `.env` for production:

```env
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-random-key>

# Use AWS S3
STORAGE_BACKEND=s3
S3_BUCKET=your-rag-documents
AWS_REGION=us-east-1
# Leave AWS keys empty to use IAM role

# Production LLM (optional upgrade)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_openai_key
```

#### Step 5: Configure Gunicorn

Create `/home/ubuntu/rag-app/gunicorn_config.py`:

```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 5

# Logging
accesslog = "/home/ubuntu/rag-app/logs/access.log"
errorlog = "/home/ubuntu/rag-app/logs/error.log"
loglevel = "info"
```

#### Step 6: Create Systemd Service

Create `/etc/systemd/system/rag-app.service`:

```ini
[Unit]
Description=RAG Application
After=network.target

[Service]
Type=notify
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/rag-app
Environment="PATH=/home/ubuntu/rag-app/venv/bin"
ExecStart=/home/ubuntu/rag-app/venv/bin/gunicorn \
  --config gunicorn_config.py \
  app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-app
sudo systemctl start rag-app
sudo systemctl status rag-app
```

#### Step 7: Configure Nginx

Create `/etc/nginx/sites-available/rag-app`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # or EC2 public IP

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location /static/ {
        alias /home/ubuntu/rag-app/static/;
        expires 30d;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/rag-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 8: SSL with Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo systemctl status certbot.timer
```

### Option 2: ECS with Docker (Scalable)

#### Step 1: Create Docker Image

Already provided in root `Dockerfile`. Build and push:

```bash
# Build image
docker build -t rag-app:latest .

# Tag for ECR
aws ecr create-repository --repository-name rag-app
docker tag rag-app:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/rag-app:latest

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/rag-app:latest
```

#### Step 2: Create ECS Task Definition

```json
{
  "family": "rag-app",
  "containerDefinitions": [{
    "name": "rag-app",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/rag-app:latest",
    "memory": 2048,
    "cpu": 1024,
    "essential": true,
    "portMappings": [{
      "containerPort": 5001,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"},
      {"name": "STORAGE_BACKEND", "value": "s3"},
      {"name": "S3_BUCKET", "value": "your-rag-documents"}
    ],
    "secrets": [
      {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "GROQ_API_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/rag-app",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }],
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::123456789:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::123456789:role/RAGAppRole"
}
```

#### Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster rag-cluster \
  --service-name rag-service \
  --task-definition rag-app \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=rag-app,containerPort=5001"
```

### Option 3: Lambda (Serverless, Cost-Effective)

Good for low-traffic applications with bursty usage.

```bash
# Package application
pip install -r requirements.txt -t package/
cp -r config core agents models storage utils package/
cp app.py package/lambda_function.py

# Create deployment package
cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --function-name rag-app \
  --runtime python3.11 \
  --role arn:aws:iam::123456789:role/lambda-rag-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://deployment.zip \
  --timeout 300 \
  --memory-size 3008 \
  --environment Variables="{STORAGE_BACKEND=s3,S3_BUCKET=your-rag-documents}"
```

---

## Docker Deployment

### Local Docker

```bash
# Build image
docker build -t rag-app .

# Run container
docker run -d \
  --name rag-app \
  -p 5001:5001 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  rag-app
```

### Docker Compose (with dependencies)

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - STORAGE_BACKEND=local
      - DATABASE_PATH=/app/data/users.db
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app

volumes:
  redis-data:
```

---

## Environment Configuration

### Development
```env
ENVIRONMENT=development
DEBUG=true
STORAGE_BACKEND=local
LOG_LEVEL=DEBUG
```

### Staging
```env
ENVIRONMENT=staging
DEBUG=false
STORAGE_BACKEND=s3
S3_BUCKET=your-rag-staging
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Production
```env
ENVIRONMENT=production
DEBUG=false
STORAGE_BACKEND=s3
S3_BUCKET=your-rag-production
LOG_LEVEL=WARNING
ENABLE_METRICS=true
ENABLE_TRACING=true

# Use production-grade LLM
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Enhanced security
JWT_EXPIRES_MIN=1440  # 24 hours instead of 7 days
```

---

## Scaling & Optimization

### Horizontal Scaling

1. **Load Balancer**: Use AWS ALB or ELB
2. **Auto Scaling**: Configure ECS/EC2 auto-scaling based on CPU/memory
3. **Session Management**: Use Redis for shared sessions

### Caching Strategy

```python
# Enable Redis caching in production
CACHE_ENABLED=true
CACHE_TTL_HOURS=24

# Use Redis instead of in-memory
REDIS_URL=redis://your-redis-endpoint:6379
```

### Database Optimization

For high traffic, migrate from SQLite to PostgreSQL/MySQL:

```env
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### CDN for Static Assets

Serve static files via CloudFront:

```bash
aws cloudfront create-distribution \
  --origin-domain-name your-s3-bucket.s3.amazonaws.com \
  --default-root-object index.html
```

### Monitoring

- **CloudWatch**: Logs, metrics, alarms
- **X-Ray**: Distributed tracing
- **Custom metrics**: Track query latency, retrieval quality

---

## Health Checks & Monitoring

### Health Check Endpoint

Add to `app.py`:

```python
@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "version": settings.APP_VERSION,
        "storage": settings.STORAGE_BACKEND
    }), 200
```

### CloudWatch Alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name rag-app-high-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name Errors \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold
```

---

## Security Best Practices

1. **Never commit `.env` to git** - use `.gitignore`
2. **Use AWS Secrets Manager** for sensitive data
3. **Enable HTTPS** in production
4. **Set up WAF** for DDoS protection
5. **Regular security updates**: `pip install --upgrade -r requirements.txt`
6. **Limit IAM permissions** to minimum required
7. **Enable CloudTrail** for audit logs
8. **Use VPC** for network isolation

---

## Troubleshooting

### Common Issues

**1. Module not found errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**2. S3 permission denied**
```bash
# Check IAM role permissions
aws iam get-role-policy --role-name RAGAppRole --policy-name S3Access
```

**3. Out of memory**
```bash
# Increase instance size or reduce workers
# In gunicorn_config.py:
workers = 2  # Reduce if OOM
```

**4. Slow responses**
```bash
# Check model loading time
# Consider using smaller models or caching
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5  # Lighter model
```

---

## Cost Optimization

- **Use S3 Intelligent-Tiering** for documents
- **Right-size EC2 instances** based on actual usage
- **Use Spot Instances** for non-critical workloads
- **Enable S3 lifecycle policies** to archive old data
- **Monitor API costs** (OpenAI, Groq)
- **Use CloudWatch Logs Insights** instead of storing all logs

---

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. Review CloudWatch logs
3. Check GitHub issues
4. Contact: [your-support-email]
