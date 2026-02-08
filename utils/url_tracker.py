"""
URL tracking and source attribution for RAG responses.
Ensures sources show original URLs, not extracted content.
"""
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from pathlib import Path


class URLTracker:
    """Tracks and manages source URLs for documents."""
    
    def __init__(self):
        self.url_map = {}  # Maps document ID to source URL
        logging.info("URLTracker initialized")
    
    def add_url(self, doc_id: str, url: str, title: str = None):
        """
        Add URL mapping for a document.
        
        Args:
            doc_id: Document or chunk ID
            url: Original source URL
            title: Optional document title
        """
        self.url_map[doc_id] = {
            "url": url,
            "title": title or self._extract_title_from_url(url),
            "domain": self._extract_domain(url)
        }
        logging.debug(f"Added URL mapping: {doc_id} -> {url}")
    
    def get_url(self, doc_id: str) -> Optional[str]:
        """Get URL for a document ID."""
        return self.url_map.get(doc_id, {}).get("url")
    
    def get_url_info(self, doc_id: str) -> Optional[Dict[str, str]]:
        """Get full URL info for a document ID."""
        return self.url_map.get(doc_id)
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"
    
    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """Extract a readable title from URL."""
        try:
            parsed = urlparse(url)
            path = parsed.path.strip('/').split('/')[-1]
            # Remove file extension and convert to title
            title = path.replace('-', ' ').replace('_', ' ')
            title = title.rsplit('.', 1)[0]  # Remove extension
            return title.title() if title else parsed.netloc
        except:
            return url


def format_sources_with_urls(source_nodes: List[Any]) -> List[Dict[str, Any]]:
    """
    Format source nodes to show URLs instead of extracted content.
    
    Args:
        source_nodes: List of retrieved nodes from LlamaIndex
        
    Returns:
        List of formatted sources with URLs
    """
    formatted_sources = []
    
    for idx, node in enumerate(source_nodes, 1):
        try:
            # Get metadata
            metadata = node.metadata if hasattr(node, 'metadata') else {}
            
            # Priority order for source URL:
            # 1. metadata['url'] (direct URL)
            # 2. metadata['source'] (file path or URL)
            # 3. metadata['file_path'] (local file)
            
            source_url = None
            source_type = "document"
            
            # Check for URL in metadata
            if 'url' in metadata and metadata['url']:
                source_url = metadata['url']
                source_type = "webpage"
            elif 'source' in metadata:
                source = metadata['source']
                if source.startswith('http://') or source.startswith('https://'):
                    source_url = source
                    source_type = "webpage"
                else:
                    # It's a file path - extract filename
                    source_url = Path(source).name
                    source_type = "file"
            elif 'file_path' in metadata:
                source_url = Path(metadata['file_path']).name
                source_type = "file"
            elif 'file_name' in metadata:
                source_url = metadata['file_name']
                source_type = "file"
            else:
                # Fallback: use document ID
                source_url = f"Document {idx}"
            
            # Get page number if available
            page_num = metadata.get('page_label') or metadata.get('page_number')
            
            # Get document title
            title = metadata.get('title') or metadata.get('doc_title')
            
            # Build source entry
            source_entry = {
                "index": idx,
                "source": source_url,  # This is the URL or filename
                "type": source_type,
                "score": float(node.score) if hasattr(node, 'score') else 1.0,
            }
            
            # Add optional fields
            if page_num:
                source_entry["page"] = page_num
            if title:
                source_entry["title"] = title
            
            # Add domain for web sources
            if source_type == "webpage":
                try:
                    parsed = urlparse(source_url)
                    source_entry["domain"] = parsed.netloc
                except:
                    pass
            
            formatted_sources.append(source_entry)
            
        except Exception as e:
            logging.warning(f"Error formatting source {idx}: {e}")
            # Fallback source
            formatted_sources.append({
                "index": idx,
                "source": f"Document {idx}",
                "type": "unknown",
                "score": 1.0
            })
    
    return formatted_sources


def enrich_documents_with_urls(documents: List[Any], url: str, title: str = None):
    """
    Add URL metadata to documents before indexing.
    
    Args:
        documents: List of LlamaIndex Document objects
        url: Source URL
        title: Optional document title
    """
    for doc in documents:
        if not hasattr(doc, 'metadata'):
            doc.metadata = {}
        
        # Add URL metadata
        doc.metadata['url'] = url
        doc.metadata['source'] = url
        
        if title:
            doc.metadata['title'] = title
        
        # Extract domain
        try:
            parsed = urlparse(url)
            doc.metadata['domain'] = parsed.netloc
            doc.metadata['source_type'] = 'webpage'
        except:
            pass
    
    logging.info(f"Enriched {len(documents)} documents with URL: {url}")


def enrich_file_with_metadata(documents: List[Any], file_path: str, tenant_id: str = None):
    """
    Add file metadata to documents before indexing.
    
    Args:
        documents: List of LlamaIndex Document objects
        file_path: Path to source file
        tenant_id: Optional tenant ID
    """
    file_name = Path(file_path).name
    
    for doc in documents:
        if not hasattr(doc, 'metadata'):
            doc.metadata = {}
        
        # Add file metadata
        doc.metadata['source'] = file_name
        doc.metadata['file_name'] = file_name
        doc.metadata['file_path'] = file_path
        doc.metadata['source_type'] = 'file'
        
        if tenant_id:
            doc.metadata['tenant_id'] = tenant_id
    
    logging.info(f"Enriched {len(documents)} documents from file: {file_name}")


def format_source_citation(source: Dict[str, Any]) -> str:
    """
    Format a source as a citation string.
    
    Args:
        source: Source dictionary
        
    Returns:
        Formatted citation string
    """
    source_str = source.get('source', 'Unknown')
    
    # For web sources, show as clickable link format
    if source.get('type') == 'webpage':
        if source.get('title'):
            return f"[{source['title']}]({source_str})"
        else:
            domain = source.get('domain', source_str)
            return f"[{domain}]({source_str})"
    
    # For files, show filename with page if available
    else:
        citation = source_str
        if source.get('page'):
            citation += f" (Page {source['page']})"
        return citation


def deduplicate_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate sources (same URL/file).
    
    Args:
        sources: List of source dictionaries
        
    Returns:
        Deduplicated list of sources
    """
    seen = {}
    unique_sources = []
    
    for source in sources:
        source_key = source.get('source')
        
        if source_key not in seen:
            seen[source_key] = True
            unique_sources.append(source)
        else:
            # If duplicate, keep the one with higher score
            for i, existing in enumerate(unique_sources):
                if existing.get('source') == source_key:
                    if source.get('score', 0) > existing.get('score', 0):
                        unique_sources[i] = source
                    break
    
    return unique_sources


# Global URL tracker instance
_url_tracker = URLTracker()


def get_url_tracker() -> URLTracker:
    """Get global URL tracker instance."""
    return _url_tracker
