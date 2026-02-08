"""
Lazy model loading and management.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path


class ModelLoader:
    """Manages lazy loading of models with caching."""
    
    def __init__(self, cache_dir: str = "data/models"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_models: Dict[str, Any] = {}
    
    def load_model(
        self,
        model_type: str,
        model_id: str,
        **kwargs
    ) -> Any:
        """
        Lazy load a model.
        
        Args:
            model_type: Type of model ('llm', 'embedding', 'reranker')
            model_id: Model identifier
            **kwargs: Additional model-specific parameters
            
        Returns:
            Loaded model instance
        """
        cache_key = f"{model_type}:{model_id}"
        
        if cache_key in self._loaded_models:
            logging.info(f"Using cached model: {cache_key}")
            return self._loaded_models[cache_key]
        
        logging.info(f"Loading model: {cache_key}")
        
        if model_type == "llm":
            model = self._load_llm(model_id, **kwargs)
        elif model_type == "embedding":
            model = self._load_embedding(model_id, **kwargs)
        elif model_type == "reranker":
            model = self._load_reranker(model_id, **kwargs)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        self._loaded_models[cache_key] = model
        return model
    
    def _load_llm(self, model_id: str, **kwargs):
        """Load LLM model."""
        from core.llm import get_llm
        from models.model_registry import ModelRegistry
        
        model_info = ModelRegistry.get(model_id)
        if not model_info:
            raise ValueError(f"Model not found in registry: {model_id}")
        
        return get_llm(
            provider=model_info.provider,
            model_name=model_info.model_name,
            **kwargs
        )
    
    def _load_embedding(self, model_id: str, **kwargs):
        """Load embedding model."""
        from core.embeddings import get_embedding_model
        from models.model_registry import ModelRegistry
        
        model_info = ModelRegistry.get(model_id)
        if not model_info:
            raise ValueError(f"Model not found in registry: {model_id}")
        
        return get_embedding_model(
            provider=model_info.provider,
            model_name=model_info.model_name,
            **kwargs
        )
    
    def _load_reranker(self, model_id: str, **kwargs):
        """Load reranker model."""
        from core.reranking import get_reranker
        from models.model_registry import ModelRegistry
        
        model_info = ModelRegistry.get(model_id)
        if not model_info:
            raise ValueError(f"Model not found in registry: {model_id}")
        
        return get_reranker(
            model_name=model_info.model_name,
            **kwargs
        )
    
    def unload_model(self, model_type: str, model_id: str):
        """Unload a specific model from memory."""
        cache_key = f"{model_type}:{model_id}"
        if cache_key in self._loaded_models:
            del self._loaded_models[cache_key]
            logging.info(f"Unloaded model: {cache_key}")
    
    def unload_all(self):
        """Unload all models from memory."""
        self._loaded_models.clear()
        logging.info("All models unloaded")
    
    def get_loaded_models(self) -> list:
        """Get list of currently loaded models."""
        return list(self._loaded_models.keys())


# Global model loader instance
_model_loader = ModelLoader()


def get_model_loader() -> ModelLoader:
    """Get global model loader instance."""
    return _model_loader
