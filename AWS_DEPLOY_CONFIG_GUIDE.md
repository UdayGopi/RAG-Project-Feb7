# AWS Deployment: Docker Image + AWS Services Configuration

This guide explains **what to put in the Docker image** and **what to configure in AWS** when you deploy CarePolicy Hub using AWS services.

---

## Part 1: Docker Image (What You Build)

### 1.1 What Goes IN the Image

| Item | Purpose |
|------|--------|
| **Application code** | `app.py`, `rag_agent.py`, `config/`, `core/`, `agents/`, `storage/`, `models/`, `retrieval/`, `database/`, `api/`, `utils/`, `ingestion/` |
| **Static assets** | `static/` (auth.html, index.html, care-policy-hub.html, etc.) |
| **Default env template** | `.env.example` copied as `.env` (placeholder values only; real values come from AWS) |
| **Python dependencies** | From `requirements.txt` (installed during `docker build`) |
| **Runtime** | Python 3.11, Gunicorn (entrypoint: `gunicorn ... app:app`) |
| **Port** | Container listens on **5001** |

### 1.2 What Does NOT Go in the Image

- **Real secrets** – no `.env` with real API keys or passwords; use AWS Secrets Manager or env vars.
- **Your data** – no `data/`, `documents/`, `chat_history/`, `*.json` (history, cache, schedules); use S3 or volumes.
- **Tests, docs, scripts** – excluded via `.dockerignore` to keep image small.

### 1.3 Optional: React Frontend in the Image

The app serves the React app from `frontend/dist/` at `/app/`. To have it in the image:

- **Option A:** Build locally (`cd frontend && npm run build`), then in Dockerfile add:  
  `COPY frontend/dist/ ./frontend/dist/`
- **Option B:** Add a multi-stage build: Node stage runs `npm ci && npm run build`, then copy `frontend/dist/` into the final stage.

If you don’t add `frontend/dist/`, the `/app/` route will 404 until you serve the built frontend elsewhere (e.g. S3 + CloudFront).

### 1.4 Build and Tag (Local)

```bash
# From project root
docker build -t carepolicy-hub:latest .

# Optional: use ultralight image (smaller, API-only embeddings)
# docker build -f Dockerfile.ultralight -t carepolicy-hub:latest .
```

---

## Part 2: AWS Services You Use

| AWS Service | Role |
|-------------|------|
| **ECR** | Store your Docker image so ECS/App Runner can pull it. |
| **ECS Fargate** or **App Runner** | Run the container (CPU, memory, scaling). |
| **S3** | Store documents, indexes, or other persistent data (when `STORAGE_BACKEND=s3`). |
| **Secrets Manager** | Store secrets (e.g. GROQ_API_KEY, SECRET_KEY, JWT_SECRET); reference from ECS/App Runner. |
| **CloudWatch Logs** | Container logs (automatic with ECS/App Runner). |
| **ALB** (optional) | Load balancer in front of ECS; required if you use ECS with a custom domain. |
| **Route 53** (optional) | Custom domain (e.g. app.yourcompany.com). |
| **ACM** (optional) | SSL certificate for HTTPS. |

---

## Part 3: Configuration in AWS

### 3.1 Amazon ECR (Image Registry)

1. Create repository (once):
   ```bash
   aws ecr create-repository --repository-name carepolicy-hub --image-scanning-configuration scanOnPush=true --region us-east-1
   ```
2. Login and push:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

   docker tag carepolicy-hub:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/carepolicy-hub:v1
   docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/carepolicy-hub:v1
   ```

**Configure:** Nothing else. ECS/App Runner will pull by image URI and tag.

---

### 3.2 AWS Secrets Manager (Secrets)

Create secrets so the container gets them at runtime (no secrets in the image).

```bash
# Replace values with your real ones; use same region as ECS/App Runner (e.g. us-east-1)

# Flask secret
aws secretsmanager create-secret --name carepolicy-hub/secret-key --secret-string "$(openssl rand -hex 32)" --region us-east-1

# JWT secret
aws secretsmanager create-secret --name carepolicy-hub/jwt-secret --secret-string "$(openssl rand -hex 32)" --region us-east-1

