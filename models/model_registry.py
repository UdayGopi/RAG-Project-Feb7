"""
Central registry for all available models with metadata.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class ModelInfo:
    """Model metadata."""
    id: str
    provider: str
    model_name: str
    type: str  # 'llm', 'embedding', 'reranker'
    version: str = "latest"
    size_mb: Optional[int] = None
    context_window: Optional[int] = None
    cost_per_1m_tokens: Optional[float] = None
    supports_streaming: bool = False
    local: bool = False
    description: str = ""
    added_date: datetime = None
    
    def __post_init__(self):
        if self.added_date is None:
            self.added_date = datetime.now()


class ModelRegistry:
    """Registry of all available models."""
    
    _models: Dict[str, ModelInfo] = {}
    
    @classmethod
    def register(cls, model_info: ModelInfo):
        """Register a new model."""
        cls._models[model_info.id] = model_info
    
    @classmethod
    def get(cls, model_id: str) -> Optional[ModelInfo]:
        """Get model info by ID."""
        return cls._models.get(model_id)
    
    @classmethod
    def list_models(
        cls,
        model_type: Optional[str] = None,
        provider: Optional[str] = None,
        local_only: bool = False
    ) -> List[ModelInfo]:
        """List models with optional filtering."""
        models = list(cls._models.values())
        
        if model_type:
            models = [m for m in models if m.type == model_type]
        
        if provider:
            models = [m for m in models if m.provider == provider]
        
        if local_only:
            models = [m for m in models if m.local]
        
        return models
    
    @classmethod
    def get_default_llm(cls) -> Optional[ModelInfo]:
        """Get default LLM model."""
        from config import settings
        model_id = f"{settings.LLM_PROVIDER}-{settings.LLM_MODEL}"
        return cls.get(model_id) or cls.list_models(model_type="llm")[0] if cls._models else None
    
    @classmethod
    def get_default_embedding(cls) -> Optional[ModelInfo]:
        """Get default embedding model."""
        from config import settings
        model_id = f"{settings.EMBEDDING_PROVIDER}-{settings.EMBEDDING_MODEL}"
        return cls.get(model_id) or cls.list_models(model_type="embedding")[0] if cls._models else None


# Register available models
def _initialize_registry():
    """Initialize registry with predefined models."""
    
    # LLMs
    ModelRegistry.register(ModelInfo(
        id="groq-llama-3.1-8b",
        provider="groq",
        model_name="llama-3.1-8b-instant",
        type="llm",
        context_window=6000,
        cost_per_1m_tokens=0.0,  # Free tier
        supports_streaming=True,
        description="Fast, free Llama 3.1 8B model from Groq"
    ))
    
    ModelRegistry.register(ModelInfo(
        id="groq-llama-3.1-70b",
        provider="groq",
        model_name="llama-3.1-70b-versatile",
        type="llm",
        context_window=6000,
        cost_per_1m_tokens=0.0,
        supports_streaming=True,
        description="Larger Llama 3.1 70B from Groq"
    ))
    
    ModelRegistry.register(ModelInfo(
        id="openai-gpt-4",
        provider="openai",
        model_name="gpt-4-turbo-preview",
        type="llm",
        context_window=128000,
        cost_per_1m_tokens=10.0,
        supports_streaming=True,
        description="Most capable OpenAI model"
    ))
    
    ModelRegistry.register(ModelInfo(
        id="openai-gpt-3.5",
        provider="openai",
        model_name="gpt-3.5-turbo",
        type="llm",
        context_window=16385,
        cost_per_1m_tokens=0.5,
        supports_streaming=True,
        description="Fast, cost-effective OpenAI model"
    ))
    
    # Embeddings
    ModelRegistry.register(ModelInfo(
        id="huggingface-bge-small",
        provider="huggingface",
        model_name="BAAI/bge-small-en-v1.5",
        type="embedding",
        size_mb=134,
        local=True,
        description="Lightweight, high-quality embeddings (384d)"
    ))
    
    ModelRegistry.register(ModelInfo(
        id="huggingface-bge-base",
        provider="huggingface",
        model_name="BAAI/bge-base-en-v1.5",
        type="embedding",
        size_mb=438,
        local=True,
        description="Balanced quality/size embeddings (768d)"
    ))
    
    ModelRegistry.register(ModelInfo(
        id="openai-ada-002",
        provider="openai",
        model_name="text-embedding-ada-002",
        type="embedding",
        cost_per_1m_tokens=0.1,
        description="High-quality OpenAI embeddings (1536d)"
    ))
    
    # Rerankers
    ModelRegistry.register(ModelInfo(
        id="bge-reranker-base",
        provider="huggingface",
        model_name="BAAI/bge-reranker-base",
        type="reranker",
        size_mb=278,
        local=True,
        description="Cross-encoder reranker for better precision"
    ))


# Initialize on import
_initialize_registry()
