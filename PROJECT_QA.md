# CarePolicy RAG Hub – Questions & Answers

A single reference for **conceptual**, **setup**, **configuration**, **API**, **Docker**, **AWS**, **troubleshooting**, and **security** questions about this project.

---

## Table of Contents

1. [Conceptual & Overview](#1-conceptual--overview)
2. [Setup & Running Locally](#2-setup--running-locally)
3. [Configuration & Environment](#3-configuration--environment)
4. [APIs & Endpoints](#4-apis--endpoints)
5. [Frontend (React)](#5-frontend-react)
6. [Docker & Images](#6-docker--images)
7. [AWS Deployment](#7-aws-deployment)
8. [RAG & Backend Logic](#8-rag--backend-logic)
9. [Troubleshooting](#9-troubleshooting)
10. [Security & Best Practices](#10-security--best-practices)

---

## 1. Conceptual & Overview

### What is this project?

A **production-grade RAG (Retrieval-Augmented Generation)** application for healthcare/care policy. Users ask questions in natural language; the system retrieves relevant chunks from ingested documents and uses an LLM (e.g. Groq) to generate answers with source citations.

### What is “CarePolicy Hub”?

The branded name of this RAG app. It provides a chat interface, document upload, tenant-specific indexes, and optional OAuth (Google/Microsoft) and JWT-based auth.

### What tech stack is used?

- **Backend:** Python 3.11, Flask, Gunicorn  
- **RAG/LLM:** LlamaIndex, Groq (default LLM), HuggingFace embeddings (e.g. BAAI/bge-small-en-v1.5)  
- **Frontend:** React 18, Vite, Tailwind CSS, Chart.js  
- **Auth:** JWT, optional OAuth (Google, Microsoft) via Authlib  
- **Storage:** Local filesystem or AWS S3 (configurable)  
- **Deploy:** Docker (default + ultralight Dockerfile), AWS (ECS/App Runner, ECR, Secrets Manager)

### What is the difference between “RAG” and “agent”?

Here, **RAG** is the retrieval + generation pipeline (documents → chunks → embeddings → retrieval → LLM answer). The **RAG agent** (`rag_agent.py`) is the main component that builds indexes, routes queries (e.g. by tenant), runs retrieval, and generates answers. There is no separate “agentic” loop in the current codebase; it’s single-shot RAG.

### Is the app multi-tenant?

Yes. The RAG agent can maintain separate vector indexes per tenant (e.g. HIH, RC). Queries can be routed by tenant or answered from a combined index depending on configuration.

---

## 2. Setup & Running Locally

### What do I need installed to run the app locally?

- **Python 3.11+**  
- **pip** (or conda)  
- **Node.js** (only if you build or run the React frontend)  
- **GROQ_API_KEY** (get one at https://groq.com)

### How do I run the backend only (no Docker)?

```bash
# From project root
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY (and SECRET_KEY for auth)

python app.py
```

The app listens on **http://127.0.0.1:5001** (or the port in `.env`).

### How do I run the React frontend in development?

```bash
cd frontend
npm install
npm run dev
```

Configure the frontend to talk to the backend (e.g. `VITE_API_URL=http://127.0.0.1:5001` or similar in `frontend/.env`). The backend serves the built frontend at `/app/` when you use the ultralight Docker image; locally you often run Vite dev server and point it at the Flask port.

### Which file does the app load for environment variables?

The app uses **`.env`** in the **project root**. `load_dotenv()` in `app.py` loads that file. `.env.example` and `.env.ultralight` are **templates only**; the app does not load them unless you copy one to `.env`.

### Do I need to create a `storage/` or `documents/` folder?

The **RAG agent** creates `documents` and `storage` (for vector index) on startup if they don’t exist. You don’t have to create them manually for local runs. In Docker, the Dockerfile may not copy `storage/` (e.g. ultralight); indexes can be built at runtime or mounted.

---

## 3. Configuration & Environment

### What are the required environment variables?

- **GROQ_API_KEY** – Required for the default LLM (Groq).  
- **SECRET_KEY** – Used by Flask and JWT; set a strong value in production.  
- **JWT_SECRET** – Optional; defaults to SECRET_KEY. Used to sign JWT tokens.

### What optional env vars are commonly used?

- **PORT**, **HOST** – Server bind (e.g. PORT=5001, HOST=0.0.0.0).  
- **JWT_EXPIRES_MIN** – Token lifetime (default 10080 = 7 days).  
- **STORAGE_BACKEND** – `local` or `s3`.  
- **S3_BUCKET**, **S3_PREFIX**, **AWS_REGION** – When using S3.  
- **GOOGLE_CLIENT_ID**, **GOOGLE_CLIENT_SECRET**, **MS_CLIENT_ID**, **MS_CLIENT_SECRET**, **APP_BASE_URL** – For OAuth.  
- **CLEANING_ENABLED**, **TABLE_EXTRACT_ENABLED**, **CACHE_ENABLED** – RAG behavior (true/false).  
- **TENANT_HIGH_CONF_THRESH**, **TENANT_MIN_CONF_THRESH**, **ROUTING_COSINE_WEIGHT**, **TENANT_ALIASES** – Tenant routing.

### Where is the list of all env vars?

See **`.env.example`** in the project root. It documents application, security, API keys, OAuth, storage, RAG, and optional Bedrock/OpenSearch vars.

### Does the app use AWS Bedrock or OpenSearch by default?

No. The **root `rag_agent.py`** uses Groq + HuggingFace embeddings and local (in-memory/filesystem) vector store. Bedrock and OpenSearch are documented in **AWS_BEDROCK_OPENSEARCH_GUIDE.md** and can be wired in via env and code changes.

---

## 4. APIs & Endpoints

### What are the main API routes?

| Method | Path | Purpose |
|--------|------|--------|
| GET | `/` | Redirect/landing |
| GET | `/welcome`, `/hub`, `/app`, `/app/` | App / hub / React app |
| GET | `/auth.html` | Auth page |
| GET | `/auth/providers` | List OAuth providers |
| GET | `/auth/login/<provider>` | Start OAuth (e.g. google) |
| GET | `/auth/callback/<provider>` | OAuth callback |
| POST | `/auth/signup` | Email/password sign up |
| POST | `/auth/signin` | Email/password sign in |
| POST | `/auth/signout` | Sign out |
| POST | `/auth/forgot` | Forgot password |
| GET | `/me` | Current user (JWT) |
| POST | `/chat` | Send chat message (RAG query) |
| POST | `/feedback` | Submit feedback |
| POST | `/upload` | Upload document |
| GET | `/tenants` | List tenants |
| GET | `/history` | Chat history |
| GET | `/analytics` | Analytics data |
| GET | `/download/<tenant_id>/<path:filename>` | Download file |
| GET | `/view/<tenant_id>/<path:filename>` | View file |
| GET | `/schedules` | List schedules |
| POST | `/schedules` | Create schedule |
| PUT | `/schedules/<sid>` | Update schedule |
| DELETE | `/schedules/<sid>` | Delete schedule |

### What does the `/chat` endpoint expect and return?

**Request:** JSON with at least `"query"` (string). Optionally `tenant_id`, session/history fields depending on implementation.

**Response:** Typically includes a summary or full answer, sources (chunks/citations), and possibly confidence or metadata. Exact shape is in `app.py` around the `chat_handler` and the return value from the RAG agent.

### Is there a health check endpoint?

The README mentions `GET /health` for production; the current `app.py` may not define it. If you need one for ECS/App Runner, add a simple route that returns `{"status": "healthy"}`.

---

## 5. Frontend (React)

### Where is the React app and how is it built?

- **Location:** `frontend/`  
- **Build:** `npm run build` (Vite). For Docker ultralight, set `VITE_BASE=/app/` so assets are served under `/app/`.

### How does the frontend talk to the backend?

The frontend uses a base URL (e.g. same origin or `VITE_API_URL`). API calls go to the same host (e.g. `http://localhost:5001`) for chat, auth, upload, etc. See `frontend/src/api.js` (or equivalent) for the actual base URL and fetch calls.

### What is served at `/app/`?

When using the **ultralight Docker image**, the backend serves the **built React app** from `frontend/dist` at `/app/`. So the React UI is at **http://localhost:5001/app/** (or your deployed host + `/app/`).

### Which Dockerfile includes the React app?

**Dockerfile.ultralight** includes the React app by copying `frontend/dist` into the image. The **default Dockerfile** does not; it’s backend-only.

---

## 6. Docker & Images

### What are the two Dockerfiles?

- **Dockerfile** (default): Full backend, `requirements.txt`, larger image (~1.2GB). No React in image.  
- **Dockerfile.ultralight**: Smaller image, `requirements.ultralight.txt`, **includes** pre-built React at `/app/`. Build requires building the frontend on the host first.

### How do I build the default image?

```bash
# From project root
docker build -t carepolicy-hub:latest .
```

### How do I build the ultralight image (with React)?

**Step 1 – Build frontend on your machine:**

```powershell
cd frontend
$env:VITE_BASE="/app/"
npm install
npm run build
cd ..
```

**Step 2 – Build image:**

```bash
docker build -f Dockerfile.ultralight -t carepolicy-hub:latest .
```

### How do I run the container?

```bash
docker run -p 5001:5001 \
  -e GROQ_API_KEY="your_key" \
  -e SECRET_KEY="your_secret" \
  carepolicy-hub:latest
```

Then open **http://localhost:5001** (default image) or **http://localhost:5001/app/** (ultralight with React).

### Why does the container crash with “Permission denied” on NLTK?

LlamaIndex uses NLTK and tries to download `punkt_tab` (and use `punkt`) at runtime into a path under the venv. The process runs as a non-root user and can’t write there. **Fix:** In Dockerfile.ultralight, NLTK data is downloaded during **build** as root into the llama_index NLTK cache path, then that directory is `chown`ed to the app user so no runtime download is needed.

### What if Docker build fails with “snapshot does not exist” or “COPY frontend” errors?

This is often a BuildKit cache issue. Try:

- `docker builder prune -f`  
- `docker build --no-cache -f Dockerfile.ultralight -t carepolicy-hub:latest .`  

Or build the frontend locally and only `COPY frontend/dist` (as in the current ultralight instructions).

### Which requirements file does each Dockerfile use?

- **Dockerfile** → **requirements.txt**  
- **Dockerfile.ultralight** → **requirements.ultralight.txt**

---

## 7. AWS Deployment

### What do I use for deployment on AWS?

Typical flow: build image → push to **Amazon ECR** → run with **ECS Fargate** or **App Runner**. Use **Secrets Manager** (or task env) for GROQ_API_KEY, SECRET_KEY, JWT_SECRET. Optionally use **S3** for documents and **ALB + Route 53 + ACM** for HTTPS and custom domain.

### Where are the deployment steps documented?

- **AWS_DEPLOY_CONFIG_GUIDE.md** – What goes in the image, which AWS services to use, ECR, Secrets Manager, ECS/App Runner config.  
- **AWS_BEDROCK_OPENSEARCH_GUIDE.md** – Optional Bedrock and OpenSearch setup.  
- **BUILD_DOCKER.md** – Docker build and run (including ultralight).  
- **docs/** – DEPLOYMENT.md, ECS_DEPLOYMENT.md, etc.

### Which Dockerfile should I use for AWS?

Either is fine: **Dockerfile** for full backend (no React in image; serve frontend via S3/CloudFront or another host) or **Dockerfile.ultralight** for one image with backend + React. The deploy script (`scripts/deploy-ecs.sh`) uses the default **Dockerfile**.

### How do I pass secrets (e.g. GROQ_API_KEY) in ECS?

Store them in **AWS Secrets Manager** and reference the secret ARN in the ECS task definition (e.g. `secrets` section mapping secret ARN to env var name). Never bake real keys into the image.

---

## 8. RAG & Backend Logic

### Where is the main RAG logic?

In **`rag_agent.py`** at the project root. `app.py` imports `RAGAgent` from there and uses it for `/chat` and document ingestion.

### What LLM and embedding models are used by default?

- **LLM:** Groq, model `llama-3.1-8b-instant` (configurable via env if supported).  
- **Embeddings:** HuggingFace `BAAI/bge-small-en-v1.5` (in `rag_agent.py`).

### Where are documents and indexes stored?

- **Documents:** `documents/` (or S3 if `STORAGE_BACKEND=s3`).  
- **Vector index:** `storage/` (local) or the path configured in the RAG agent. The root `rag_agent.py` uses LlamaIndex’s storage (e.g. local by default).

### Does the app support hybrid search or query expansion?

The **architecture** (README and docs) describes hybrid retrieval, query expansion, and reranking. The **root `rag_agent.py`** uses LlamaIndex with Groq and HuggingFace embeddings; exact features (hybrid, expansion, reranking) depend on the code in that file and env flags (e.g. RETRIEVAL_MODE, ENABLE_QUERY_EXPANSION).

### What are “tenants” in this app?

Tenants are logical namespaces (e.g. HIH, RC) for isolating documents and optionally indexes. The RAG agent can route queries to a tenant-specific index or use tenant metadata for filtering.

---

## 9. Troubleshooting

### “GROQ_API_KEY environment variable is not set”

Set it in `.env` (local) or in the environment where the app runs (Docker `-e`, ECS task definition, etc.). The RAG agent raises this error on startup if the key is missing.

### “Module not found” when running the app

Ensure you’re in the correct venv and have installed deps: `pip install -r requirements.txt` (or `requirements.ultralight.txt` for ultralight). If you use Docker, rebuild the image so the module is installed in the image.

### “Permission denied” for NLTK in Docker

NLTK is trying to write into the venv at runtime. Use a Dockerfile that pre-downloads NLTK data during build and chowns the cache dir to the app user (see Dockerfile.ultralight NLTK fix).

### S3 “access denied” or upload fails

Check **STORAGE_BACKEND=s3**, **S3_BUCKET**, **AWS_REGION**, and credentials (env vars or IAM role). Ensure the bucket policy or IAM role allows the required s3:GetObject/s3:PutObject (and list if used).

### Port 5001 already in use

Change **PORT** in `.env` or run Docker with another host port: `docker run -p 5002:5001 ...` and use **http://localhost:5002**.

### Frontend shows 404 for `/app/`

Either the image doesn’t include the React build (default Dockerfile), or the build wasn’t done with `VITE_BASE=/app/` and the assets are requested from the wrong path. Use Dockerfile.ultralight and follow BUILD_DOCKER.md for the two-step build.

### Pip dependency conflict (e.g. llama-index-core)

If you see version conflicts with `llama-index-llms-groq` and `llama-index-core`, align versions in the requirements file (e.g. `llama-index-core>=0.10.1,<0.11.0` in requirements.ultralight.txt).

---

## 10. Security & Best Practices

### Should I commit `.env`?

**No.** `.env` contains secrets. Use `.env.example` as a template and add `.env` to `.gitignore` (it usually is).

### I accidentally committed or shared my GROQ API key. What should I do?

**Rotate the key** in the Groq dashboard immediately and update the key everywhere you run the app (local `.env`, Docker run, AWS Secrets Manager, etc.). Treat the old key as compromised.

### How should I set SECRET_KEY and JWT_SECRET in production?

Use long random values (e.g. `openssl rand -hex 32`). Set them via environment or AWS Secrets Manager, not in the image or in code.

### Does the app use HTTPS?

Flask serves HTTP. In production, put the app behind a reverse proxy or load balancer (e.g. ALB, App Runner) that terminates HTTPS. Set **APP_BASE_URL** to the public HTTPS URL for OAuth callbacks.

### Where are passwords stored?

Passwords are hashed (e.g. with Werkzeug’s `generate_password_hash`) and stored in the app’s database (e.g. SQLite). Never store plain-text passwords.

---

## Quick reference

| Topic | Key file / doc |
|-------|-----------------|
| Run locally | `python app.py` after `pip install -r requirements.txt` and `.env` |
| Env template | `.env.example` |
| Main app entry | `app.py` |
| RAG logic | `rag_agent.py` |
| React app | `frontend/`, build with `VITE_BASE=/app/` for Docker |
| Docker default | `Dockerfile` + `requirements.txt` |
| Docker with React | `Dockerfile.ultralight` + build `frontend/dist` first |
| Build instructions | `BUILD_DOCKER.md` |
| AWS config | `AWS_DEPLOY_CONFIG_GUIDE.md`, `AWS_BEDROCK_OPENSEARCH_GUIDE.md` |
| Architecture | `docs/ARCHITECTURE.md`, `README.md` |

---

*Generated for the CarePolicy RAG Hub project. Update this file as the project evolves.*
