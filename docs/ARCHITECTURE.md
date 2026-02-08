# 🏗️ System Architecture

## Overview

This is a production-grade, multi-tenant RAG (Retrieval-Augmented Generation) system designed for scalability, modularity, and easy cloud deployment.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Web UI  │  │   API    │  │  Mobile  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                    API Layer (Flask)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   Auth   │  │   Chat   │  │  Upload  │  │Analytics │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
└───────┼─────────────┼─────────────┼─────────────┼───────────┘
        │             │             │             │
┌───────▼─────────────▼─────────────▼─────────────▼───────────┐
│                    Business Logic Layer                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           RAG Agent (Multi-Tenant Router)            │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐          │    │
│  │  │ Tenant A │  │ Tenant B │  │ Tenant C │          │    │
│  │  │  Index   │  │  Index   │  │  Index   │          │    │
│  │  └──────────┘  └──────────┘  └──────────┘          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Retrieval  │  │    Models    │  │  Ingestion   │      │
│  │  - Hybrid    │  │  - LLM Mgmt  │  │  - Parsers   │      │
│  │  - Fusion    │  │  - Embedding │  │  - Chunking  │      │
│  │  - Filters   │  │  - Reranking │  │  - Cleanup   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                   Infrastructure Layer                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Storage │  │   Cache  │  │    DB    │  │  Metrics │    │
│  │ (S3/Local)│  │  (Redis) │  │ (SQLite) │  │(CloudWatch)│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└───────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼─────────────────────────────────────────┐
│                   External Services                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │   Groq   │  │  OpenAI  │  │   AWS    │                    │
│  │   LLM    │  │   LLM    │  │   S3     │                    │
│  └──────────┘  └──────────┘  └──────────┘                    │
└───────────────────────────────────────────────────────────────┘
```

## Module Structure

### 1. Configuration (`config/`)

Centralized configuration management using Pydantic for validation.

- **`settings.py`**: All environment variables and app settings
- **`models.py`**: Model configurations (LLM, embeddings, rerankers)
- **`storage.py`**: Storage backend configuration
- **`constants.py`**: Application constants and enums

**Key Features:**
- Type-safe configuration with Pydantic
- Environment variable validation
- Easy switching between dev/staging/prod
- Default values with override capability

### 2. Storage (`storage/`)

Abstraction layer for document and index storage.

- **`base.py`**: Abstract storage interface
- **`local_storage.py`**: Local filesystem implementation
- **`s3_storage.py`**: AWS S3 implementation
- **`azure_storage.py`**: Azure Blob Storage (optional)
- **`factory.py`**: Storage factory and global instance

**Key Features:**
- Unified interface for local and cloud storage
- Easy switching via configuration
- Presigned URL support for secure access
- Sync utilities for cache management

### 3. Core RAG Components (`core/`)

Fundamental RAG building blocks.

- **`llm.py`**: LLM management and switching
- **`embeddings.py`**: Embedding model management
- **`chunking.py`**: Document chunking strategies
- **`reranking.py`**: Reranking models

**Key Features:**
- Support for multiple providers (Groq, OpenAI, Anthropic, Ollama)
- Model caching for performance
- Hot-swapping models without restart
- Preset chunking strategies

### 4. Models (`models/`)

Model registry, loading, and caching.

- **`model_registry.py`**: Central registry of available models
- **`model_loader.py`**: Lazy loading with caching
- **`model_cache.py`**: Local model file caching

**Key Features:**
- Metadata for all available models
- Lazy loading to save memory
- Disk caching for cloud-stored models
- Version tracking

### 5. Retrieval (`retrieval/`)

Advanced retrieval strategies.

- **`hybrid_search.py`**: BM25 + Semantic search with RRF
- **`query_expansion.py`**: Query rewriting and expansion
- **`rag_fusion.py`**: Multi-query retrieval with fusion
- **`filters.py`**: Metadata filtering

**Key Features:**
- Hybrid search for better precision
- Query expansion techniques (HyDE, Multi-Query)
- Reciprocal Rank Fusion (RRF)
- Intelligent metadata filtering

### 6. Agents (`agents/`)

RAG agent implementations.

- **`base_agent.py`**: Abstract agent interface
- **`rag_agent.py`**: Main RAG agent (refactored)
- **`query_router.py`**: Multi-tenant routing
- **`intent_classifier.py`**: Query intent detection

**Key Features:**
- Multi-tenant support
- Intent-based routing
- Confidence scoring
- Fallback handling

### 7. Ingestion (`ingestion/`)

Document processing pipeline.

- **`processors.py`**: Document parsers (PDF, DOCX, etc.)
- **`extractors.py`**: Table and image extraction
- **`web_scraper.py`**: URL ingestion
- **`validators.py`**: File validation

**Key Features:**
- Multiple document format support
- Table extraction
- Web scraping with domain whitelisting
- File size and type validation

### 8. Database (`database/`)

Data persistence layer.

- **`users.py`**: User management
- **`cache.py`**: Response caching
- **`analytics.py`**: Query analytics

**Key Features:**
- SQLite for development
- PostgreSQL-ready for production
- Query caching
- Usage analytics

### 9. API (`api/`)

Flask route organization.

- **`auth.py`**: Authentication routes
- **`chat.py`**: Chat endpoints
- **`upload.py`**: Document upload
- **`analytics.py`**: Analytics endpoints

**Key Features:**
- Clean separation of concerns
- JWT authentication
- OAuth support (Google, Microsoft)
- Rate limiting ready

### 10. Utils (`utils/`)

Shared utilities.

- **`logging.py`**: Custom logging
- **`metrics.py`**: Performance tracking
- **`validators.py`**: Input validation
- **`helpers.py`**: Helper functions

## Data Flow

### 1. Query Processing

```
User Query
    │
    ▼
