"""
URL processing and ingestion with proper metadata tracking.
"""
import logging
from typing import List, Dict, Any
from llama_index.core import Document
from llama_index.core import download_loader


class URLProcessor:
    """Process URLs and maintain source attribution."""
    
    def __init__(self, allowed_domains: List[str] = None):
        """
        Initialize URL processor.
        
        Args:
            allowed_domains: List of allowed domains for scraping
        """
        self.allowed_domains = allowed_domains or [
            "www.cms.gov",
            "esmdguide-fhir.cms.hhs.gov",
            "www.hhs.gov"
        ]
        
        # Load web reader
        try:
            TrafilaturaWebReader = download_loader("TrafilaturaWebReader")
            self.web_reader = TrafilaturaWebReader()
            logging.info("TrafilaturaWebReader loaded")
        except Exception as e:
            logging.warning(f"Could not load TrafilaturaWebReader: {e}")
            self.web_reader = None
    
    def is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is allowed."""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc
            return any(allowed in domain for allowed in self.allowed_domains)
        except:
            return False
    
    def process_url(self, url: str, tenant_id: str = None) -> List[Document]:
        """
        Process URL and return documents with proper metadata.
        
        Args:
            url: URL to process
            tenant_id: Optional tenant ID
            
        Returns:
            List of Document objects with URL metadata
        """
        # Validate domain
        if not self.is_allowed_domain(url):
            raise ValueError(f"Domain not allowed: {url}")
        
        # Load documents from URL
        if self.web_reader:
            documents = self.web_reader.load_data(urls=[url])
        else:
            # Fallback: simple requests
            documents = self._load_with_requests(url)
        
        # Enrich documents with URL metadata
        for doc in documents:
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            
            # Add URL metadata
            doc.metadata['url'] = url
            doc.metadata['source'] = url  # THIS IS KEY - source should be the URL
            doc.metadata['source_type'] = 'webpage'
            
            # Extract domain
            from urllib.parse import urlparse
            try:
                parsed = urlparse(url)
                doc.metadata['domain'] = parsed.netloc
            except:
                pass
            
            # Add tenant if provided
            if tenant_id:
                doc.metadata['tenant_id'] = tenant_id
            
            # Extract title from content if available
            if hasattr(doc, 'text') and doc.text:
                # Try to extract title from first line or heading
                first_line = doc.text.split('\n')[0].strip()
                if len(first_line) < 200:  # Reasonable title length
                    doc.metadata['title'] = first_line
        
        logging.info(f"Processed URL: {url} -> {len(documents)} documents")
        return documents
    
    def _load_with_requests(self, url: str) -> List[Document]:
        """Fallback: Load URL with requests library."""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Extract title
            title = soup.title.string if soup.title else url
            
            # Create document
            doc = Document(
                text=text,
                metadata={
                    'url': url,
                    'source': url,
                    'title': title,
                    'source_type': 'webpage'
                }
            )
            
            return [doc]
            
        except Exception as e:
            logging.error(f"Failed to load URL {url}: {e}")
            return []
    
    def process_multiple_urls(
        self,
        urls: List[str],
        tenant_id: str = None
    ) -> Dict[str, List[Document]]:
        """
        Process multiple URLs.
        
        Args:
            urls: List of URLs to process
            tenant_id: Optional tenant ID
            
        Returns:
            Dictionary mapping URL to documents
        """
        results = {}
        
        for url in urls:
            try:
                documents = self.process_url(url, tenant_id)
                results[url] = documents
            except Exception as e:
                logging.error(f"Error processing {url}: {e}")
                results[url] = []
        
        return results


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    processor = URLProcessor()
    
    # Process a URL
    url = "https://www.cms.gov/example-page"
    documents = processor.process_url(url, tenant_id="HIH")
    
    print(f"Processed {len(documents)} documents from {url}")
    for doc in documents:
        print(f"  - Metadata: {doc.metadata}")
