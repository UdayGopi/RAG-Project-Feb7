# 🚀 Production-Grade RAG Application

A modular, scalable, cloud-ready Retrieval-Augmented Generation (RAG) system built with modern best practices.

## ✨ Key Features

### 🏗️ Production Architecture
- **Modular Design**: Clean separation of concerns across 10+ modules
- **Cloud-Ready**: Seamless switching between local and S3/Azure storage
- **Multi-Tenant**: Isolated data and indexes per tenant
- **Scalable**: Horizontal and vertical scaling support

### 🤖 Advanced RAG
- **Hybrid Retrieval**: Combines semantic (embeddings) and keyword (BM25) search
- **Query Expansion**: HyDE, multi-query, and synonym expansion
- **Smart Reranking**: Cross-encoder reranking for precision
- **Metadata Filtering**: Pre-filter documents by type, tenant, date
- **Context Management**: Intelligent token-aware context truncation

### 🔌 Flexible Models
- **Multiple LLM Providers**: Groq, OpenAI, Anthropic, Ollama
- **Multiple Embeddings**: HuggingFace, OpenAI, Cohere
- **Hot-Swapping**: Switch models without restart
- **Model Registry**: Central catalog of available models
- **Lazy Loading**: Load models on-demand for efficiency

### 💾 Storage Options
- **Local**: Filesystem storage for development
- **AWS S3**: Production cloud storage with versioning
- **Azure Blob**: Alternative cloud storage
- **Hybrid**: Local cache with cloud backup

### 🔐 Security & Auth
- **JWT Authentication**: Secure API access
- **OAuth 2.0**: Google and Microsoft login
- **Role-Based Access**: Admin and user roles
- **Tenant Isolation**: Data segregation

