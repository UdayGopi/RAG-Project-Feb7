# AWS Deployment Guide (Docker + ECR + App Runner or ECS Fargate)

This guide shows two easy deployment paths on AWS using the included Dockerfile:

- Option A: Amazon ECR + AWS App Runner (simplest managed runtime)
- Option B: Amazon ECR + Amazon ECS (Fargate) behind an Application Load Balancer

Your repository already contains:
- `Dockerfile` (production-ready, Gunicorn server)
- `.dockerignore` (smaller images)
- `requirements.txt` with `gunicorn`

Make sure you have an `.env` locally for dev; do not commit secrets.

## Prerequisites

- AWS account and IAM user with permissions for ECR/App Runner/ECS/IAM/CloudWatch/ALB
- AWS CLI v2 installed and configured: `aws configure`
- Docker installed and running

## Environment variables (required at runtime)

Set these in the AWS service (App Runner or ECS task definition):
- APP_BASE_URL: e.g. `https://your-domain.com` or the service URL
- SECRET_KEY or JWT_SECRET: a strong random value
- GROQ_API_KEY: your key
- GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (optional)
- MS_CLIENT_ID / MS_CLIENT_SECRET (optional)
- PORT: 5001 (App Runner/ECS will route to container port 5001)

If you expose the service on HTTPS with a domain, update your OAuth redirect URIs, e.g.:
- `https://your-domain.com/auth/callback/google`
- `https://your-domain.com/auth/callback/microsoft`

## Build and push image to Amazon ECR

1) Create an ECR repository (one time):
```
aws ecr create-repository --repository-name carepolicy-hub --image-scanning-configuration scanOnPush=true --region <REGION>
```

2) Authenticate Docker to ECR:
```
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com
```

3) Build and push the image:
```
REPO=<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/carepolicy-hub
TAG=v1

docker build -t carepolicy-hub:latest .
docker tag carepolicy-hub:latest $REPO:$TAG

docker push $REPO:$TAG
```

---

## Option A: Deploy with AWS App Runner

1) In AWS Console → App Runner → Create service → From ECR
   - Choose your ECR repository and image tag
   - Specify Port: `5001`
   - CPU/Memory: Start with 1 vCPU / 2GB
   - Auto scaling: default is fine
   - Health check path: `/auth.html`

2) Add Environment variables under Runtime configuration
   - Set `APP_BASE_URL` to the URL that App Runner provides after first deploy (you can update it post-deploy), or your own domain if you map one
   - Add all secrets/keys from the list above

3) Create service. After deploy, note the default App Runner URL.
   - If you later map a custom domain (App Runner supports this), update `APP_BASE_URL`.
   - Update your OAuth redirect URIs to match the final URL.

4) Logging/Monitoring
   - App Runner streams logs to CloudWatch automatically; check for errors in startup or requests.

---

## Option B: Deploy with ECS Fargate

1) Create a Task Definition (Fargate):
   - Container image: `<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/carepolicy-hub:v1`
   - Container port: `5001`
   - Environment: set vars listed above
   - CPU/Memory: start with 0.5 vCPU / 1GB or higher
   - Log configuration: awslogs → `/ecs/carepolicy-hub`

2) Create a Service with Fargate launch type:
   - Desired tasks: 1+ (scale later as needed)
   - Attach to an Application Load Balancer (ALB)
     - Target group: TCP/HTTP to port `5001`
     - Health check path: `/auth.html`
   - Security group: allow inbound 80/443 from Internet

3) Domain & TLS (recommended):
   - In Route 53, create an A/ALIAS to the ALB
   - Use AWS Certificate Manager (ACM) for an SSL cert and attach to the ALB listener on 443
   - After domain works on HTTPS, set `APP_BASE_URL=https://your-domain.com`

4) Autoscaling (optional):
   - Configure ECS Service autoscaling by CPU/Memory or request count via ALB

---

## Post-deploy validation

- Open `https://<your-service>/auth.html`
- Email Sign Up/Sign In flow works; auth cookie persists; `/` serves the chat page
- `/auth/providers` reflects your configured providers
- If Google/Microsoft OAuth is enabled, ensure redirect URIs match the deployed domain

---

## Cost and scale tips

- App Runner is simplest and auto-scales. Good for ~100 users/day.
- ECS Fargate offers more control and VPC integration.
- Enable CloudWatch log retention and alarms (errors, 5xx)
- SQLite is fine for light usage; consider RDS if you need multi-AZ durability and higher concurrency.

---

## Troubleshooting

- If `/` redirects to `/auth.html` unexpectedly, check cookies arriving from the same domain and `APP_BASE_URL` settings.
- Update OAuth redirect URIs exactly to your production domain.
- For 502/503 behind ALB, verify target health check path `/auth.html` and security groups/subnets.
- For Java errors in Tabula, ensure `default-jre` layer included (present in Dockerfile).