Intent Classification
    │
    ├─> Small Talk ──> Canned Response
    ├─> Download   ──> File Retrieval
    └─> Question   ──> Continue
            │
            ▼
    Query Expansion (Optional)
            │
            ▼
    Tenant Detection
            │
            ▼
    Multi-Tenant Router
            │
            ▼
    Retrieval (Hybrid/Semantic)
            │
            ▼
    Reranking
            │
            ▼
    Context Truncation
            │
            ▼
    LLM Generation
            │
            ▼
    Response Formatting
            │
            ▼
    Return to User
```

### 2. Document Ingestion

```
Upload File/URL
    │
    ▼
Validation
    │
    ▼
Storage (S3/Local)
    │
    ▼
Document Parsing
    │
    ▼
Chunking
    │
    ▼
Embedding Generation
    │
    ▼
Vector Index Update
    │
    ▼
Success Response
```

## Scaling Strategies

### Horizontal Scaling

- **Load Balancer**: AWS ALB/ELB distributes traffic
- **Multiple Instances**: Auto-scaling group of EC2/ECS
- **Shared Storage**: S3 for documents and indexes
- **Shared Database**: PostgreSQL RDS

### Vertical Scaling

- **Larger Instances**: Increase CPU/RAM
- **GPU Instances**: For local model inference
- **Optimized Models**: Use smaller, faster models

### Caching

- **Response Cache**: Redis for frequent queries
- **Model Cache**: Local disk for downloaded models
- **CDN**: CloudFront for static assets

### Async Processing

- **Background Jobs**: Celery for long-running tasks
- **Message Queue**: SQS for async ingestion
- **Batch Processing**: Lambda for scheduled tasks

## Security

### Authentication

- **JWT Tokens**: For API authentication
- **OAuth 2.0**: Google and Microsoft login
- **Session Management**: Secure session handling

### Authorization

- **Role-Based Access**: Admin, User roles
- **Tenant Isolation**: Data segregation by tenant
- **API Keys**: For programmatic access

### Data Protection

- **Encryption at Rest**: S3 server-side encryption
- **Encryption in Transit**: HTTPS/TLS
- **Secrets Management**: AWS Secrets Manager
- **Input Validation**: Prevent injection attacks

## Monitoring & Observability

### Logging

- **Structured Logging**: JSON format for parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **CloudWatch Logs**: Centralized log aggregation

### Metrics

- **Application Metrics**: Query latency, error rate
- **Infrastructure Metrics**: CPU, memory, disk
- **Business Metrics**: Queries per day, user engagement

### Tracing

- **AWS X-Ray**: Distributed tracing
- **Request IDs**: Track requests across services
- **Performance Profiling**: Identify bottlenecks

### Alerting

- **CloudWatch Alarms**: CPU, error rate, latency
- **SNS Notifications**: Email/SMS alerts
- **PagerDuty Integration**: On-call rotation

## Deployment Options

### 1. EC2 (Traditional)
- Full control over environment
- Easy to debug and monitor
- Suitable for steady traffic

### 2. ECS/Fargate (Containers)
- Scalable and managed
- Easy rolling updates
- Pay per use

### 3. Lambda (Serverless)
- Cost-effective for low traffic
- Auto-scaling
- Cold start considerations

### 4. Kubernetes (Advanced)
- Maximum flexibility
- Complex setup
- Best for large-scale

## Future Enhancements

1. **Multi-Modal RAG**: Support images, tables, charts
2. **Agentic RAG**: Iterative retrieval with reasoning
3. **Self-RAG**: Self-reflection and verification
4. **Graph RAG**: Knowledge graph integration
5. **Fine-Tuned Models**: Domain-specific fine-tuning
6. **Real-Time Updates**: Streaming ingestion
7. **Federated Search**: Cross-tenant search
8. **A/B Testing**: Compare retrieval strategies

## Performance Benchmarks

Target metrics for production:

- **Query Latency**: < 2s (p95)
- **Retrieval Precision**: > 0.85
- **Retrieval Recall**: > 0.90
- **Uptime**: > 99.9%
- **Concurrent Users**: 100+

## Cost Optimization

- **Use free-tier LLMs** (Groq) for development
- **S3 Intelligent-Tiering** for cost-effective storage
- **Spot Instances** for non-critical workloads
- **Model caching** to reduce API calls
- **Query deduplication** and caching

---

For deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).
For API documentation, see [API.md](API.md).
