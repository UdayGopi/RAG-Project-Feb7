# 📋 Quick Reference

Cheat sheet for common configurations and tasks.

## Configuration Quick Reference

### Storage Backends

```bash
# Local (default, development)
STORAGE_BACKEND=local
LOCAL_DOCUMENTS_DIR=data/documents

# AWS S3 (production)
STORAGE_BACKEND=s3
S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
# Leave credentials empty to use IAM role

# Azure Blob
STORAGE_BACKEND=azure
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_CONTAINER_NAME=rag-documents
```

### LLM Providers

```bash
# Groq (fast, free, default)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
GROQ_API_KEY=your_key

# OpenAI (best quality)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_key

# Anthropic (good balance)
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=your_key

# Ollama (local, privacy)
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

### Embedding Models

```bash
# HuggingFace (free, local, default)
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5    # Small, fast
# EMBEDDING_MODEL=BAAI/bge-base-en-v1.5   # Balanced
# EMBEDDING_MODEL=BAAI/bge-large-en-v1.5  # Best quality

# OpenAI (best quality, paid)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_key

# Cohere (good multilingual)
EMBEDDING_PROVIDER=cohere
EMBEDDING_MODEL=embed-english-v3.0
COHERE_API_KEY=your_key
```

### Retrieval Strategies

```bash
# Semantic (default, embeddings only)
RETRIEVAL_MODE=semantic

# Hybrid (BM25 + Semantic, recommended!)
RETRIEVAL_MODE=hybrid

# Fusion (multi-query with RRF)
RETRIEVAL_MODE=fusion
```

### Query Expansion

```bash
# Disabled (default)
ENABLE_QUERY_EXPANSION=false

# Enable with synonyms (simple)
ENABLE_QUERY_EXPANSION=true
QUERY_EXPANSION_COUNT=2

# Enable with LLM (advanced)
ENABLE_QUERY_EXPANSION=true
QUERY_EXPANSION_COUNT=3
```

### Retrieval Parameters

```bash
# Initial retrieval
SIMILARITY_TOP_K=10        # Number to retrieve initially
SIMILARITY_CUTOFF=0.5      # Min similarity score (0.0-1.0)

# After reranking
RERANK_TOP_N=3             # Final number after reranking

# Context limits
MAX_CONTEXT_TOKENS=3500    # Max tokens for context
MAX_PROMPT_TOKENS=5500     # Max tokens for full prompt
```

### Chunking Strategies

```bash
# Small (for tweets, short docs)
CHUNK_SIZE=256
CHUNK_OVERLAP=50

# Medium (balanced)
CHUNK_SIZE=512
CHUNK_OVERLAP=100

# Large (default, for long documents)
CHUNK_SIZE=1024
CHUNK_OVERLAP=100

# XLarge (for very detailed retrieval)
CHUNK_SIZE=2048
CHUNK_OVERLAP=200
```

### Feature Toggles

```bash
# Text cleaning
CLEANING_ENABLED=true

# Table extraction
TABLE_EXTRACT_ENABLED=true

# Response caching
CACHE_ENABLED=true
CACHE_TTL_HOURS=24

# Performance metrics
ENABLE_METRICS=true

# Detailed tracing
ENABLE_TRACING=false
```

### Logging

```bash
# Development
LOG_LEVEL=DEBUG
DEBUG=true

# Production
LOG_LEVEL=WARNING
DEBUG=false

# Log file
LOG_FILE=logs/app.log
```

## Code Examples

### Using Storage

```python
from storage import get_storage

# Get storage (auto-detects from config)
storage = get_storage()

# Upload file
storage.upload_file("local_file.pdf", "documents/HIH/file.pdf")

# Download file
storage.download_file("documents/HIH/file.pdf", "/tmp/file.pdf")

# List files
files = storage.list_files("documents/HIH/")

# Check existence
exists = storage.exists("documents/HIH/file.pdf")

# Get presigned URL
url = storage.get_url("documents/HIH/file.pdf", expiry_seconds=3600)
```

### Using Models

```python
from core import get_llm, get_embedding_model, get_reranker

# Get LLM (from config)
llm = get_llm()

# Or specify provider
llm = get_llm(provider="openai", model_name="gpt-4")

# Get embeddings
embeddings = get_embedding_model()

# Get reranker
reranker = get_reranker(top_n=3)
```

### Hybrid Retrieval

```python
from retrieval import HybridRetriever

# Create hybrid retriever
retriever = HybridRetriever(
    vector_index=index,
    similarity_top_k=10,
    bm25_top_k=10,
    alpha=0.5  # 0=BM25 only, 1=semantic only
)

# Retrieve
from llama_index.core import QueryBundle
query = QueryBundle("What is HIH?")
nodes = retriever.retrieve(query)
```

### Query Expansion

```python
from retrieval import QueryExpander

# Create expander
expander = QueryExpander(llm=llm)

# Expand with synonyms
queries = expander.expand_query("What is HIH?", method="synonyms")