# Groq API key (replace with your key)
aws secretsmanager create-secret --name carepolicy-hub/groq-api-key --secret-string "gsk_your_actual_key" --region us-east-1
```

**Configure:** In ECS task definition or App Runner, you will reference these by ARN (see below). For OAuth you can add:

- `carepolicy-hub/google-client-id`
- `carepolicy-hub/google-client-secret`
- `carepolicy-hub/ms-client-id`
- `carepolicy-hub/ms-client-secret`

---

### 3.3 S3 (Document Storage)

Use when `STORAGE_BACKEND=s3`.

1. Create bucket:
   ```bash
   aws s3 mb s3://your-carepolicy-documents --region us-east-1
   ```
2. (Recommended) Enable versioning and encryption (see your existing ECS_DEPLOYMENT.md).
3. Give the ECS task role (or App Runner instance role) permission to read/write this bucket (e.g. `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on `arn:aws:s3:::your-carepolicy-documents`).

**Configure in container:** Set env vars (see 3.5):

- `STORAGE_BACKEND=s3`
- `S3_BUCKET=your-carepolicy-documents`
- `AWS_REGION=us-east-1`  
If the task runs with an IAM role that has access to the bucket, leave `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` unset.

---

### 3.4 IAM Roles (ECS or App Runner)

**ECS Fargate:**

- **Execution role** – Used to pull image from ECR and (optionally) read secrets from Secrets Manager. Standard `ecsTaskExecutionRole` + policy for `secretsmanager:GetSecretValue` for your secret ARNs.
- **Task role** – Used by the app at runtime (e.g. S3, Secrets if you inject them via sidecar). Attach a policy that allows:
  - `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on your S3 bucket.
  - (If you use Secrets Manager from the app) `secretsmanager:GetSecretValue` on your secret ARNs.

**App Runner:**

- Use the default instance role or create one that has S3 (and optionally Secrets Manager) access, and attach it to the App Runner service.

---

### 3.5 Environment Variables (ECS or App Runner)

Set these in the **task definition** (ECS) or **Runtime configuration** (App Runner). Use **environment** for non-sensitive values and **secrets** (or Secrets Manager ARNs) for sensitive ones.

**Required (non-secret):**

| Variable | Example | Notes |
|----------|---------|--------|
| `ENVIRONMENT` | `production` | |
| `DEBUG` | `false` | Must be false in production. |
| `PORT` | `5001` | Container port. |
| `APP_BASE_URL` | `https://your-domain.com` or App Runner default URL | For OAuth redirects and links. |

**Required (secret – use Secrets Manager or env secrets):**

| Variable | Where to set | Notes |
|----------|----------------|--------|
| `SECRET_KEY` | Secrets Manager → reference in task def | Flask secret. |
| `JWT_SECRET` | Secrets Manager → reference in task def | JWT signing. |
| `GROQ_API_KEY` | Secrets Manager → reference in task def | LLM API. |

**Optional – OAuth:**

| Variable | Example |
|----------|--------|
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `MS_CLIENT_ID` | From Azure AD |
| `MS_CLIENT_SECRET` | From Azure AD |

**Optional – S3 (if using S3 storage):**

| Variable | Example |
|----------|--------|
| `STORAGE_BACKEND` | `s3` |
| `S3_BUCKET` | `your-carepolicy-documents` |
| `AWS_REGION` | `us-east-1` |

**Optional – RAG/LLM (defaults often fine):**

| Variable | Example |
|----------|--------|
| `LLM_PROVIDER` | `groq` |
| `LLM_MODEL` | `llama-3.1-8b-instant` |
| `EMBEDDING_PROVIDER` | `huggingface` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `RETRIEVAL_MODE` | `semantic` or `hybrid` |
| `LOG_LEVEL` | `INFO` |

---

### 3.6 ECS Task Definition (Fargate) – Summary

