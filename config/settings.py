"""
Centralized settings management using Pydantic for validation.
All environment variables are loaded and validated here.
"""
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, Dict, Literal
import json
import os


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""
    
    # ==================== Application ====================
    APP_NAME: str = Field(default="CarePolicy RAG Hub", description="Application name")
    APP_VERSION: str = Field(default="2.0.0", description="Application version")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development", 
        description="Deployment environment"
    )
    DEBUG: bool = Field(default=True, description="Debug mode")
    PORT: int = Field(default=5001, description="Server port")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    
    # ==================== Security ====================
    SECRET_KEY: str = Field(default="dev_secret_change_me", description="Flask secret key")
    JWT_SECRET: str = Field(default="", description="JWT signing secret")
    JWT_EXPIRES_MIN: int = Field(default=10080, description="JWT expiration in minutes (7 days)")
    
    # ==================== API Keys ====================
    GROQ_API_KEY: str = Field(..., description="Groq API key (required)")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key (optional)")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key (optional)")
    COHERE_API_KEY: Optional[str] = Field(default=None, description="Cohere API key (optional)")
    
    # ==================== Models ====================
    LLM_PROVIDER: Literal["groq", "openai", "anthropic", "ollama"] = Field(
        default="groq",
        description="LLM provider to use"
    )
    LLM_MODEL: str = Field(default="llama-3.1-8b-instant", description="LLM model name")
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0, description="LLM temperature")
    LLM_MAX_TOKENS: int = Field(default=2048, description="Max tokens for LLM response")
    
    EMBEDDING_PROVIDER: Literal["huggingface", "openai", "cohere", "bedrock", "local"] = Field(
        default="huggingface",
        description="Embedding provider"
    )
    EMBEDDING_MODEL: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Embedding model name"
    )
    EMBEDDING_DIMENSION: int = Field(default=384, description="Embedding dimension")
    
    # Amazon Bedrock (AWS-native embeddings)
    BEDROCK_EMBEDDING_MODEL: str = Field(
        default="amazon.titan-embed-text-v1",
        description="Bedrock embedding model (e.g. amazon.titan-embed-text-v1, amazon.titan-embed-g1-text-02)"
    )
    
    RERANKER_MODEL: str = Field(
        default="BAAI/bge-reranker-base",
        description="Reranking model"
    )
    
    # ==================== Storage Backend ====================
    STORAGE_BACKEND: Literal["local", "s3", "azure"] = Field(
        default="local",
        description="Storage backend type"
    )
    
    # Local Storage
    LOCAL_DOCUMENTS_DIR: str = Field(default="data/documents", description="Local documents directory")
    LOCAL_STORAGE_DIR: str = Field(default="data/storage", description="Local vector storage directory")
    LOCAL_CACHE_DIR: str = Field(default="data/cache", description="Local cache directory")
    LOCAL_MODELS_DIR: str = Field(default="data/models", description="Local models directory")
    
    # AWS S3 Storage
    AWS_REGION: Optional[str] = Field(default="us-east-1", description="AWS region")
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS access key")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS secret key")
    S3_BUCKET: Optional[str] = Field(default=None, description="S3 bucket for documents")
    S3_DOCUMENTS_PREFIX: str = Field(default="documents", description="S3 prefix for documents")
    S3_INDEXES_PREFIX: str = Field(default="indexes", description="S3 prefix for vector indexes")
    S3_MODELS_PREFIX: str = Field(default="models", description="S3 prefix for models")
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = Field(default=None)
    AZURE_CONTAINER_NAME: Optional[str] = Field(default=None)
    
    # ==================== RAG Configuration ====================
    CHUNK_SIZE: int = Field(default=1024, ge=128, le=4096, description="Document chunk size")
    CHUNK_OVERLAP: int = Field(default=100, ge=0, le=512, description="Chunk overlap")
    
    SIMILARITY_TOP_K: int = Field(default=10, ge=1, le=50, description="Initial retrieval count")
    SIMILARITY_CUTOFF: float = Field(default=0.5, ge=0.0, le=1.0, description="Similarity threshold")
    RERANK_TOP_N: int = Field(default=3, ge=1, le=10, description="Final reranked results")
    
    MAX_CONTEXT_TOKENS: int = Field(default=3500, description="Max tokens for context")
    MAX_PROMPT_TOKENS: int = Field(default=5500, description="Max tokens for entire prompt")
    
    # ==================== Retrieval Strategy ====================
    RETRIEVAL_MODE: Literal["semantic", "hybrid", "fusion"] = Field(
        default="semantic",
        description="Retrieval strategy: semantic (current), hybrid (BM25+semantic), fusion (multi-query)"
    )
    ENABLE_QUERY_EXPANSION: bool = Field(default=False, description="Enable query expansion")
    QUERY_EXPANSION_COUNT: int = Field(default=2, ge=1, le=5, description="Number of query variations")
    
    # ==================== Feature Toggles ====================
    CLEANING_ENABLED: bool = Field(default=True, description="Enable text cleaning")
    TABLE_EXTRACT_ENABLED: bool = Field(default=True, description="Enable table extraction")
    CACHE_ENABLED: bool = Field(default=True, description="Enable response caching")
    CACHE_TTL_HOURS: int = Field(default=24, description="Cache time-to-live in hours")
    
    # ==================== Tenant Configuration ====================
    TENANT_HIGH_CONF_THRESH: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Confidence threshold for direct routing"
    )
    TENANT_MIN_CONF_THRESH: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence to proceed"
    )
    
    TENANT_ALIASES: Dict[str, str] = Field(
        default_factory=lambda: {
            "hih": "HIH",
            "health information handler": "HIH",
            "handler": "HIH",
            "rc": "RC",
            "review contractor": "RC",
            "review contractors": "RC",
        },
        description="Tenant name aliases"
    )
    
    # ==================== OAuth ====================
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None)
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None)
    MS_CLIENT_ID: Optional[str] = Field(default=None)
    MS_CLIENT_SECRET: Optional[str] = Field(default=None)
    APP_BASE_URL: str = Field(default="http://127.0.0.1:5001")
    
    # ==================== Database ====================
    DATABASE_PATH: str = Field(default="data/users.db", description="SQLite database path")
    
    # ==================== Vector Storage (for embeddings/indexes) ====================
    VECTOR_STORE: Literal["local", "qdrant", "pinecone", "opensearch"] = Field(
        default="local",
        description="Vector database type"
    )
    
    # Qdrant (Recommended for production)
    QDRANT_URL: Optional[str] = Field(default="http://localhost:6333", description="Qdrant URL")
    QDRANT_API_KEY: Optional[str] = Field(default=None, description="Qdrant API key")
    QDRANT_COLLECTION: str = Field(default="rag_documents", description="Qdrant collection name")
    
    # Pinecone (Managed service)
    PINECONE_API_KEY: Optional[str] = Field(default=None, description="Pinecone API key")
    PINECONE_ENV: str = Field(default="us-west1-gcp", description="Pinecone environment")
    PINECONE_INDEX: str = Field(default="rag-index", description="Pinecone index name")
    
    # OpenSearch (AWS native - use for vector store on AWS)
    OPENSEARCH_HOST: Optional[str] = Field(default=None, description="OpenSearch host (e.g. search-xxx.us-east-1.es.amazonaws.com)")
    OPENSEARCH_PORT: int = Field(default=443, description="OpenSearch port (443 for AWS)")
    OPENSEARCH_USER: str = Field(default="admin", description="OpenSearch username")
    OPENSEARCH_PASSWORD: Optional[str] = Field(default=None, description="OpenSearch password")
    OPENSEARCH_INDEX: str = Field(default="rag_documents", description="OpenSearch index name")
    OPENSEARCH_USE_SSL: bool = Field(default=True, description="Use HTTPS for OpenSearch (True for AWS)")
    
    # ==================== Monitoring ====================
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    ENABLE_TRACING: bool = Field(default=False, description="Enable detailed tracing")
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/app.log", description="Log file path")
    
    # ==================== Performance ====================
    ASYNC_ENABLED: bool = Field(default=False, description="Enable async processing")
    MAX_WORKERS: int = Field(default=4, ge=1, le=32, description="Thread pool size")
    REQUEST_TIMEOUT: int = Field(default=300, description="Request timeout in seconds")
    
    @validator("JWT_SECRET", pre=True, always=True)
    def set_jwt_secret(cls, v, values):
        """Use SECRET_KEY as JWT_SECRET if not provided."""
        return v or values.get("SECRET_KEY", "dev_secret_change_me")
    
    @validator("TENANT_ALIASES", pre=True)
    def parse_tenant_aliases(cls, v):
        """Parse TENANT_ALIASES from JSON string if provided."""
        if isinstance(v, str) and v.strip():
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if isinstance(v, dict) else {}
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields


