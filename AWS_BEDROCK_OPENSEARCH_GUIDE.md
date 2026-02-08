# AWS Bedrock & OpenSearch Service: Where to Add and How to Access

This guide explains **where to add** configuration for **Amazon Bedrock** (embeddings/LLM) and **OpenSearch Service** (vector store), and how the app accesses them.

---

## Important: What Uses These Today

| Component | Bedrock (embeddings) | OpenSearch (vector store) |
|-----------|----------------------|----------------------------|
| **config/settings.py** | ✅ Has `EMBEDDING_PROVIDER=bedrock`, `BEDROCK_EMBEDDING_MODEL`, `AWS_REGION` | ✅ Has `VECTOR_STORE=opensearch`, `OPENSEARCH_*` |
| **core/embeddings.py** | ✅ `get_embedding_model(provider="bedrock")` implemented | N/A (vector store is separate) |
| **Root rag_agent.py** (used by **app.py**) | ❌ Uses hardcoded HuggingFace | ❌ Uses local disk (`storage_dir`) |
| **agents/rag_agent.py** (ModernRAGAgent) | ✅ Can use config/settings | ✅ Can use config/settings |

So: **Bedrock and OpenSearch are supported in config + core/embeddings**, but the **main app** (Flask `app.py` + root `rag_agent.py`) does not read them yet. To use Bedrock/OpenSearch you can either:

1. **Use the agents path** (e.g. run `app_new.py` or wire app.py to use `agents.rag_agent`), which respects config/settings, or  
2. **Add env-based selection** to root `rag_agent.py` so it picks embedding provider and vector store from env (see “Making the main app use Bedrock/OpenSearch” below).

Regardless, **where to add** the configuration is the same: **.env** (local) and **AWS** (ECS/App Runner env + Secrets Manager).

---

## Part 1: Amazon Bedrock

### What it is

- **Bedrock** = AWS managed service for foundation models (LLM and embeddings).
- Your app can use it for **embeddings** (and optionally LLM) so you don’t run models in the container.
- Access is via **AWS API** (no separate API key); auth is **IAM** (role or keys).

### Where to add configuration

**1. Local (.env)**

Add (or uncomment) in your **`.env`** in the project root:

```bash
# Use Bedrock for embeddings
EMBEDDING_PROVIDER=bedrock
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1
# Or: amazon.titan-embed-g1-text-02

# AWS (Bedrock uses same region/credentials as rest of AWS)
AWS_REGION=us-east-1

# Optional: only if not using IAM role (e.g. local dev)
# AWS_ACCESS_KEY_ID=AKIA...
# AWS_SECRET_ACCESS_KEY=...
```

**2. AWS (ECS or App Runner)**

- **Environment variables** (task definition or App Runner runtime config):

  | Variable | Example | Secret? |
  |----------|---------|--------|
  | `EMBEDDING_PROVIDER` | `bedrock` | No |
  | `BEDROCK_EMBEDDING_MODEL` | `amazon.titan-embed-text-v1` | No |
  | `AWS_REGION` | `us-east-1` | No |

- **Credentials**: Prefer **no** keys in env. Attach an **IAM role** to the ECS task (task role) or App Runner instance so the app uses IAM automatically. If you must use keys (not recommended), put them in **Secrets Manager** and map them to `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the task definition.

**3. IAM (how the app accesses Bedrock)**

The role used by the container (ECS task role or App Runner instance role) needs permission to call Bedrock, for example:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/*"
}
```

Or narrow to a region:

```json
"Resource": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
```

- In **AWS Console**: IAM → Roles → your ECS task role / App Runner role → Add permissions → attach a policy with the above (or use `AmazonBedrockFullAccess` for testing only).
- **Model access**: In Bedrock console, ensure the Titan embedding model (or the one you set in `BEDROCK_EMBEDDING_MODEL`) is **available** for your account/region.

### Code that uses it

