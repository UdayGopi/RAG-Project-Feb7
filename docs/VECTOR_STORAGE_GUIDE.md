# 🗄️ Vector Storage Guide for Production

## Overview

Your RAG system needs **two types of storage**:

1. **Document Storage**: Raw files (PDFs, DOCX) - Already configured (local/S3/Azure)
2. **Vector Storage**: Embeddings/indexes for fast retrieval - **This is what we'll cover**

---

## Current Setup (What You Have)

### Local Development (Default)
- **Vector Store**: LlamaIndex default (local disk)
- **Location**: `data/storage/` folder
- **Embedding Model**: `BAAI/bge-small-en-v1.5` (384 dimensions)
- **Works for**: Development, small datasets (<10K documents)

**Pros:**
- ✅ Free
- ✅ No external dependencies
- ✅ Fast for small datasets

**Cons:**
- ❌ Not scalable (single machine)
- ❌ No distributed search
- ❌ Hard to share across instances

---

## Production Options (What You Need)

For AWS deployment with better performance, you have **3 main options**:

### Option 1: **Pinecone** (Recommended for Easiest Setup) ⭐

**Best for**: Quick production deployment, managed service

```bash
# In .env
VECTOR_STORE=pinecone
PINECONE_API_KEY=your_api_key
PINECONE_ENVIRONMENT=us-west1-gcp
PINECONE_INDEX_NAME=rag-index
```

**Pros:**
- ✅ Fully managed (no infrastructure to manage)
- ✅ Auto-scaling
- ✅ Fast similarity search
- ✅ Built-in filtering and metadata
- ✅ Great documentation

**Cons:**
- ❌ Costs money (but has free tier: 100K vectors)
- ❌ Vendor lock-in

**Cost**: 
- Free tier: 100K vectors
- Paid: ~$70/month for 1M vectors

**Setup Time**: 5 minutes

---

### Option 2: **Qdrant** (Recommended for Best Value) ⭐⭐

**Best for**: Self-hosted or cloud, cost-effective

```bash
# In .env
VECTOR_STORE=qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_api_key
QDRANT_COLLECTION=rag_documents
```

**Pros:**
- ✅ Open-source (can self-host on EC2)
- ✅ Excellent performance
- ✅ Rich filtering capabilities
- ✅ Lower cost than Pinecone
- ✅ Docker support

**Cons:**
- ❌ Need to manage if self-hosting
- ❌ More setup than Pinecone

**Cost**:
- Self-hosted: EC2 costs only (~$30-50/month for t3.medium)
- Cloud: ~$25/month for 1M vectors

**Setup Time**: 15 minutes (cloud) or 30 minutes (self-hosted)

---

### Option 3: **OpenSearch** (AWS Native) ⭐⭐⭐

**Best for**: Already using AWS, need native integration

```bash
# In .env
VECTOR_STORE=opensearch
OPENSEARCH_HOST=your-domain.us-east-1.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=your_password
```

**Pros:**
- ✅ Native AWS service
- ✅ Integrates with other AWS services
- ✅ Very scalable
- ✅ Can use for logs + vectors

**Cons:**
- ❌ More expensive
- ❌ More complex setup
- ❌ Slower than dedicated vector DBs

**Cost**: ~$100-200/month for production cluster

**Setup Time**: 30-45 minutes

---

## 📊 Comparison Table

| Feature | Local (Current) | Pinecone | Qdrant | OpenSearch |
|---------|----------------|----------|---------|------------|
| **Cost** | Free | $70/mo | $30-50/mo | $100-200/mo |
| **Setup** | ✅ Done | ⭐⭐⭐ Easy | ⭐⭐ Medium | ⭐ Hard |
| **Performance** | Good | Excellent | Excellent | Good |
| **Scalability** | ❌ Limited | ✅ Unlimited | ✅ High | ✅ Unlimited |
| **AWS Integration** | N/A | External | External | ✅ Native |
| **Maintenance** | None | None | Low | Medium |
| **Free Tier** | ✅ Yes | ✅ 100K vectors | ❌ No | ❌ No |

---

## 🎯 My Recommendation for You

### For Development (Current)
**Keep using local storage** - it's already working!

```bash
# .env (current)
VECTOR_STORE=local  # or just don't set it
LOCAL_STORAGE_DIR=data/storage
```

### For Production on AWS
**Use Qdrant (self-hosted on EC2)** - Best value and performance

**Why Qdrant?**
1. ✅ **Cost-effective**: ~$30-50/month total
2. ✅ **Fast**: Excellent performance
3. ✅ **Flexible**: Can migrate to cloud later
4. ✅ **Control**: You own the data
5. ✅ **Scalable**: Handle millions of vectors

