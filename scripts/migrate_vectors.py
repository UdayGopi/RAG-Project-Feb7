"""
Migrate vector data from local storage to cloud vector database.
Useful when switching from local to Qdrant/Pinecone.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from storage.vector_stores import get_vector_store_from_config, VectorStoreFactory
from llama_index.core import load_index_from_storage, StorageContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_local_to_cloud(
    source_dir: str,
    target_store_type: str,
    target_config: dict,
    tenant_id: str = None
):
    """
    Migrate local vector indexes to cloud vector database.
    
    Args:
        source_dir: Local storage directory
        target_store_type: Target vector store type (qdrant, pinecone, opensearch)
        target_config: Configuration for target store
        tenant_id: Optional tenant ID to migrate specific tenant
    """
    logger.info(f"Starting migration: local -> {target_store_type}")
    
    # Get local directories to migrate
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return
    
    # Find all tenant directories or specific tenant
    if tenant_id:
        tenant_dirs = [source_path / tenant_id]
    else:
        tenant_dirs = [d for d in source_path.iterdir() if d.is_dir()]
    
    logger.info(f"Found {len(tenant_dirs)} tenant(s) to migrate")
    
    # Create target vector store
    target_vector_store = VectorStoreFactory.create_vector_store(
        target_store_type, 
        target_config
    )
    
    # Migrate each tenant
    for tenant_dir in tenant_dirs:
        tenant_name = tenant_dir.name
        logger.info(f"\nMigrating tenant: {tenant_name}")
        
        try:
            # Load local index
            logger.info(f"Loading local index from: {tenant_dir}")
            storage_context = StorageContext.from_defaults(persist_dir=str(tenant_dir))
            local_index = load_index_from_storage(storage_context)
            
            # Get all documents from local index
            logger.info("Extracting documents from local index...")
            documents = []
            for node in local_index.docstore.docs.values():
                documents.append(node)
            
            logger.info(f"Found {len(documents)} documents")
            
            # Create new index with target vector store
            logger.info(f"Creating new index in {target_store_type}...")
            target_storage_context = StorageContext.from_defaults(
                vector_store=target_vector_store
            )
            
            from llama_index.core import VectorStoreIndex
            target_index = VectorStoreIndex.from_documents(
                documents,
                storage_context=target_storage_context
            )
            
            logger.info(f"✅ Successfully migrated tenant: {tenant_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate tenant {tenant_name}: {e}")
            continue
    
    logger.info(f"\n✅ Migration complete!")


def main():
    """Main migration script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate vector data to cloud")
    parser.add_argument(
        "--source",
        default="data/storage",
        help="Source directory with local indexes"
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["qdrant", "pinecone", "opensearch"],
        help="Target vector store type"
    )
    parser.add_argument(
        "--tenant",
        help="Specific tenant to migrate (optional)"
    )
    
    args = parser.parse_args()
    
    # Build target configuration from settings
    target_config = {
        "qdrant_url": settings.QDRANT_URL,
        "qdrant_api_key": settings.QDRANT_API_KEY,
        "qdrant_collection": settings.QDRANT_COLLECTION,
        "pinecone_api_key": settings.PINECONE_API_KEY,
        "pinecone_environment": settings.PINECONE_ENV,
        "pinecone_index_name": settings.PINECONE_INDEX,
        "embedding_dimension": settings.EMBEDDING_DIMENSION,
        "opensearch_host": settings.OPENSEARCH_HOST,
        "opensearch_port": settings.OPENSEARCH_PORT,
        "opensearch_user": settings.OPENSEARCH_USER,
        "opensearch_password": settings.OPENSEARCH_PASSWORD,
        "opensearch_index": settings.OPENSEARCH_INDEX,
    }
    
    # Perform migration
    migrate_local_to_cloud(
        source_dir=args.source,
        target_store_type=args.target,
        target_config=target_config,
        tenant_id=args.tenant
    )


if __name__ == "__main__":
    main()