- **Image:** `&lt;ACCOUNT_ID&gt;.dkr.ecr.&lt;REGION&gt;.amazonaws.com/carepolicy-hub:v1`
- **Container port:** 5001
- **CPU / Memory:** e.g. 1024 CPU, 2048 MB
- **Environment:** All non-secret variables from 3.5
- **Secrets:** Map Secrets Manager ARNs to env names, e.g.:
  - `SECRET_KEY` ← `arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:carepolicy-hub/secret-key`
  - `JWT_SECRET` ← `arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:carepolicy-hub/jwt-secret`
  - `GROQ_API_KEY` ← `arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:carepolicy-hub/groq-api-key`
- **Logging:** `awslogs` driver, log group e.g. `/ecs/carepolicy-hub`
- **Health check:** `CMD-SHELL curl -f http://localhost:5001/health || exit 1`

Your repo’s `ecs/task-definition.json` is a template; replace `YOUR_ACCOUNT_ID`, `YOUR_REGION`, bucket name, and secret ARNs with your values.

---

### 3.7 App Runner – Summary

- **Source:** ECR – same image as above.
- **Port:** 5001
- **CPU / Memory:** e.g. 1 vCPU, 2 GB
- **Environment:** Same variables as 3.5; add them in the App Runner console under Runtime → Environment variables. For secrets, you can type values directly (or use Secrets Manager if supported in your region).
- **Health check path:** `/health` or `/auth.html`
- **URL:** Use the default `*.awsapprunner.com` URL as `APP_BASE_URL` until you attach a custom domain.

---

### 3.8 Load Balancer + Domain (ECS Only)

If you use ECS (not App Runner):

1. Create an Application Load Balancer (ALB) in the same VPC as your ECS service.
2. Create a target group (port 5001, protocol HTTP, health check `/health` or `/auth.html`).
3. Add an HTTP/HTTPS listener that forwards to this target group. For HTTPS, attach an ACM certificate.
4. Point your ECS service to this target group.
5. In Route 53, create an A or alias record to the ALB.
6. Set `APP_BASE_URL=https://your-domain.com` in the task definition.
7. In Google/Microsoft OAuth config, set redirect URI to `https://your-domain.com/auth/callback/google` (and same for Microsoft).

---

## Part 4: Quick Checklist

**Docker image**

- [ ] Build with `docker build -t carepolicy-hub:latest .` (or Dockerfile.ultralight if using ultralight).
- [ ] Image includes `app.py`, `rag_agent.py`, and all app packages (no real `.env` or data).
- [ ] (Optional) Include `frontend/dist/` if you serve React from the same container.

**AWS – ECR**

- [ ] Repository created; image pushed with correct tag.

**AWS – Secrets Manager**

- [ ] `SECRET_KEY`, `JWT_SECRET`, `GROQ_API_KEY` created; OAuth secrets if needed.

**AWS – S3**

- [ ] Bucket created; versioning/encryption if required; task/instance role has S3 permissions.

**AWS – ECS or App Runner**

- [ ] Task/Service uses your ECR image and tag.
- [ ] All env vars set (ENVIRONMENT=production, DEBUG=false, PORT=5001, APP_BASE_URL, STORAGE_*, etc.).
- [ ] Secrets wired from Secrets Manager (ECS) or set securely (App Runner).
- [ ] Health check path `/health` or `/auth.html`; port 5001.
- [ ] Logs go to CloudWatch.

**OAuth (if used)**

- [ ] Redirect URIs updated to your production URL (`https://.../auth/callback/google`, etc.).
- [ ] `APP_BASE_URL` matches that URL.

---

## Summary Table

| Where | What you configure |
|-------|--------------------|
| **Docker image** | App code, static files, default `.env` template, Python deps, Gunicorn on 5001. No secrets, no data. |
| **ECR** | Repository + push image. |
| **Secrets Manager** | SECRET_KEY, JWT_SECRET, GROQ_API_KEY (and OAuth if used). |
| **S3** | Bucket for documents; IAM for task/instance role. |
| **ECS or App Runner** | Image URI, CPU/memory, env vars, secrets (from Secrets Manager), port 5001, health check, logging. |
| **ALB + Route 53 + ACM** | (ECS) HTTPS and custom domain; then set APP_BASE_URL and OAuth redirect URIs. |

After this, your app runs from the Docker image with config and secrets coming from AWS services only.
