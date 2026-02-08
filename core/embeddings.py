"""
Embedding model management with support for multiple providers.
"""
import logging
from typing import Optional
from config import settings


def get_embedding_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    Get embedding model instance based on provider.
    
    Args:
        provider: Embedding provider ('huggingface', 'openai', 'cohere')
        model_name: Specific model name
        api_key: API key (if different from settings)
        
    Returns:
        Embedding model instance compatible with LlamaIndex
    """
    provider = provider or settings.EMBEDDING_PROVIDER
    model_name = model_name or settings.EMBEDDING_MODEL
    
    logging.info(f"Initializing embeddings: {provider}/{model_name}")
    
    if provider == "huggingface":
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        
        return HuggingFaceEmbedding(
            model_name=model_name,
            cache_folder=settings.LOCAL_MODELS_DIR
        )
    
    elif provider == "openai":
        from llama_index.embeddings.openai import OpenAIEmbedding
        
        if not api_key:
            api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY required for OpenAI embeddings")
        
        return OpenAIEmbedding(
            model=model_name,
            api_key=api_key
        )
    
    elif provider == "cohere":
        from llama_index.embeddings.cohere import CohereEmbedding
        
        if not api_key:
            api_key = settings.COHERE_API_KEY
        if not api_key:
            raise ValueError("COHERE_API_KEY required for Cohere embeddings")
        
        return CohereEmbedding(
            model_name=model_name,
            api_key=api_key
        )
    
    elif provider == "bedrock":
        try:
            from llama_index.embeddings.bedrock import BedrockEmbedding
        except ImportError:
            raise ImportError(
                "Bedrock embeddings require: pip install llama-index-embeddings-bedrock boto3"
            )
        return BedrockEmbedding(
            model_name=settings.BEDROCK_EMBEDDING_MODEL,
            region_name=settings.AWS_REGION or "us-east-1",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    
    elif provider == "local":
        # Use sentence-transformers directly
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        return HuggingFaceEmbedding(
            model_name=model_name or "sentence-transformers/all-MiniLM-L6-v2",
            cache_folder=settings.LOCAL_MODELS_DIR
        )
    
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")


class EmbeddingManager:
    """Manages embedding models with caching."""
    
    def __init__(self):
        self._embedding_cache = {}
        self._current_provider = settings.EMBEDDING_PROVIDER
        self._current_model = settings.EMBEDDING_MODEL
    
    def get_embedding_model(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """Get or create embedding model with caching."""
        provider = provider or self._current_provider
        model_name = model_name or self._current_model
        
        cache_key = f"{provider}:{model_name}"
        
        if cache_key not in self._embedding_cache:
            self._embedding_cache[cache_key] = get_embedding_model(provider, model_name)
            logging.info(f"Cached new embedding model: {cache_key}")
        
        return self._embedding_cache[cache_key]
    
    def switch_embedding(self, provider: str, model_name: str):
        """Switch to different embedding model."""
        logging.info(f"Switching embeddings: {provider}/{model_name}")
        self._current_provider = provider
        self._current_model = model_name
        return self.get_embedding_model(provider, model_name)
    
    def get_dimension(self) -> int:
        """Get embedding dimension for current model."""
        # This could be improved by querying the model directly
        from config.models import EMBEDDING_MODELS
        for key, config in EMBEDDING_MODELS.items():
            if config.model_name == self._current_model:
                return config.dimension
        return 384  # Default
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._embedding_cache.clear()
        logging.info("Embedding cache cleared")


# Global embedding manager
_embedding_manager = EmbeddingManager()


def get_default_embedding_model():
    """Get default embedding model instance."""
    return _embedding_manager.get_embedding_model()


def switch_embedding(provider: str, model_name: str):
    """Switch to different embedding model globally."""
    return _embedding_manager.switch_embedding(provider, model_name)


def get_embedding_dimension() -> int:
    """Get current embedding dimension."""
    return _embedding_manager.get_dimension()