---

## 🚀 Implementation Plans

I'll create implementations for all three options so you can **toggle via .env**:

### Implementation 1: Enhanced Config (VectorStoreConfig)

Already started in `config/storage.py`! I'll complete it:

```python
# config/storage.py
class VectorStoreConfig:
    store_type: str = "local"  # or pinecone, qdrant, opensearch
    
    # Pinecone
    pinecone_api_key: str = None
    pinecone_environment: str = None
    pinecone_index_name: str = None
    
    # Qdrant
    qdrant_url: str = None
    qdrant_api_key: str = None
    qdrant_collection: str = None
    
    # OpenSearch
    opensearch_host: str = None
    opensearch_port: int = 443
```

### Implementation 2: Vector Store Factory

```python
# storage/vector_store.py (NEW)
def get_vector_store(config: VectorStoreConfig):
    """Factory for vector stores"""
    if config.store_type == "local":
        return LocalVectorStore()
    elif config.store_type == "pinecone":
        return PineconeVectorStore(config)
    elif config.store_type == "qdrant":
        return QdrantVectorStore(config)
    elif config.store_type == "opensearch":
        return OpenSearchVectorStore(config)
```

### Implementation 3: Updated .env

```bash
# Vector Storage Configuration
VECTOR_STORE=qdrant  # local, pinecone, qdrant, opensearch

# Qdrant (recommended for production)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=rag_documents

# Pinecone (alternative)
# PINECONE_API_KEY=your_key
# PINECONE_ENVIRONMENT=us-west1-gcp
# PINECONE_INDEX_NAME=rag-index

# OpenSearch (AWS native)
# OPENSEARCH_HOST=your-domain.us-east-1.es.amazonaws.com
# OPENSEARCH_PORT=443
```

---

## 🤖 Embedding Model Recommendations

### Current Setup
```bash
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
```

**Good for**: Development, cost-conscious production

### For Production AWS Deployment

#### Option 1: **Keep HuggingFace BGE** (Recommended) ⭐⭐⭐

```bash
# Small (fast, good quality)
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384

# OR Base (better quality, slightly slower)
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
EMBEDDING_DIMENSION=768

# OR Large (best quality, slowest)
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSION=1024
```

**Pros:**
- ✅ Free (no API calls)
- ✅ Fast (runs locally)
- ✅ High quality
- ✅ Privacy (no data sent externally)

**Cons:**
- ❌ Requires CPU/GPU on your instance
- ❌ Cold start time (first load)

**Best for**: You already have this working!

#### Option 2: **OpenAI Embeddings** (If using OpenAI LLM)

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=your_key
```

**Pros:**
- ✅ Excellent quality
- ✅ No local compute needed
- ✅ Consistent with OpenAI LLM

**Cons:**
- ❌ Costs money ($0.02 per 1M tokens)
- ❌ API dependency
- ❌ Privacy concerns

**Cost**: ~$20/month for 10K documents

#### Option 3: **Cohere Embeddings** (Best Multilingual)

```bash
EMBEDDING_PROVIDER=cohere
EMBEDDING_MODEL=embed-english-v3.0
EMBEDDING_DIMENSION=1024
COHERE_API_KEY=your_key
```

**Pros:**
- ✅ Great multilingual support
- ✅ Competitive pricing
- ✅ Good performance

**Cons:**
- ❌ Costs money
- ❌ API dependency

---

## 📋 Complete Production Setup

### Best Tech Stack for AWS Production

```bash
# ========== DOCUMENT STORAGE ==========
STORAGE_BACKEND=s3
S3_BUCKET=your-rag-documents
AWS_REGION=us-east-1

# ========== VECTOR STORAGE ==========
VECTOR_STORE=qdrant
QDRANT_URL=http://your-ec2-ip:6333
QDRANT_COLLECTION=rag_documents

# ========== EMBEDDINGS ==========
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5  # Upgrade from small to base
EMBEDDING_DIMENSION=768

# ========== LLM ==========
LLM_PROVIDER=groq  # or openai for production
LLM_MODEL=llama-3.1-8b-instant

# ========== RETRIEVAL ==========
RETRIEVAL_MODE=hybrid  # BM25 + Semantic
SIMILARITY_TOP_K=15
RERANK_TOP_N=5
SIMILARITY_CUTOFF=0.5

# ========== QUERY ENHANCEMENT ==========
ENABLE_QUERY_EXPANSION=true
QUERY_EXPANSION_COUNT=2

