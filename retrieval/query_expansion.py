"""
Query expansion techniques to improve retrieval recall.
"""
import logging
from typing import List
from config import settings


class QueryExpander:
    """Expands queries using various techniques."""
    
    def __init__(self, llm=None):
        """
        Initialize query expander.
        
        Args:
            llm: Language model for generating expansions
        """
        self.llm = llm
        if self.llm:
            logging.info("QueryExpander initialized with LLM")
        else:
            logging.info("QueryExpander initialized (no LLM, using rule-based)")
    
    def expand_query(self, query: str, method: str = "synonyms") -> List[str]:
        """
        Expand a query using specified method.
        
        Args:
            query: Original query
            method: Expansion method ('synonyms', 'multi_query', 'hyde')
            
        Returns:
            List of expanded queries (including original)
        """
        if method == "synonyms":
            return self._expand_with_synonyms(query)
        elif method == "multi_query":
            return self._multi_query_expansion(query)
        elif method == "hyde":
            return self._hypothetical_document_expansion(query)
        else:
            return [query]
    
    def _expand_with_synonyms(self, query: str) -> List[str]:
        """
        Simple synonym-based expansion.
        """
        # Domain-specific synonym mappings
        synonyms = {
            "guide": ["manual", "handbook", "documentation"],
            "form": ["document", "template", "application"],
            "policy": ["guideline", "regulation", "rule"],
            "extension": ["addon", "plugin", "module"],
            "implementation": ["setup", "deployment", "integration"],
        }
        
        queries = [query]
        words = query.lower().split()
        
        for word in words:
            if word in synonyms:
                for synonym in synonyms[word][:1]:  # Use first synonym only
                    expanded = query.lower().replace(word, synonym)
                    if expanded != query.lower():
                        queries.append(expanded)
        
        return queries[:settings.QUERY_EXPANSION_COUNT + 1]
    
    def _multi_query_expansion(self, query: str) -> List[str]:
        """
        Generate multiple variations of the query using LLM.
        """
        if not self.llm:
            return [query]
        
        prompt = f"""Generate {settings.QUERY_EXPANSION_COUNT} alternative ways to ask this question.
Each variation should preserve the original meaning but use different words or phrasing.

Original question: {query}

Alternative questions:
1."""
        
        try:
            response = self.llm.complete(prompt)
            variations = [query]  # Always include original
            
            # Parse response
            lines = response.text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit():
                    # Remove numbering
                    variation = line.split('.', 1)[-1].strip()
                    if variation and variation != query:
                        variations.append(variation)
            
            return variations[:settings.QUERY_EXPANSION_COUNT + 1]
        
        except Exception as e:
            logging.error(f"Multi-query expansion failed: {e}")
            return [query]
    
    def _hypothetical_document_expansion(self, query: str) -> List[str]:
        """
        HyDE: Generate hypothetical ideal answer, use for retrieval.
        """
        if not self.llm:
            return [query]
        
        prompt = f"""Given this question, write a detailed, accurate answer as it might appear in a policy document or guide.
Be specific and use domain terminology.

Question: {query}

Ideal answer:"""
        
        try:
            response = self.llm.complete(prompt)
            hypothetical_doc = response.text.strip()
            
            # Return both original query and hypothetical doc
            return [query, hypothetical_doc]
        
        except Exception as e:
            logging.error(f"HyDE expansion failed: {e}")
            return [query]


def expand_query(query: str, llm=None, method: str = "synonyms") -> List[str]:
    """
    Convenience function to expand a query.
    
    Args:
        query: Original query
        llm: Optional LLM for advanced expansion
        method: Expansion method
        
    Returns:
        List of query variations
    """
    expander = QueryExpander(llm=llm)
    return expander.expand_query(query, method=method)
