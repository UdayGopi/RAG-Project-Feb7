"""
Document chunking strategies.
"""
from dataclasses import dataclass
from typing import List, Literal
from llama_index.core import Settings
from config import settings


@dataclass
class ChunkConfig:
    """Chunking configuration."""
    chunk_size: int = 1024
    chunk_overlap: int = 100
    separator: str = "\n\n"
    
    @classmethod
    def from_settings(cls):
        """Create from global settings."""
        return cls(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )


class ChunkingStrategy:
    """Manages document chunking strategies."""
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig.from_settings()
        self.apply_to_settings()
    
    def apply_to_settings(self):
        """Apply chunking config to LlamaIndex Settings."""
        Settings.chunk_size = self.config.chunk_size
        Settings.chunk_overlap = self.config.chunk_overlap
    
    def get_config(self) -> ChunkConfig:
        """Get current chunking configuration."""
        return self.config
    
    def update_config(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """Update chunking configuration."""
        if chunk_size is not None:
            self.config.chunk_size = chunk_size
        if chunk_overlap is not None:
            self.config.chunk_overlap = chunk_overlap
        
        self.apply_to_settings()
    
    @staticmethod
    def get_preset(preset: Literal["small", "medium", "large", "xlarge"]) -> ChunkConfig:
        """Get preset chunking configuration."""
        presets = {
            "small": ChunkConfig(chunk_size=256, chunk_overlap=50),
            "medium": ChunkConfig(chunk_size=512, chunk_overlap=100),
            "large": ChunkConfig(chunk_size=1024, chunk_overlap=100),
            "xlarge": ChunkConfig(chunk_size=2048, chunk_overlap=200),
        }
        return presets.get(preset, ChunkConfig())


def apply_chunking_strategy(strategy: str = "large"):
    """
    Apply a chunking strategy globally.
    
    Args:
        strategy: One of 'small', 'medium', 'large', 'xlarge'
    """
    config = ChunkingStrategy.get_preset(strategy)
    Settings.chunk_size = config.chunk_size
    Settings.chunk_overlap = config.chunk_overlap
    return config