- **core/embeddings.py**: when `EMBEDDING_PROVIDER=bedrock`, it uses `BedrockEmbedding` with `settings.BEDROCK_EMBEDDING_MODEL`, `settings.AWS_REGION`, and optional `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.
- **requirements.txt** already includes `llama-index-embeddings-bedrock==0.1.2` and `boto3`.

So: **add the env vars in .env and in AWS**; **attach an IAM role with Bedrock permissions** to the task/instance. No extra “access” step beyond that.

---

## Part 2: OpenSearch Service (vector store)

### What it is

- **OpenSearch Service** = AWS managed search/vector store. You create a domain; the app connects to its **endpoint** and stores/queries vector embeddings there.
- Replaces local vector storage so multiple tasks or restarts share the same index.

### Where to add configuration

**1. Local (.env)**

In **`.env`**:

```bash
# Use OpenSearch as vector store
VECTOR_STORE=opensearch

# OpenSearch Service endpoint (from AWS console: OpenSearch → your domain → Endpoint)
OPENSEARCH_HOST=search-your-domain-xxxxx.us-east-1.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USE_SSL=true

# Fine-grained access control (user/password)
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=YourOpenSearchMasterPassword

# Index name (app will use this for vectors)
OPENSEARCH_INDEX=rag_documents
```

**2. AWS (ECS or App Runner)**

- **Environment variables**:

  | Variable | Example | Secret? |
  |----------|---------|--------|
  | `VECTOR_STORE` | `opensearch` | No |
  | `OPENSEARCH_HOST` | `search-xxx.us-east-1.es.amazonaws.com` | No |
  | `OPENSEARCH_PORT` | `443` | No |
  | `OPENSEARCH_USE_SSL` | `true` | No |
  | `OPENSEARCH_USER` | `admin` | No (or use secret) |
  | `OPENSEARCH_INDEX` | `rag_documents` | No |

- **OPENSEARCH_PASSWORD**: Store in **Secrets Manager** (e.g. `carepolicy-hub/opensearch-password`) and reference in the task definition as a secret → env `OPENSEARCH_PASSWORD`.

**3. Network and security (how the app accesses OpenSearch)**

- **VPC**: Run ECS tasks (or App Runner VPC connector) in the **same VPC** as the OpenSearch domain, or ensure the domain is reachable (e.g. public access or VPC peering). OpenSearch Service is usually in a VPC.
- **Security group**: OpenSearch domain’s security group must allow **inbound 443** from the ECS task security group (or the NAT/public IP used by the app).
- **IAM vs master user**: OpenSearch can use either:
  - **Fine-grained access (master user)**: use `OPENSEARCH_USER` + `OPENSEARCH_PASSWORD` (password in Secrets Manager).
  - **IAM**: if your domain has IAM auth enabled, you’d use SigV4 and no password; that requires code/LLamaIndex support for IAM-signed requests (some clients support it).

So: **add the env vars in .env and in AWS**; **put OpenSearch password in Secrets Manager**; **place the app in a network that can reach the OpenSearch endpoint** and **allow 443** in the domain’s security group.

### Packages

In **requirements.txt**, OpenSearch is commented out. To use OpenSearch, uncomment:

```text
# For OpenSearch (AWS):
llama-index-vector-stores-opensearch==0.1.5
opensearch-py==2.4.0
```

Then **rebuild the Docker image** so the container has these dependencies.

### Where the app would use it

- **config/settings.py** already defines `VECTOR_STORE`, `OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`, `OPENSEARCH_INDEX`, `OPENSEARCH_USE_SSL`.
- Any code that builds the vector store from **config/settings** (e.g. a vector store factory or **agents/rag_agent.py**) can use OpenSearch when `VECTOR_STORE=opensearch`. The **root rag_agent.py** currently does not; it uses local storage only.

---

## Part 3: Summary – Where to Add What

| What | .env (local) | AWS (ECS / App Runner) | AWS (Secrets Manager) | AWS (IAM / network) |
|------|----------------|-------------------------|------------------------|----------------------|
| **Bedrock** | `EMBEDDING_PROVIDER=bedrock`, `BEDROCK_EMBEDDING_MODEL`, `AWS_REGION` | Same env vars; no keys if using IAM | Optional: `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` if not using role | Task/instance role: `bedrock:InvokeModel` (and model enabled in Bedrock console) |
| **OpenSearch** | `VECTOR_STORE=opensearch`, `OPENSEARCH_HOST`, `OPENSEARCH_PORT`, `OPENSEARCH_USE_SSL`, `OPENSEARCH_USER`, `OPENSEARCH_INDEX`, `OPENSEARCH_PASSWORD` | Same env vars; password can be from secret | `OPENSEARCH_PASSWORD` (recommended) | Same VPC/reachability; security group allow 443 to OpenSearch |

---

## Part 4: Making the main app (app.py) use Bedrock and OpenSearch

The Flask app currently uses **root rag_agent.py**, which hardcodes HuggingFace embeddings and local vector storage. To use Bedrock and OpenSearch from the **same** app:

1. **Add env-based selection in rag_agent.py**  
   - Read `os.getenv("EMBEDDING_PROVIDER")` / `os.getenv("VECTOR_STORE")`.  
   - If `bedrock`, create the embedding model via `core.embeddings.get_embedding_model(provider="bedrock")` (and set `Settings.embed_model`).  
   - If `opensearch`, build the vector store from `config.settings` (OPENSEARCH_*) and use it when building indices instead of local storage.  
   This requires adding the OpenSearch vector store construction (using LlamaIndex’s OpenSearch integration) where the index is created/loaded.

2. **Or switch the app to the agents path**  
   - Use **agents.rag_agent** (ModernRAGAgent) and ensure it’s initialized from **config/settings** so it already uses `EMBEDDING_PROVIDER` and `VECTOR_STORE`. Then point **app.py** to that agent instead of the root `RAGAgent`.

Until one of these is done, **adding the env vars and IAM/Secrets/network only prepares configuration**; the main app will actually use Bedrock/OpenSearch only after the code path that builds embeddings and vector store reads these settings (config + core/embeddings or agents path).

---

## Part 5: ECS task definition snippet (example)

You can add these to your ECS task definition (environment + secrets) so the container gets Bedrock and OpenSearch config in AWS:

**Environment (non-secret):**

```json
{"name": "EMBEDDING_PROVIDER", "value": "bedrock"},
{"name": "BEDROCK_EMBEDDING_MODEL", "value": "amazon.titan-embed-text-v1"},
{"name": "AWS_REGION", "value": "us-east-1"},
{"name": "VECTOR_STORE", "value": "opensearch"},
{"name": "OPENSEARCH_HOST", "value": "search-your-domain-xxxxx.us-east-1.es.amazonaws.com"},
{"name": "OPENSEARCH_PORT", "value": "443"},
{"name": "OPENSEARCH_USE_SSL", "value": "true"},
{"name": "OPENSEARCH_USER", "value": "admin"},
{"name": "OPENSEARCH_INDEX", "value": "rag_documents"}
```

**Secrets (from Secrets Manager):**

```json
{"name": "OPENSEARCH_PASSWORD", "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:carepolicy-hub/opensearch-password"}
```

Create the secret:

```bash
aws secretsmanager create-secret \
  --name carepolicy-hub/opensearch-password \
  --secret-string "YourOpenSearchMasterPassword" \
  --region us-east-1
```

Ensure the task **role** has:
- Bedrock: `bedrock:InvokeModel` (and optionally `bedrock:InvokeModelWithResponseStream`).
- OpenSearch: if you use IAM for OpenSearch, add `es:ESHttpGet`, `es:ESHttpPost`, etc., as required by your domain; if you use master user/password, no extra IAM for OpenSearch is needed.

---

## Quick checklist

- **Bedrock**: Set `EMBEDDING_PROVIDER=bedrock`, `BEDROCK_EMBEDDING_MODEL`, `AWS_REGION` in .env and in ECS/App Runner; give the task/instance role Bedrock invoke permission; enable the model in Bedrock console.
- **OpenSearch**: Set `VECTOR_STORE=opensearch` and all `OPENSEARCH_*` in .env and in ECS/App Runner; put `OPENSEARCH_PASSWORD` in Secrets Manager; uncomment OpenSearch packages in requirements and rebuild image; ensure app runs in a network that can reach the OpenSearch endpoint (VPC + security group 443).
- **Code**: Either switch to the agents path that uses config/settings, or add env-based Bedrock/OpenSearch support in root `rag_agent.py` so the main app actually uses these settings.
