"""
LLM management with support for multiple providers.
"""
import logging
from typing import Optional
from config import settings


def get_llm(provider: Optional[str] = None, model_name: Optional[str] = None, api_key: Optional[str] = None):
    """
    Get LLM instance based on provider.
    
    Args:
        provider: LLM provider ('groq', 'openai', 'anthropic', 'ollama')
        model_name: Specific model name
        api_key: API key (if different from settings)
        
    Returns:
        LLM instance compatible with LlamaIndex
    """
    provider = provider or settings.LLM_PROVIDER
    model_name = model_name or settings.LLM_MODEL
    api_key = api_key or settings.GROQ_API_KEY
    
    logging.info(f"Initializing LLM: {provider}/{model_name}")
    
    if provider == "groq":
        from llama_index.llms.groq import Groq
        
        if not api_key:
            api_key = settings.GROQ_API_KEY
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for Groq provider")
        
        return Groq(
            model=model_name,
            api_key=api_key,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    
    elif provider == "openai":
        from llama_index.llms.openai import OpenAI
        
        if not api_key:
            api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        
        return OpenAI(
            model=model_name,
            api_key=api_key,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    
    elif provider == "anthropic":
        from llama_index.llms.anthropic import Anthropic
        
        if not api_key:
            api_key = settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        
        return Anthropic(
            model=model_name,
            api_key=api_key,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )
    
    elif provider == "ollama":
        from llama_index.llms.ollama import Ollama
        
        return Ollama(
            model=model_name,
            temperature=settings.LLM_TEMPERATURE,
            request_timeout=120.0
        )
    
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_llm_token_limit(model_name: str) -> int:
    """Get token limit for a specific model."""
    from config.constants import MODEL_TOKEN_LIMITS
    return MODEL_TOKEN_LIMITS.get(model_name, 4096)


class LLMManager:
    """Manages LLM instances with caching and switching."""
    
    def __init__(self):
        self._llm_cache = {}
        self._current_provider = settings.LLM_PROVIDER
        self._current_model = settings.LLM_MODEL
    
    def get_llm(self, provider: Optional[str] = None, model_name: Optional[str] = None):
        """Get or create LLM instance with caching."""
        provider = provider or self._current_provider
        model_name = model_name or self._current_model
        
        cache_key = f"{provider}:{model_name}"
        
        if cache_key not in self._llm_cache:
            self._llm_cache[cache_key] = get_llm(provider, model_name)
            logging.info(f"Cached new LLM: {cache_key}")
        
        return self._llm_cache[cache_key]
    
    def switch_llm(self, provider: str, model_name: str):
        """Switch to a different LLM."""
        logging.info(f"Switching LLM: {provider}/{model_name}")
        self._current_provider = provider
        self._current_model = model_name
        return self.get_llm(provider, model_name)
    
    def clear_cache(self):
        """Clear LLM cache."""
        self._llm_cache.clear()
        logging.info("LLM cache cleared")


# Global LLM manager instance
_llm_manager = LLMManager()


def get_default_llm():
    """Get default LLM instance."""
    return _llm_manager.get_llm()


def switch_llm(provider: str, model_name: str):
    """Switch to different LLM globally."""
    return _llm_manager.switch_llm(provider, model_name)