# Expand with LLM (multi-query)
queries = expander.expand_query("What is HIH?", method="multi_query")

# Expand with HyDE
queries = expander.expand_query("What is HIH?", method="hyde")
```

### Metadata Filtering

```python
from retrieval import MetadataFilter

# Filter by tenant
filters = MetadataFilter.create_tenant_filter("HIH")

# Filter by document type
filters = MetadataFilter.create_document_type_filter("policy")

# Combined filters
filters = MetadataFilter.create_combined_filter(
    tenant_id="HIH",
    doc_type="guide",
    tags=["onboarding", "esmd"]
)

# Use in query
query_engine = index.as_query_engine(filters=filters)
```

### Model Registry

```python
from models import ModelRegistry

# List all LLMs
llms = ModelRegistry.list_models(model_type="llm")

# List embeddings
embeddings = ModelRegistry.list_models(model_type="embedding")

# Get model info
info = ModelRegistry.get("groq-llama-3.1-8b")
print(f"Provider: {info.provider}")
print(f"Model: {info.model_name}")
print(f"Context: {info.context_window}")
print(f"Cost: ${info.cost_per_1m_tokens}/1M tokens")
```

### Intent Classification

```python
from agents import classify_intent
from config.constants import IntentType

# Classify query
intent, confidence = classify_intent("Hello, how are you?")

if intent == IntentType.SMALL_TALK:
    return "Hello! How can I help you today?"
elif intent == IntentType.DOWNLOAD:
    # Handle download request
    pass
elif intent == IntentType.QUESTION:
    # Process with RAG
    pass
```

## API Endpoints

### Authentication

```bash
# Sign up
POST /auth/signup
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "secure_password"
}

# Sign in
POST /auth/signin
{
  "email": "john@example.com",
  "password": "secure_password"
}

# Response includes JWT token
{
  "token": "eyJ...",
  "user": {...}
}
```

### Chat

```bash
# Send query
POST /chat
Authorization: Bearer <token>
{
  "query": "What are the HIH onboarding steps?",
  "tenant_id": "HIH"  # optional
}

# Response
{
  "summary": "Brief answer",
  "detailed_response": "Full answer with context",
  "sources": [
    {
      "text": "...",
      "score": 0.92,
      "metadata": {...}
    }
  ],
  "confidence": 0.92
}
```

### Upload

```bash
# Upload document
POST /upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

FormData:
- file: document.pdf
- tenant_id: HIH
- doc_type: policy  # optional
- tags: onboarding,esmd  # optional

# Response
{
  "message": "Document uploaded successfully",
  "file_id": "abc123",
  "chunks_created": 42
}
```

### Health Check

```bash
# Check status
GET /health

# Response
{
  "status": "healthy",
  "version": "2.0.0",
  "storage": "local",
  "llm_provider": "groq",
  "embedding_provider": "huggingface"
}
```

## Docker Commands

```bash
# Build
docker build -t rag-app .

# Run
docker run -d \
  --name rag-app \
  -p 5001:5001 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  rag-app

# View logs
docker logs -f rag-app

# Stop
docker stop rag-app

# Remove
docker rm rag-app

# Docker Compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

## AWS Deployment

```bash
# Create S3 bucket
aws s3 mb s3://your-rag-documents

# Upload code to EC2
scp -r Rag-Project ubuntu@your-ec2-ip:/home/ubuntu/

# SSH to EC2
ssh ubuntu@your-ec2-ip

# On EC2: Setup
cd /home/ubuntu/Rag-Project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Configure

# Run with gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 300 app:app

# Or use systemd service (see DEPLOYMENT.md)
```

## Performance Tuning

### For Speed

```bash
# Use smaller models
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
LLM_MODEL=llama-3.1-8b-instant

# Reduce retrieval
SIMILARITY_TOP_K=5
RERANK_TOP_N=2

# Smaller chunks
CHUNK_SIZE=512

# Enable caching
CACHE_ENABLED=true
```

### For Quality

```bash
# Use larger models
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview

# Increase retrieval
SIMILARITY_TOP_K=15
RERANK_TOP_N=5

# Use hybrid search
RETRIEVAL_MODE=hybrid

# Enable query expansion
ENABLE_QUERY_EXPANSION=true
```

### For Cost

```bash
# Use free tier LLM
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant

# Local embeddings
EMBEDDING_PROVIDER=huggingface

# Reduce token usage
MAX_CONTEXT_TOKENS=2000
MAX_PROMPT_TOKENS=3000

# Enable aggressive caching
CACHE_ENABLED=true
CACHE_TTL_HOURS=72
```

## Monitoring Commands

```bash
# View logs
tail -f logs/app.log

# Filter errors
grep ERROR logs/app.log

# Check health
curl http://localhost:5001/health

# Monitor performance
# (if metrics enabled)
curl http://localhost:5001/metrics

# System resources
htop  # or top
df -h  # disk usage
free -h  # memory
```

---

For more details, see full documentation in `docs/` folder.
