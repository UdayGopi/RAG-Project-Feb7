"""
Metadata filtering for improved retrieval precision.
"""
import logging
from typing import Dict, Any, List, Optional
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter as LIMetadataFilter, FilterOperator


class MetadataFilter:
    """Helper for creating metadata filters."""
    
    @staticmethod
    def create_tenant_filter(tenant_id: str) -> MetadataFilters:
        """
        Create filter for specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            MetadataFilters object
        """
        return MetadataFilters(
            filters=[
                LIMetadataFilter(
                    key="tenant_id",
                    value=tenant_id,
                    operator=FilterOperator.EQ
                )
            ]
        )
    
    @staticmethod
    def create_document_type_filter(doc_type: str) -> MetadataFilters:
        """
        Create filter for document type.
        
        Args:
            doc_type: Document type (policy, guide, form, etc.)
            
        Returns:
            MetadataFilters object
        """
        return MetadataFilters(
            filters=[
                LIMetadataFilter(
                    key="doc_type",
                    value=doc_type,
                    operator=FilterOperator.EQ
                )
            ]
        )
    
    @staticmethod
    def create_date_range_filter(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> MetadataFilters:
        """
        Create filter for date range.
        
        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            MetadataFilters object
        """
        filters = []
        
        if start_date:
            filters.append(
                LIMetadataFilter(
                    key="date",
                    value=start_date,
                    operator=FilterOperator.GTE
                )
            )
        
        if end_date:
            filters.append(
                LIMetadataFilter(
                    key="date",
                    value=end_date,
                    operator=FilterOperator.LTE
                )
            )
        
        return MetadataFilters(filters=filters) if filters else None
    
    @staticmethod
    def create_combined_filter(
        tenant_id: Optional[str] = None,
        doc_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_filters: Optional[Dict[str, Any]] = None
    ) -> MetadataFilters:
        """
        Create combined metadata filters.
        
        Args:
            tenant_id: Optional tenant filter
            doc_type: Optional document type filter
            tags: Optional tags to match (any)
            custom_filters: Additional custom filters
            
        Returns:
            Combined MetadataFilters object
        """
        filters = []
        
        if tenant_id:
            filters.append(
                LIMetadataFilter(
                    key="tenant_id",
                    value=tenant_id,
                    operator=FilterOperator.EQ
                )
            )
        
        if doc_type:
            filters.append(
                LIMetadataFilter(
                    key="doc_type",
                    value=doc_type,
                    operator=FilterOperator.EQ
                )
            )
        
        if tags:
            # Match any of the provided tags
            filters.append(
                LIMetadataFilter(
                    key="tags",
                    value=tags,
                    operator=FilterOperator.IN
                )
            )
        
        if custom_filters:
            for key, value in custom_filters.items():
                filters.append(
                    LIMetadataFilter(
                        key=key,
                        value=value,
                        operator=FilterOperator.EQ
                    )
                )
        
        return MetadataFilters(filters=filters) if filters else None


def extract_filters_from_query(query: str) -> Dict[str, Any]:
    """
    Extract metadata filter hints from natural language query.
    
    Args:
        query: User query
        
    Returns:
        Dictionary of detected filters
    """
    filters = {}
    query_lower = query.lower()
    
    # Document type detection
    if "policy" in query_lower or "policies" in query_lower:
        filters["doc_type"] = "policy"
    elif "guide" in query_lower or "manual" in query_lower:
        filters["doc_type"] = "guide"
    elif "form" in query_lower:
        filters["doc_type"] = "form"
    
    # Tenant detection (basic)
    if "hih" in query_lower or "health information handler" in query_lower:
        filters["tenant_id"] = "HIH"
    elif "rc" in query_lower or "review contractor" in query_lower:
        filters["tenant_id"] = "RC"
    
    # Date patterns (simple)
    import re
    year_match = re.search(r'\b(20\d{2})\b', query)
    if year_match:
        filters["year"] = year_match.group(1)
    
    return filters
