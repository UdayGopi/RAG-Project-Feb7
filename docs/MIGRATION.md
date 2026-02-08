# 🔄 Migration Guide

Guide for migrating from the old monolithic structure to the new modular architecture.

## Overview of Changes

### Before (Monolithic)
```
Rag-Project/
├── app.py (880+ lines)
├── rag_agent.py (1785+ lines!)
├── documents/
├── storage/
└── .env
```

### After (Modular)
```
Rag-Project/
├── config/           # Centralized configuration
├── core/             # RAG components
├── agents/           # Agent logic
├── storage/          # Storage abstraction
├── retrieval/        # Advanced retrieval
├── models/           # Model management
├── ingestion/        # Document processing
├── database/         # Data layer
├── api/              # API routes
├── utils/            # Utilities
├── app.py            # Slim main file
└── .env              # Enhanced config
```

## Migration Steps

### Step 1: Backup Current System

```bash
# Backup everything
cp -r Rag-Project Rag-Project-backup

# Backup database
cp data/users.db data/users.db.backup

# Backup environment
cp .env .env.backup
```

### Step 2: Update Environment Variables

The new `.env` has many more options. Update your `.env`:

```bash
# Copy new template
cp .env.example .env.new

# Migrate your values from old .env to .env.new
# Old format:
GROQ_API_KEY=xxx
SECRET_KEY=xxx

# New format (same keys, but more options):
# Application
ENVIRONMENT=production  # NEW
APP_VERSION=2.0.0       # NEW

# API Keys (same)
GROQ_API_KEY=xxx

# Storage Backend (NEW - defaults to local)
STORAGE_BACKEND=local   # or 's3', 'azure'

# Model Configuration (NEW - more control)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2048

EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Retrieval Strategy (NEW)
RETRIEVAL_MODE=semantic  # or 'hybrid', 'fusion'
ENABLE_QUERY_EXPANSION=false

# Feature Toggles (were hardcoded before)
CLEANING_ENABLED=true
TABLE_EXTRACT_ENABLED=true
CACHE_ENABLED=true
```

Once migrated:
```bash
mv .env .env.old
mv .env.new .env
```

### Step 3: Install New Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Update dependencies
pip install -r requirements.txt --upgrade

# Verify installation
python -c "from config import settings; print('Config loaded!')"
```

### Step 4: Migrate Existing Data

Your existing data is compatible! No migration needed for:
- **Documents**: Stay in `data/documents/` or `documents/`
- **Indexes**: Stay in `data/storage/` or `storage/`
- **Database**: Stay in `data/users.db`

But you should reorganize:

```bash
# If your data is scattered
mkdir -p data/documents data/storage data/cache data/models

