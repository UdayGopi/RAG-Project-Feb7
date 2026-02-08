"""
Application constants and enums.
"""
from enum import Enum


class IntentType(Enum):
    """User query intent types."""
    SMALL_TALK = "small_talk"
    CLARIFY = "clarify"
    DOWNLOAD = "download"
    QUESTION = "question"
    UNKNOWN = "unknown"


class RetrievalMode(Enum):
    """Retrieval strategy modes."""
    SEMANTIC = "semantic"           # Dense embeddings only
    HYBRID = "hybrid"               # BM25 + Semantic
    FUSION = "fusion"               # Multi-query with RRF
    AGENTIC = "agentic"            # Iterative retrieval


class StorageBackend(Enum):
    """Storage backend types."""
    LOCAL = "local"
    S3 = "s3"
    AZURE = "azure"


class DocumentType(Enum):
    """Document types for metadata."""
    POLICY = "policy"
    GUIDE = "guide"
    FORM = "form"
    MANUAL = "manual"
    REFERENCE = "reference"
    OTHER = "other"


# Allowed file extensions
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md",
    ".html", ".htm", ".csv", ".xlsx", ".xls",
    ".pptx", ".ppt", ".json", ".xml"
}

# Allowed domains for web scraping
ALLOWED_DOMAINS = [
    "www.cms.gov",
    "esmdguide-fhir.cms.hhs.gov",
    "www.hhs.gov"
]

# Max file sizes (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_UPLOAD_SIZE = 200 * 1024 * 1024  # 200MB

# Token limits per model
MODEL_TOKEN_LIMITS = {
    "llama-3.1-8b-instant": 6000,      # Groq free tier
    "llama-3.1-70b-versatile": 6000,   # Groq free tier
    "gpt-4-turbo-preview": 128000,     # OpenAI
    "gpt-3.5-turbo": 16385,            # OpenAI
    "claude-3-sonnet": 200000,         # Anthropic
}

# Cache settings
CACHE_KEY_MAX_LENGTH = 200
CACHE_MAX_ENTRIES = 1000
CACHE_CLEANUP_THRESHOLD = 0.9  # Clean when 90% full

# Query validation
MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 500
MIN_MEANINGFUL_TOKENS = 1

# Confidence thresholds
DEFAULT_HIGH_CONFIDENCE = 0.75
DEFAULT_MIN_CONFIDENCE = 0.5

# Retrieval defaults
DEFAULT_TOP_K = 10
DEFAULT_RERANK_TOP_N = 3
DEFAULT_SIMILARITY_CUTOFF = 0.5

# Context limits
MAX_CONTEXT_TOKENS = 3500
MAX_PROMPT_TOKENS = 5500

# Stopwords for keyword extraction
STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", 
    "about", "have", "what", "which", "when", "where", "will", 
    "there", "into", "those", "been", "being", "were", "are", 
    "how", "make", "made", "like", "such", "use", "uses", "used", 
    "using", "can", "you", "please", "tell", "more", "info", 
    "step", "steps", "process", "guide", "guidance", "policy", 
    "policies", "onboarding", "onboard", "form", "forms"
}

# Domain-specific terms (always important)
DOMAIN_TERMS = {
    "esmd", "fhir", "cms", "hhs", "extension", "extensions",
    "implementation", "lob", "medicare", "medicaid", "marketplace",
    "icd", "cpt", "hcpcs", "drg", "npi"
}

# Intent detection patterns
GREETING_PATTERNS = [
    r"\b(hi|hello|hey|hiya|yo|sup)\b",
    r"\b(good\s+(morning|afternoon|evening|night))\b",
    r"\b(how\s+are\s+you|what'?s\s+up|whats\s+up)\b"
]

DOWNLOAD_KEYWORDS = [
    "download", "form", "get", "obtain", "document", 
    "file", "pdf", "retrieve", "export"
]

# Logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
