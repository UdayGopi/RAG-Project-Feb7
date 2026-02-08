"""
Model configurations for LLMs, embeddings, and rerankers.
Supports multiple providers with easy switching.
"""
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


@dataclass
class LLMConfig:
    """LLM model configuration."""
    provider: Literal["groq", "openai", "anthropic", "ollama"]
    model_name: str
    api_key: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 2048
    base_url: Optional[str] = None  # For Ollama or custom endpoints
    
    @property
    def display_name(self) -> str:
        """Human-readable model name."""
        return f"{self.provider.title()}: {self.model_name}"


@dataclass
class EmbeddingConfig:
    """Embedding model configuration."""
    provider: Literal["huggingface", "openai", "cohere", "local"]
    model_name: str
    dimension: int = 384
    api_key: Optional[str] = None
    batch_size: int = 32
    cache_folder: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Human-readable model name."""
        return f"{self.provider.title()}: {self.model_name}"


@dataclass
class RerankerConfig:
    """Reranking model configuration."""
    model_name: str = "BAAI/bge-reranker-base"
    top_n: int = 3
    batch_size: int = 32


# ==================== Predefined Model Configurations ====================

# LLM Options
LLM_MODELS: Dict[str, LLMConfig] = {
    # Groq (Fast, free tier)
    "groq-llama-3.1-8b": LLMConfig(
        provider="groq",
        model_name="llama-3.1-8b-instant",
        temperature=0.1,
        max_tokens=2048
    ),
    "groq-llama-3.1-70b": LLMConfig(
        provider="groq",
        model_name="llama-3.1-70b-versatile",
        temperature=0.1,
        max_tokens=4096
    ),
    
    # OpenAI (Best quality, paid)
    "openai-gpt-4": LLMConfig(
        provider="openai",
        model_name="gpt-4-turbo-preview",
        temperature=0.1,
        max_tokens=4096
    ),
    "openai-gpt-3.5": LLMConfig(
        provider="openai",
        model_name="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=2048
    ),
    
    # Anthropic (Good balance)
    "anthropic-claude-3": LLMConfig(
        provider="anthropic",
        model_name="claude-3-sonnet-20240229",
        temperature=0.1,
        max_tokens=4096
    ),
    
    # Ollama (Fully local, privacy)
    "ollama-llama3": LLMConfig(
        provider="ollama",
        model_name="llama3",
        temperature=0.1,
        max_tokens=2048,
        base_url="http://localhost:11434"
    ),
}

# Embedding Options
EMBEDDING_MODELS: Dict[str, EmbeddingConfig] = {
    # HuggingFace (Free, local)
    "bge-small": EmbeddingConfig(
        provider="huggingface",
        model_name="BAAI/bge-small-en-v1.5",
        dimension=384
    ),
    "bge-base": EmbeddingConfig(
        provider="huggingface",
        model_name="BAAI/bge-base-en-v1.5",
        dimension=768
    ),
    "bge-large": EmbeddingConfig(
        provider="huggingface",
        model_name="BAAI/bge-large-en-v1.5",
        dimension=1024
    ),
    
    # OpenAI (Best quality, paid)
    "openai-ada-002": EmbeddingConfig(
        provider="openai",
        model_name="text-embedding-ada-002",
        dimension=1536
    ),
    "openai-3-small": EmbeddingConfig(
        provider="openai",
        model_name="text-embedding-3-small",
        dimension=1536
    ),
    
    # Cohere (Good multilingual)
    "cohere-english": EmbeddingConfig(
        provider="cohere",
        model_name="embed-english-v3.0",
        dimension=1024
    ),
}

# Reranker Options
RERANKER_MODELS: Dict[str, RerankerConfig] = {
    "bge-reranker-base": RerankerConfig(
        model_name="BAAI/bge-reranker-base",
        top_n=3
    ),
    "bge-reranker-large": RerankerConfig(
        model_name="BAAI/bge-reranker-large",
        top_n=3
    ),
    "cohere-rerank": RerankerConfig(
        model_name="rerank-english-v2.0",
        top_n=3
    ),
}


def get_model_config(config_type: str, model_key: str = None) -> Any:
    """
    Get model configuration by type and key.
    
    Args:
        config_type: One of 'llm', 'embedding', 'reranker'
        model_key: Specific model key, or None to use defaults
        
    Returns:
        Model configuration object
    """
    if config_type == "llm":
        if model_key and model_key in LLM_MODELS:
            return LLM_MODELS[model_key]
        # Default from settings
        from .settings import settings
        return LLMConfig(
            provider=settings.LLM_PROVIDER,
            model_name=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY if settings.LLM_PROVIDER == "groq" else None,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    
    elif config_type == "embedding":
        if model_key and model_key in EMBEDDING_MODELS:
            return EMBEDDING_MODELS[model_key]
        # Default from settings
        from .settings import settings
        return EmbeddingConfig(
            provider=settings.EMBEDDING_PROVIDER,
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION
        )
    
    elif config_type == "reranker":
        if model_key and model_key in RERANKER_MODELS:
            return RERANKER_MODELS[model_key]
        # Default
        from .settings import settings
        return RerankerConfig(
            model_name=settings.RERANKER_MODEL,
            top_n=3
        )
    
    else:
        raise ValueError(f"Unknown config type: {config_type}")


# Model registry for easy switching
class ModelRegistry:
    """Central registry for all available models."""
    
    @staticmethod
    def list_llms() -> list:
        """List all available LLM models."""
        return list(LLM_MODELS.keys())
    
    @staticmethod
    def list_embeddings() -> list:
        """List all available embedding models."""
        return list(EMBEDDING_MODELS.keys())
    
    @staticmethod
    def list_rerankers() -> list:
        """List all available reranker models."""
        return list(RERANKER_MODELS.keys())
    
    @staticmethod
    def get_llm(key: str = None) -> LLMConfig:
        """Get LLM configuration."""
        return get_model_config("llm", key)
    
    @staticmethod
    def get_embedding(key: str = None) -> EmbeddingConfig:
        """Get embedding configuration."""
        return get_model_config("embedding", key)
    
    @staticmethod
    def get_reranker(key: str = None) -> RerankerConfig:
        """Get reranker configuration."""
        return get_model_config("reranker", key)