# Move documents if needed
mv documents/* data/documents/

# Move storage if needed
mv storage/* data/storage/

# Move database if needed
mv users.db data/users.db
```

### Step 5: Update Code References (If You Modified)

If you modified the old `rag_agent.py` or `app.py`, here's how to migrate:

#### Old Code (Monolithic)

```python
# Old rag_agent.py
from rag_agent import RAGAgent

agent = RAGAgent(
    documents_dir="documents",
    storage_dir="storage"
)

response = agent.query("What is HIH?")
```

#### New Code (Modular)

```python
# New structure
from agents import ModernRAGAgent
from config import settings

agent = ModernRAGAgent()  # Uses settings automatically

response = agent.query("What is HIH?")
```

#### Configuration Changes

**Old Way**:
```python
# Hardcoded in rag_agent.py
self.llm = Groq(model="llama-3.1-8b-instant", api_key=os.getenv("GROQ_API_KEY"))
self.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
```

**New Way**:
```python
# In config/settings.py (via .env)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.1-8b-instant

# In your code
from core import get_llm, get_embedding_model

llm = get_llm()  # Automatically uses settings
embeddings = get_embedding_model()
```

#### Storage Changes

**Old Way**:
```python
# Direct filesystem access
import os
doc_path = os.path.join("documents", tenant_id, filename)
with open(doc_path, 'rb') as f:
    content = f.read()
```

**New Way**:
```python
# Storage abstraction
from storage import get_storage

storage = get_storage()  # Automatically uses config (local/S3)
content = storage.download_file(f"{tenant_id}/{filename}", "/tmp/temp.pdf")
```

### Step 6: Test the Migration

```bash
# Start the server
python app.py

# In another terminal, test endpoints
curl http://localhost:5001/health

# Test chat
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is HIH?"}'

# Test with your existing documents
# They should work immediately!
```

### Step 7: Verify Functionality

Checklist:

- [ ] Server starts without errors
- [ ] Health endpoint responds
- [ ] Can authenticate (if using auth)
- [ ] Can query existing documents
- [ ] Can upload new documents
- [ ] Logs are being written
- [ ] Database queries work

### Step 8: Enable New Features (Optional)

Now that you're on the new structure, enable advanced features:

#### Enable Hybrid Search

```bash
# In .env
RETRIEVAL_MODE=hybrid
```

This combines semantic and keyword search for better results.

#### Enable Query Expansion

```bash
# In .env
ENABLE_QUERY_EXPANSION=true
QUERY_EXPANSION_COUNT=2
```

This generates query variations for better recall.

#### Switch to Cloud Storage (S3)

```bash
# In .env
STORAGE_BACKEND=s3
S3_BUCKET=your-rag-documents
AWS_REGION=us-east-1

# If not using IAM role:
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

Then sync your local data to S3:

```python
from storage import get_storage

storage = get_storage()
storage.sync_from_local("data/documents", "documents")
```

## Backward Compatibility

### Old RAGAgent Still Works (Temporarily)

If you want to keep the old agent temporarily:

```bash
# Rename it
mv rag_agent.py rag_agent_legacy.py

# Import in your code
from rag_agent_legacy import RAGAgent  # Old agent
```

But migrate ASAP to benefit from new features!

## Common Issues

### Issue 1: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'config'
```

**Solution:**
```bash
# Make sure you're in the project root
cd Rag-Project

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Issue 2: Configuration Not Loading

**Error:**
```
ValidationError: GROQ_API_KEY field required
```

**Solution:**
```bash
# Check .env exists
ls -la .env

# Check format
cat .env | grep GROQ_API_KEY

# Verify it's loaded
python -c "from config import settings; print(settings.GROQ_API_KEY[:10])"
```

### Issue 3: Old Data Not Found

**Error:**
```
FileNotFoundError: data/documents not found
```

**Solution:**
```bash
# Check data structure
ls -R data/

# Verify settings
python -c "from config import settings; print(settings.LOCAL_DOCUMENTS_DIR)"

# Update .env if paths differ
LOCAL_DOCUMENTS_DIR=documents  # If your docs are here
```

### Issue 4: S3 Permission Denied

**Error:**
```
botocore.exceptions.ClientError: Access Denied
```

**Solution:**
```bash
# Check AWS credentials
aws configure list

# Test S3 access
aws s3 ls s3://your-bucket

# Verify IAM permissions include:
# - s3:GetObject
# - s3:PutObject
# - s3:ListBucket
```

## Performance Improvements

After migration, you should see:

1. **Faster Startup**: Model lazy loading
2. **Better Memory**: Models cached, not reloaded
3. **Improved Retrieval**: Hybrid search + reranking
4. **Lower API Costs**: Context truncation and caching
5. **Easier Debugging**: Structured logs and metrics

## Rollback Plan

If something goes wrong:

```bash
# Stop new server
# Ctrl+C or kill process

# Restore backup
rm -rf Rag-Project
mv Rag-Project-backup Rag-Project
cd Rag-Project

# Restore old .env
mv .env.backup .env

# Restore database
mv data/users.db.backup data/users.db

# Start old server
python app.py
```

## Next Steps

1. **Read Architecture Docs**: Understand new structure
   ```bash
   cat docs/ARCHITECTURE.md
   ```

2. **Explore New Features**: Try hybrid search, query expansion
   ```bash
   cat docs/DEPLOYMENT.md
   ```

3. **Deploy to Cloud**: Use new AWS deployment options
   ```bash
   cat docs/DEPLOYMENT.md
   ```

4. **Monitor Performance**: Check logs and metrics
   ```bash
   tail -f logs/app.log
   ```

## Support

If you encounter issues during migration:

1. Check logs: `logs/app.log`
2. Review error messages carefully
3. Consult documentation in `docs/`
4. Open GitHub issue with:
   - Error message
   - Steps to reproduce
   - Environment details

## Migration Checklist

- [ ] Backed up current system
- [ ] Updated .env with new format
- [ ] Installed new dependencies
- [ ] Reorganized data directories
- [ ] Updated code references (if modified)
- [ ] Tested all endpoints
- [ ] Verified existing data works
- [ ] Enabled new features
- [ ] Reviewed logs for errors
- [ ] Updated deployment scripts
- [ ] Documented custom changes

---

**Questions?** See [ARCHITECTURE.md](ARCHITECTURE.md) or [DEPLOYMENT.md](DEPLOYMENT.md)