# ========== PERFORMANCE ==========
CACHE_ENABLED=true
CACHE_TTL_HOURS=24
MAX_WORKERS=4
```

---

## 🛠️ What We Need to Implement

### Already Have ✅
- ✅ Document storage abstraction (local/S3/Azure)
- ✅ Multiple LLM providers
- ✅ Multiple embedding providers
- ✅ Hybrid retrieval
- ✅ Query expansion
- ✅ Reranking
- ✅ Configuration management

### Need to Add 📝
- 🔨 **Vector store abstraction** (Pinecone/Qdrant/OpenSearch)
- 🔨 **Vector store factory** (like storage factory)
- 🔨 **Migration utilities** (local → cloud vector DB)
- 🔨 **Qdrant integration** (recommended)
- 🔨 **Pinecone integration** (optional)
- 🔨 **OpenSearch integration** (optional)

---

## 🚀 Quick Setup Guide

### Step 1: Choose Your Vector Store

**For testing/development:**
```bash
VECTOR_STORE=local  # Current, keep it
```

**For production (recommended):**
```bash
VECTOR_STORE=qdrant
```

### Step 2: Deploy Qdrant on AWS EC2

```bash
# SSH to your EC2 instance
ssh ubuntu@your-ec2-ip

# Install Docker
sudo apt update
sudo apt install docker.io -y

# Run Qdrant
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify
curl http://localhost:6333/collections
```

### Step 3: Update .env

```bash
VECTOR_STORE=qdrant
QDRANT_URL=http://your-ec2-ip:6333
QDRANT_COLLECTION=rag_documents
```

### Step 4: Migrate Data (if needed)

```python
# I'll create a migration script
python scripts/migrate_to_qdrant.py
```

---

## 💰 Cost Comparison

### Development Setup (Current)
- **Document Storage**: Local (Free)
- **Vector Storage**: Local (Free)
- **Embeddings**: HuggingFace (Free)
- **LLM**: Groq (Free)
- **Total**: $0/month ✅

### Production Setup Option 1 (Budget)
- **Document Storage**: S3 (~$5/month)
- **Vector Storage**: Qdrant self-hosted (~$40/month EC2 t3.medium)
- **Embeddings**: HuggingFace (Free, runs on EC2)
- **LLM**: Groq (Free, rate-limited)
- **Total**: ~$45/month

### Production Setup Option 2 (Quality)
- **Document Storage**: S3 (~$5/month)
- **Vector Storage**: Pinecone (~$70/month)
- **Embeddings**: OpenAI (~$20/month)
- **LLM**: OpenAI (~$100/month)
- **Total**: ~$195/month

### Production Setup Option 3 (AWS Native)
- **Document Storage**: S3 (~$5/month)
- **Vector Storage**: OpenSearch (~$150/month)
- **Embeddings**: HuggingFace (Free, runs on EC2)
- **LLM**: OpenAI (~$100/month)
- **EC2**: t3.large (~$60/month)
- **Total**: ~$315/month

---

## 🎯 My Specific Recommendation for You

### Current State: ✅ Perfect for Development
Keep everything as-is until you're ready to deploy.

### When Ready for Production:

1. **Start with Qdrant + HuggingFace** (Cost-effective)
   ```bash
   VECTOR_STORE=qdrant
   QDRANT_URL=http://your-ec2:6333
   EMBEDDING_MODEL=BAAI/bge-base-en-v1.5  # Upgrade to base
   ```

2. **Enable all retrieval features**
   ```bash
   RETRIEVAL_MODE=hybrid
   ENABLE_QUERY_EXPANSION=true
   RERANK_TOP_N=5
   ```

3. **Upgrade LLM if budget allows**
   ```bash
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4-turbo-preview
   ```

---

## 📦 What I'll Implement Next

Let me know if you want me to implement:

1. ✅ **Qdrant integration** (recommended)
2. ✅ **Pinecone integration** (alternative)
3. ✅ **Vector store factory** (toggle via .env)
4. ✅ **Migration scripts** (local → cloud)
5. ✅ **Deployment guide for Qdrant on EC2**

**Ready to implement?** Just say "yes, implement vector storage" and I'll add all the code!

---

## 🎓 Summary

**You already have:**
- ✅ Document storage (local/S3) - Done!
- ✅ Multiple embedding models - Done!
- ✅ Advanced retrieval - Done!

**You need to add:**
- 🔨 Vector store abstraction (I can implement)
- 🔨 Qdrant/Pinecone integration (I can implement)
- 🔨 Toggle via .env (I can implement)

**Best production setup:**
```
Documents → S3
Vectors → Qdrant (self-hosted)
Embeddings → HuggingFace BGE-base
Retrieval → Hybrid + Reranking
LLM → Groq (free) or OpenAI (quality)
Total Cost: ~$45/month
```

Let me know if you want me to implement the vector storage layer now!
