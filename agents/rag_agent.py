"""
Modern RAG Agent using modular architecture.
Replaces the old monolithic rag_agent.py with clean, maintainable code.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.selectors import PydanticSingleSelector

# Import from new modular structure
from config import settings
from core import get_llm, get_embedding_model, get_reranker
from storage import get_storage
from storage.vector_stores import get_vector_store_from_config, create_storage_context
from utils.url_tracker import (
    format_sources_with_urls,
    deduplicate_sources,
    enrich_documents_with_urls,
    enrich_file_with_metadata
)
from ingestion.url_processor import URLProcessor
from retrieval import HybridRetriever, QueryExpander, MetadataFilter
from agents.intent_classifier import classify_intent
from config.constants import IntentType


class ModernRAGAgent:
    """
    Modern RAG Agent using modular architecture.
    Supports multi-tenant, hybrid retrieval, and proper source attribution.
    """
    
    def __init__(self, documents_dir: str = None, storage_dir: str = None):
        """
        Initialize RAG Agent.
        
        Args:
            documents_dir: Override documents directory (uses config if not provided)
            storage_dir: Override storage directory (uses config if not provided)
        """
        # Setup directories
        self.documents_dir = documents_dir or settings.LOCAL_DOCUMENTS_DIR
        self.storage_dir = storage_dir or settings.LOCAL_STORAGE_DIR
        
        os.makedirs(self.documents_dir, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)
        
        logging.info(f"Initializing ModernRAGAgent")
        logging.info(f"  Documents: {self.documents_dir}")
        logging.info(f"  Storage: {self.storage_dir}")
        
        # Initialize models
        self._init_models()
        
        # Initialize storage
        self._init_storage()
        
        # Initialize URL processor
        self.url_processor = URLProcessor(
            allowed_domains=["www.cms.gov", "esmdguide-fhir.cms.hhs.gov", "www.hhs.gov"]
        )
        
        # Initialize query expander if enabled
        self.query_expander = None
        if settings.ENABLE_QUERY_EXPANSION:
            self.query_expander = QueryExpander(llm=self.llm)
            logging.info("Query expansion enabled")
        
        # Multi-tenant router
        self.router_query_engine: Optional[RouterQueryEngine] = None
        self.tenants: List[str] = []
        self.tools: List[QueryEngineTool] = []
        
        # Load existing tenants
        self._load_tenants()
        
        logging.info("✅ ModernRAGAgent initialized successfully")
    
    def _init_models(self):
        """Initialize LLM, embeddings, and other models."""
        logging.info("Initializing models...")
        
        # Get models from config
        self.llm = get_llm()
        self.embed_model = get_embedding_model()
        
        # Set global settings
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model
        Settings.chunk_size = settings.CHUNK_SIZE
        Settings.chunk_overlap = settings.CHUNK_OVERLAP
        
        # Get reranker if available
        try:
            self.reranker = get_reranker()
            logging.info(f"✅ Reranker initialized: {settings.RERANKER_MODEL}")
        except Exception as e:
            logging.warning(f"Reranker not available: {e}")
            self.reranker = None
        
        logging.info(f"✅ Models initialized:")
        logging.info(f"  LLM: {settings.LLM_PROVIDER}/{settings.LLM_MODEL}")
        logging.info(f"  Embeddings: {settings.EMBEDDING_PROVIDER}/{settings.EMBEDDING_MODEL}")
    
    def _init_storage(self):
        """Initialize storage backends."""
        logging.info("Initializing storage...")
        
        # Document storage (S3/local)
        self.document_storage = get_storage()
        
        # Vector storage (Qdrant/Pinecone/local)
        try:
            self.vector_store = get_vector_store_from_config()
            logging.info(f"✅ Vector store: {settings.VECTOR_STORE}")
        except Exception as e:
            logging.warning(f"Using default vector store: {e}")
            self.vector_store = None
    
    def _load_tenants(self):
        """Load existing tenant indexes."""
        logging.info("Loading existing tenants...")
        
        tenants_found = []
        storage_path = Path(self.storage_dir)
        
        if storage_path.exists():
            for tenant_dir in storage_path.iterdir():
                if tenant_dir.is_dir():
                    tenants_found.append(tenant_dir.name)
        
        if tenants_found:
            logging.info(f"Found {len(tenants_found)} tenants: {tenants_found}")
            self._rebuild_router_engine(tenants_found)
        else:
            logging.info("No existing tenants found")
    
    def _rebuild_router_engine(self, tenant_ids: List[str]):
        """
        Build/rebuild router query engine for multi-tenant access.
        
        Args:
            tenant_ids: List of tenant IDs to include
        """
        if not tenant_ids:
            logging.warning("No tenants to build router")
            return
        
        logging.info(f"Building router for tenants: {tenant_ids}")
        
        tools = []
        
        for tenant_id in tenant_ids:
            try:
                # Load tenant index
                tenant_storage_path = os.path.join(self.storage_dir, tenant_id)
                
                if not os.path.exists(tenant_storage_path):
                    logging.warning(f"Tenant storage not found: {tenant_id}")
                    continue
                
                # Load index
                storage_context = StorageContext.from_defaults(
                    persist_dir=tenant_storage_path
                )
                index = load_index_from_storage(storage_context)
                
                # Create query engine with optional reranker
                if self.reranker:
                    query_engine = index.as_query_engine(
                        similarity_top_k=settings.SIMILARITY_TOP_K,
                        node_postprocessors=[self.reranker],
                        similarity_cutoff=settings.SIMILARITY_CUTOFF
                    )
                else:
                    query_engine = index.as_query_engine(
                        similarity_top_k=settings.SIMILARITY_TOP_K,
                        similarity_cutoff=settings.SIMILARITY_CUTOFF
                    )
                
                # Create tool
                tool = QueryEngineTool(
                    query_engine=query_engine,
                    metadata=ToolMetadata(
                        name=tenant_id,
                        description=f"Knowledge base for {tenant_id} tenant"
                    )
                )
                
                tools.append(tool)
                logging.info(f"  ✅ Loaded: {tenant_id}")
                
            except Exception as e:
                logging.error(f"Failed to load tenant {tenant_id}: {e}")
        
        if tools:
            # Build router
            self.router_query_engine = RouterQueryEngine(
                selector=PydanticSingleSelector.from_defaults(),
                query_engine_tools=tools
            )
            self.tools = tools
            self.tenants = tenant_ids
            logging.info(f"✅ Router built with {len(tools)} tenants")
        else:
            logging.warning("No tools created, router not built")
            self.router_query_engine = None
    
    def ingest_url(self, url: str, tenant_id: str) -> Dict[str, Any]:
        """
        Ingest content from URL with proper source attribution.
        
        Args:
            url: URL to ingest
            tenant_id: Tenant ID
            
        Returns:
            Status dictionary
        """
        logging.info(f"Ingesting URL: {url} for tenant: {tenant_id}")
        
        try:
            # Process URL (automatically adds metadata)
            documents = self.url_processor.process_url(url, tenant_id)
            
            if not documents:
                return {
                    "success": False,
                    "error": "No content extracted from URL"
                }
            
            logging.info(f"Extracted {len(documents)} documents from {url}")
            
            # Index documents
            result = self._index_documents(documents, tenant_id)
            
            return {
                "success": True,
                "url": url,
                "documents_created": len(documents),
                "chunks_created": result.get("chunks_created", 0)
            }
            
        except Exception as e:
            logging.error(f"Error ingesting URL: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def ingest_file(self, file_path: str, tenant_id: str) -> Dict[str, Any]:
        """
        Ingest file with proper source attribution.
        
        Args:
            file_path: Path to file
            tenant_id: Tenant ID
            
        Returns:
            Status dictionary
        """
        logging.info(f"Ingesting file: {file_path} for tenant: {tenant_id}")
        
        try:
            # Load documents
            documents = SimpleDirectoryReader(
                input_files=[file_path]
            ).load_data()
            
            if not documents:
                return {
                    "success": False,
                    "error": "No content extracted from file"
                }
            
            # Add file metadata (for proper citations)
            enrich_file_with_metadata(documents, file_path, tenant_id)
            
            logging.info(f"Extracted {len(documents)} documents from {Path(file_path).name}")
            
            # Index documents
            result = self._index_documents(documents, tenant_id)
            
            return {
                "success": True,
                "file": Path(file_path).name,
                "documents_created": len(documents),
                "chunks_created": result.get("chunks_created", 0)
            }
            
        except Exception as e:
            logging.error(f"Error ingesting file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _index_documents(self, documents: List, tenant_id: str) -> Dict[str, Any]:
        """
        Index documents for a tenant.
        
        Args:
            documents: List of documents
            tenant_id: Tenant ID
            
        Returns:
            Indexing result
        """
        tenant_storage_path = os.path.join(self.storage_dir, tenant_id)
        os.makedirs(tenant_storage_path, exist_ok=True)
        
        # Check if index exists
        if os.path.exists(os.path.join(tenant_storage_path, "docstore.json")):
            # Load existing index
            storage_context = StorageContext.from_defaults(
                persist_dir=tenant_storage_path
            )
            index = load_index_from_storage(storage_context)
            
            # Add documents
            for doc in documents:
                index.insert(doc)
            
            logging.info(f"Added {len(documents)} documents to existing index")
        else:
            # Create new index
            if self.vector_store:
                storage_context = create_storage_context(self.vector_store)
            else:
                storage_context = StorageContext.from_defaults()
            
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context
            )
            
            logging.info(f"Created new index with {len(documents)} documents")
        
        # Persist index
        index.storage_context.persist(persist_dir=tenant_storage_path)
        
        # Rebuild router if tenant is new
        if tenant_id not in self.tenants:
            self.tenants.append(tenant_id)
            self._rebuild_router_engine(self.tenants)
        
        return {
            "chunks_created": len(documents)
        }
    
    def query(self, user_query: str, tenant_id: str = None) -> Dict[str, Any]:
        """
        Query the RAG system with proper source citations.
        
        Args:
            user_query: User's question
            tenant_id: Optional specific tenant to query
            
        Returns:
            Response with sources showing URLs, not extracted content
        """
        logging.info(f"Query: {user_query[:100]}...")
        
        # Classify intent
        intent, confidence = classify_intent(user_query)
        
        # Handle small talk
        if intent == IntentType.SMALL_TALK:
            return {
                "summary": "Hello! How can I help you today?",
                "detailed_response": "I'm here to help answer your questions about policies and procedures.",
                "sources": [],
                "intent": "small_talk"
            }
        
        # Check if router is initialized
        if not self.router_query_engine:
            return {
                "summary": "No Knowledge Base",
                "detailed_response": "No documents have been indexed yet. Please upload documents first.",
                "sources": [],
                "error": "No index available"
            }
        
        try:
            # Expand query if enabled
            queries = [user_query]
            if self.query_expander:
                queries = self.query_expander.expand_query(user_query)
                logging.info(f"Expanded query into {len(queries)} variations")
            
            # Query the router (multi-tenant)
            response = self.router_query_engine.query(queries[0])
            
            # Format sources - URLs only, not extracted content!
            sources = format_sources_with_urls(response.source_nodes)
            sources = deduplicate_sources(sources)
            
            # Build response
            result = {
                "summary": response.response[:200] if len(response.response) > 200 else response.response,
                "detailed_response": response.response,
                "sources": sources,  # Clean URLs and filenames!
                "confidence": self._calculate_confidence(response)
            }
            
            logging.info(f"Query successful, {len(sources)} sources")
            return result
            
        except Exception as e:
            logging.error(f"Query error: {e}")
            return {
                "summary": "Error",
                "detailed_response": f"An error occurred: {str(e)}",
                "sources": [],
                "error": str(e)
            }
    
    def _calculate_confidence(self, response) -> float:
        """Calculate confidence score from response."""
        if not response.source_nodes:
            return 0.0
        
        # Average of top source scores
        scores = [node.score for node in response.source_nodes if hasattr(node, 'score')]
        return sum(scores) / len(scores) if scores else 0.5
    
    def list_tenants(self) -> List[str]:
        """Get list of available tenants."""
        return self.tenants
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            "tenants": len(self.tenants),
            "tenant_ids": self.tenants,
            "storage_backend": settings.STORAGE_BACKEND,
            "vector_store": settings.VECTOR_STORE,
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "retrieval_mode": settings.RETRIEVAL_MODE
        }


# Global agent instance (initialized on first use)
_agent_instance: Optional[ModernRAGAgent] = None


def get_rag_agent() -> ModernRAGAgent:
    """
    Get global RAG agent instance.
    Creates on first call, reuses thereafter.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ModernRAGAgent()
    return _agent_instance


def initialize_agent(documents_dir: str = None, storage_dir: str = None) -> ModernRAGAgent:
    """
    Initialize RAG agent with custom directories.
    
    Args:
        documents_dir: Documents directory
        storage_dir: Storage directory
        
    Returns:
        Initialized agent
    """
    global _agent_instance
    _agent_instance = ModernRAGAgent(documents_dir, storage_dir)
    return _agent_instance
