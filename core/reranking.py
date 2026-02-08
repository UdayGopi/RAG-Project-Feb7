"""
Reranking models for improving retrieval quality.
"""
import logging
from typing import Optional
from llama_index.core.postprocessor import SentenceTransformerRerank
from config import settings


def get_reranker(
    model_name: Optional[str] = None,
    top_n: Optional[int] = None
):
    """
    Get reranker instance.
    
    Args:
        model_name: Reranker model name
        top_n: Number of top results to keep after reranking
        
    Returns:
        Reranker instance
    """
    model_name = model_name or settings.RERANKER_MODEL
    top_n = top_n or settings.RERANK_TOP_N
    
    logging.info(f"Initializing reranker: {model_name} (top_n={top_n})")
    
    return SentenceTransformerRerank(
        model=model_name,
        top_n=top_n
    )


class RerankerManager:
    """Manages reranker instances."""
    
    def __init__(self):
        self._reranker_cache = {}
        self._current_model = settings.RERANKER_MODEL
        self._current_top_n = settings.RERANK_TOP_N
    
    def get_reranker(
        self,
        model_name: Optional[str] = None,
        top_n: Optional[int] = None
    ):
        """Get or create reranker with caching."""
        model_name = model_name or self._current_model
        top_n = top_n or self._current_top_n
        
        cache_key = f"{model_name}:{top_n}"
        
        if cache_key not in self._reranker_cache:
            self._reranker_cache[cache_key] = get_reranker(model_name, top_n)
            logging.info(f"Cached new reranker: {cache_key}")
        
        return self._reranker_cache[cache_key]
    
    def update_top_n(self, top_n: int):
        """Update top_n globally."""
        self._current_top_n = top_n
        return self.get_reranker(top_n=top_n)
    
    def clear_cache(self):
        """Clear reranker cache."""
        self._reranker_cache.clear()
        logging.info("Reranker cache cleared")


# Global reranker manager
_reranker_manager = RerankerManager()


def get_default_reranker():
    """Get default reranker instance."""
    return _reranker_manager.get_reranker()


def update_rerank_top_n(top_n: int):
    """Update reranking top_n globally."""
    return _reranker_manager.update_top_n(top_n)
