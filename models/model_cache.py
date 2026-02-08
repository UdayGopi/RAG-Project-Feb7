"""
Model file caching for cloud storage.
"""
import logging
import hashlib
from pathlib import Path
from typing import Optional


class ModelCache:
    """Caches model files locally when using cloud storage."""
    
    def __init__(self, cache_dir: str = "data/models"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"ModelCache initialized at: {self.cache_dir}")
    
    def get_cache_path(self, model_name: str, file_name: str = None) -> Path:
        """Get local cache path for a model."""
        # Sanitize model name for filesystem
        safe_name = model_name.replace("/", "_").replace(":", "_")
        model_dir = self.cache_dir / safe_name
        
        if file_name:
            return model_dir / file_name
        return model_dir
    
    def is_cached(self, model_name: str) -> bool:
        """Check if model is cached locally."""
        cache_path = self.get_cache_path(model_name)
        return cache_path.exists() and any(cache_path.iterdir())
    
    def cache_model(self, model_name: str, source_path: str) -> Path:
        """
        Cache a model from source to local storage.
        
        Args:
            model_name: Model identifier
            source_path: Path to model files
            
        Returns:
            Path to cached model
        """
        cache_path = self.get_cache_path(model_name)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source path not found: {source_path}")
        
        # Copy model files
        import shutil
        if source.is_file():
            shutil.copy2(source, cache_path / source.name)
        else:
            shutil.copytree(source, cache_path, dirs_exist_ok=True)
        
        logging.info(f"Cached model: {model_name} at {cache_path}")
        return cache_path
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get path to cached model, or None if not cached."""
        cache_path = self.get_cache_path(model_name)
        return cache_path if self.is_cached(model_name) else None
    
    def clear_cache(self, model_name: Optional[str] = None):
        """Clear cache for specific model or all models."""
        import shutil
        
        if model_name:
            cache_path = self.get_cache_path(model_name)
            if cache_path.exists():
                shutil.rmtree(cache_path)
                logging.info(f"Cleared cache for: {model_name}")
        else:
            # Clear entire cache
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logging.info("Cleared all model cache")
    
    def get_cache_size(self, model_name: Optional[str] = None) -> int:
        """Get cache size in bytes."""
        if model_name:
            cache_path = self.get_cache_path(model_name)
            if not cache_path.exists():
                return 0
            paths = [cache_path]
        else:
            paths = list(self.cache_dir.iterdir())
        
        total_size = 0
        for path in paths:
            if path.is_file():
                total_size += path.stat().st_size
            elif path.is_dir():
                for file in path.rglob("*"):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        return total_size
    
    def get_cache_info(self) -> dict:
        """Get information about cached models."""
        models = []
        total_size = 0
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir():
                size = self.get_cache_size(model_dir.name)
                models.append({
                    "name": model_dir.name,
                    "size_mb": size / (1024 * 1024),
                    "path": str(model_dir)
                })
                total_size += size
        
        return {
            "models": models,
            "total_models": len(models),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }


# Global model cache instance
_model_cache = ModelCache()


def get_model_cache() -> ModelCache:
    """Get global model cache instance."""
    return _model_cache
