"""
Storage backend configuration.
Supports local filesystem, AWS S3, and Azure Blob Storage.
"""
from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class StorageConfig:
    """Storage backend configuration."""
    backend: Literal["local", "s3", "azure"]
    
    # Local settings
    local_base_path: Optional[str] = None
    
    # AWS S3 settings
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = "us-east-1"
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None
    s3_endpoint_url: Optional[str] = None  # For MinIO or custom S3
    
    # Azure settings
    azure_connection_string: Optional[str] = None
    azure_container: Optional[str] = None
    
    # Performance settings
    upload_chunk_size: int = 5 * 1024 * 1024  # 5MB chunks
    download_timeout: int = 300  # 5 minutes
    max_retries: int = 3
    
    @classmethod
    def from_settings(cls, settings):
        """Create StorageConfig from Settings object."""
        return cls(
            backend=settings.STORAGE_BACKEND,
            local_base_path=settings.LOCAL_DOCUMENTS_DIR,
            s3_bucket=settings.S3_BUCKET,
            s3_region=settings.AWS_REGION,
            s3_access_key=settings.AWS_ACCESS_KEY_ID,
            s3_secret_key=settings.AWS_SECRET_ACCESS_KEY,
            azure_connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
            azure_container=settings.AZURE_CONTAINER_NAME
        )
    
    def is_cloud(self) -> bool:
        """Check if using cloud storage."""
        return self.backend in ["s3", "azure"]
    
    def is_s3_configured(self) -> bool:
        """Check if S3 is properly configured."""
        return self.backend == "s3" and bool(self.s3_bucket)
    
    def is_azure_configured(self) -> bool:
        """Check if Azure is properly configured."""
        return self.backend == "azure" and bool(self.azure_connection_string)
    
    def validate(self) -> bool:
        """Validate storage configuration."""
        if self.backend == "local":
            return bool(self.local_base_path)
        elif self.backend == "s3":
            return self.is_s3_configured()
        elif self.backend == "azure":
            return self.is_azure_configured()
        return False


@dataclass
class VectorStoreConfig:
    """Vector store configuration."""
    store_type: Literal["local", "pinecone", "qdrant", "weaviate"] = "local"
    
    # Pinecone
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    
    # Qdrant
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_collection: Optional[str] = None
    
    # Weaviate
    weaviate_url: Optional[str] = None
    weaviate_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls):
        """Create from environment variables."""
        import os
        return cls(
            store_type=os.getenv("VECTOR_STORE", "local"),
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            pinecone_environment=os.getenv("PINECONE_ENV"),
            pinecone_index_name=os.getenv("PINECONE_INDEX"),
            qdrant_url=os.getenv("QDRANT_URL"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION"),
            weaviate_url=os.getenv("WEAVIATE_URL"),
            weaviate_api_key=os.getenv("WEAVIATE_API_KEY")
        )