# Global settings instance
settings = Settings()


# Helper functions for common paths
def get_tenant_documents_path(tenant_id: str, storage_backend: str = None) -> str:
    """Get path for tenant documents based on storage backend."""
    backend = storage_backend or settings.STORAGE_BACKEND
    
    if backend == "local":
        return os.path.join(settings.LOCAL_DOCUMENTS_DIR, tenant_id)
    elif backend == "s3":
        return f"{settings.S3_DOCUMENTS_PREFIX}/{tenant_id}"
    elif backend == "azure":
        return f"documents/{tenant_id}"
    else:
        raise ValueError(f"Unsupported storage backend: {backend}")


def get_tenant_storage_path(tenant_id: str, storage_backend: str = None) -> str:
    """Get path for tenant vector storage based on backend."""
    backend = storage_backend or settings.STORAGE_BACKEND
    
    if backend == "local":
        return os.path.join(settings.LOCAL_STORAGE_DIR, tenant_id)
    elif backend == "s3":
        return f"{settings.S3_INDEXES_PREFIX}/{tenant_id}"
    elif backend == "azure":
        return f"indexes/{tenant_id}"
    else:
        raise ValueError(f"Unsupported storage backend: {backend}")


def is_cloud_storage() -> bool:
    """Check if cloud storage is being used."""
    return settings.STORAGE_BACKEND in ["s3", "azure"]


def get_model_cache_path(model_name: str) -> str:
    """Get local cache path for a model."""
    safe_name = model_name.replace("/", "_").replace(":", "_")
    return os.path.join(settings.LOCAL_MODELS_DIR, safe_name)