### 📊 Monitoring
- **Structured Logging**: JSON logs for easy parsing
- **Metrics**: Query latency, error rates, usage stats
- **Health Checks**: Kubernetes-ready health endpoints
- **CloudWatch Integration**: AWS native monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- pip or conda
- Groq API key (free at https://groq.com)

### Local Development

```bash
# Clone repository
git clone <your-repo-url>
cd Rag-Project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your GROQ_API_KEY

# Run application
python app.py
```

Access at: **http://localhost:5001**

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

## 📁 Project Structure

```
Rag-Project/
│
├── config/                    # 🔧 Configuration
│   ├── settings.py           # Centralized settings
│   ├── models.py             # Model configurations
│   ├── storage.py            # Storage configs
│   └── constants.py          # App constants
│
├── core/                      # 🤖 Core RAG Components
│   ├── llm.py                # LLM management
│   ├── embeddings.py         # Embedding models
│   ├── chunking.py           # Document chunking
│   └── reranking.py          # Reranking models
│
├── agents/                    # 🧠 Agent Logic
│   ├── rag_agent.py          # Main RAG agent
│   ├── query_router.py       # Multi-tenant routing
│   └── intent_classifier.py  # Intent detection
│
├── storage/                   # 💾 Storage Abstraction
│   ├── base.py               # Storage interface
│   ├── local_storage.py      # Local filesystem
│   ├── s3_storage.py         # AWS S3
│   └── factory.py            # Storage factory
│
├── retrieval/                 # 🔍 Advanced Retrieval
│   ├── hybrid_search.py      # BM25 + Semantic
│   ├── query_expansion.py    # Query rewriting
│   ├── rag_fusion.py         # Multi-query fusion
│   └── filters.py            # Metadata filtering
│
├── models/                    # 📦 Model Management
│   ├── model_registry.py     # Available models
│   ├── model_loader.py       # Lazy loading
│   └── model_cache.py        # Model caching
│
├── ingestion/                 # 📄 Document Processing
│   ├── processors.py         # PDF, DOCX parsers
│   ├── extractors.py         # Table extraction
│   └── web_scraper.py        # URL ingestion
│
├── database/                  # 💽 Data Layer
│   ├── users.py              # User management
│   └── cache.py              # Response caching
│
├── api/                       # 🌐 API Routes
│   ├── auth.py               # Authentication
│   ├── chat.py               # Chat endpoints
│   └── upload.py             # File upload
│
├── utils/                     # 🛠️ Utilities
│   ├── logging.py            # Custom logging
│   └── metrics.py            # Metrics tracking
│
├── static/                    # 🎨 Frontend
│   ├── index.html
│   └── care-policy-hub.html
│
├── docs/                      # 📚 Documentation
│   ├── DEPLOYMENT.md         # Deployment guide
│   ├── ARCHITECTURE.md       # System architecture
│   └── MIGRATION.md          # Migration guide
│
├── app.py                     # 🚪 Main application
├── requirements.txt           # 📦 Dependencies
├── Dockerfile                 # 🐳 Docker config
├── docker-compose.yml         # 🐳 Compose config
└── .env.example               # ⚙️ Environment template
```

## ⚙️ Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Storage Backend
STORAGE_BACKEND=local  # or 's3', 'azure'

# LLM Provider
LLM_PROVIDER=groq      # or 'openai', 'anthropic', 'ollama'
LLM_MODEL=llama-3.1-8b-instant

# Embedding Provider
EMBEDDING_PROVIDER=huggingface  # or 'openai', 'cohere'
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5

# Retrieval Strategy
RETRIEVAL_MODE=semantic  # or 'hybrid', 'fusion'
ENABLE_QUERY_EXPANSION=false
```

### Switching to Cloud Storage (S3)

```bash
# In .env
STORAGE_BACKEND=s3
S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1
# Leave AWS keys empty to use IAM role
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

### Switching LLM Provider

```bash
# Use OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_openai_key

# Use Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=your_anthropic_key

# Use Local Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama3
```

## 🔍 Advanced RAG Features

### 1. Hybrid Search

Combines semantic and keyword search for better results:

```python
# Enable in .env
RETRIEVAL_MODE=hybrid
```

### 2. Query Expansion

Generate multiple query variations:

```python
# Enable in .env
ENABLE_QUERY_EXPANSION=true
QUERY_EXPANSION_COUNT=2
```

### 3. Metadata Filtering

Filter by document type, tenant, date:

```python
from retrieval.filters import MetadataFilter

# In your code
filters = MetadataFilter.create_tenant_filter("HIH")
```

### 4. Context Truncation

Smart token-aware context management:

```python
# Configure in .env
MAX_CONTEXT_TOKENS=3500
MAX_PROMPT_TOKENS=5500
```

## 🚀 Deployment

### Local Development

```bash
python app.py
```

### Production with Gunicorn

```bash
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 300 app:app
```

### Docker

```bash
docker build -t rag-app .
docker run -p 5001:5001 --env-file .env rag-app
```

### AWS EC2

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete guide.

## 📊 API Endpoints

### Authentication

```bash
# Sign in
POST /auth/signin
{
  "email": "user@example.com",
  "password": "password"
}

# Sign up
POST /auth/signup
{
  "name": "John Doe",
  "email": "user@example.com",
  "password": "password"
}
```

### Chat

```bash
# Send query
POST /chat
{
  "query": "What are the HIH onboarding steps?",
  "tenant_id": "HIH"  # optional
}

# Response
{
  "summary": "...",
  "detailed_response": "...",
  "sources": [...],
  "confidence": 0.92
}
```

### Upload

```bash
# Upload document
POST /upload
Content-Type: multipart/form-data
- file: document.pdf
- tenant_id: HIH
```

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# Specific test
pytest tests/test_rag_agent.py
```

## 📈 Monitoring

### Health Check

```bash
GET /health

# Response
{
  "status": "healthy",
  "version": "2.0.0",
  "storage": "local"
}
```

### Logs

```bash
# View logs
tail -f logs/app.log

# Docker logs
docker logs -f rag-app
```

## 🔧 Troubleshooting

### Common Issues

**1. Module not found**
```bash
pip install -r requirements.txt --force-reinstall
```

**2. S3 permission denied**
- Check AWS credentials
- Verify IAM role permissions
- Test with AWS CLI: `aws s3 ls s3://your-bucket`

**3. Model loading slow**
- First load downloads model (~100-500MB)
- Subsequent loads use cache
- Use smaller models: `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5`

**4. Out of memory**
- Reduce workers: `gunicorn --workers 2`
- Use smaller chunk size: `CHUNK_SIZE=512`
- Use lighter models

## 🎯 Roadmap

- [ ] Agentic RAG (iterative retrieval)
- [ ] Multi-modal support (images, tables)
- [ ] GraphRAG integration
- [ ] Real-time streaming
- [ ] Advanced caching (Redis)
- [ ] A/B testing framework
- [ ] Fine-tuned models
- [ ] Federated search

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Deployment](docs/DEPLOYMENT.md) - Deployment guides for AWS, Docker
- [Migration](docs/MIGRATION.md) - Migrate from old structure
- [API Documentation](docs/API.md) - Detailed API reference

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License.

## 💡 Support

- **Issues**: Open GitHub issue
- **Docs**: Check [docs/](docs/) folder
- **Email**: your-email@example.com

---

**Built with ❤️ for production-grade RAG applications**
