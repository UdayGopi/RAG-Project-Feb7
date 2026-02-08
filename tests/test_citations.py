"""
Test suite for source citations and URL tracking.
"""
import pytest
from pathlib import Path
from llama_index.core.schema import NodeWithScore, TextNode

# Test utilities
from utils.url_tracker import (
    format_sources_with_urls,
    deduplicate_sources,
    enrich_documents_with_urls,
    enrich_file_with_metadata,
    format_source_citation
)


class TestSourceFormatting:
    """Test source formatting functions."""
    
    def test_url_source_formatting(self):
        """Test that URL sources are formatted correctly."""
        # Create test node with URL metadata
        node = NodeWithScore(
            node=TextNode(
                text="Medicare covers inpatient hospital stays...",
                metadata={
                    'url': 'https://www.cms.gov/medicare/part-a',
                    'source': 'https://www.cms.gov/medicare/part-a',
                    'title': 'Medicare Part A Coverage',
                    'domain': 'www.cms.gov'
                }
            ),
            score=0.92
        )
        
        # Format sources
        sources = format_sources_with_urls([node])
        
        # Assertions
        assert len(sources) == 1
        assert sources[0]['source'] == 'https://www.cms.gov/medicare/part-a'
        assert sources[0]['type'] == 'webpage'
        assert sources[0]['domain'] == 'www.cms.gov'
        assert sources[0]['title'] == 'Medicare Part A Coverage'
        assert sources[0]['score'] == 0.92
        
        # Ensure it's NOT showing extracted text
        assert 'text' not in sources[0]
        assert len(sources[0]['source']) < 500  # URL, not content
    
    def test_file_source_formatting(self):
        """Test that file sources are formatted correctly."""
        node = NodeWithScore(
            node=TextNode(
                text="Policy states that...",
                metadata={
                    'file_name': 'HIH_Policy_2024.pdf',
                    'source': 'HIH_Policy_2024.pdf',
                    'page_number': 5,
                    'source_type': 'file'
                }
            ),
            score=0.88
        )
        
        sources = format_sources_with_urls([node])
        
        assert len(sources) == 1
        assert sources[0]['source'] == 'HIH_Policy_2024.pdf'
        assert sources[0]['type'] == 'file'
        assert sources[0]['page'] == 5
        assert sources[0]['score'] == 0.88
    
    def test_source_deduplication(self):
        """Test that duplicate sources are removed."""
        nodes = [
            NodeWithScore(
                node=TextNode(
                    text="Text 1",
                    metadata={'url': 'https://www.cms.gov/page', 'source': 'https://www.cms.gov/page'}
                ),
                score=0.92
            ),
            NodeWithScore(
                node=TextNode(
                    text="Text 2",
                    metadata={'url': 'https://www.cms.gov/page', 'source': 'https://www.cms.gov/page'}
                ),
                score=0.85
            ),
            NodeWithScore(
                node=TextNode(
                    text="Text 3",
                    metadata={'url': 'https://www.hhs.gov/other', 'source': 'https://www.hhs.gov/other'}
                ),
                score=0.80
            )
        ]
        
        sources = format_sources_with_urls(nodes)
        deduplicated = deduplicate_sources(sources)
        
        # Should have 2 unique sources (not 3)
        assert len(deduplicated) == 2
        
        # Should keep the higher score for duplicate
        cms_source = [s for s in deduplicated if 'cms.gov' in s['source']][0]
        assert cms_source['score'] == 0.92  # Kept higher score


class TestURLEnrichment:
    """Test URL enrichment functions."""
    
    def test_enrich_documents_with_urls(self):
        """Test that documents are enriched with URL metadata."""
        from llama_index.core import Document
        
        # Create test documents
        docs = [
            Document(text="Content 1"),
            Document(text="Content 2")
        ]
        
        # Enrich with URL
        enrich_documents_with_urls(
            docs,
            url="https://www.cms.gov/regulations",
            title="CMS Regulations"
        )
        
        # Check metadata
        for doc in docs:
            assert 'url' in doc.metadata
            assert doc.metadata['url'] == 'https://www.cms.gov/regulations'
            assert doc.metadata['source'] == 'https://www.cms.gov/regulations'
            assert doc.metadata['title'] == 'CMS Regulations'
            assert doc.metadata['domain'] == 'www.cms.gov'
            assert doc.metadata['source_type'] == 'webpage'
    
    def test_enrich_file_with_metadata(self):
        """Test that files are enriched with proper metadata."""
        from llama_index.core import Document
        
        docs = [Document(text="Policy content")]
        
        enrich_file_with_metadata(
            docs,
            file_path="/path/to/HIH_Policy.pdf",
            tenant_id="HIH"
        )
        
        # Check metadata
        assert docs[0].metadata['source'] == 'HIH_Policy.pdf'
        assert docs[0].metadata['file_name'] == 'HIH_Policy.pdf'
        assert docs[0].metadata['file_path'] == '/path/to/HIH_Policy.pdf'
        assert docs[0].metadata['source_type'] == 'file'
        assert docs[0].metadata['tenant_id'] == 'HIH'


class TestCitationFormatting:
    """Test citation formatting."""
    
    def test_webpage_citation(self):
        """Test webpage citation formatting."""
        source = {
            'source': 'https://www.cms.gov/medicare',
            'type': 'webpage',
            'title': 'Medicare Overview',
            'domain': 'www.cms.gov'
        }
        
        citation = format_source_citation(source)
        
        # Should be markdown link format
        assert '[Medicare Overview]' in citation
        assert '(https://www.cms.gov/medicare)' in citation
    
    def test_file_citation(self):
        """Test file citation formatting."""
        source = {
            'source': 'HIH_Policy.pdf',
            'type': 'file',
            'page': 12
        }
        
        citation = format_source_citation(source)
        
        assert 'HIH_Policy.pdf' in citation
        assert 'Page 12' in citation


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
