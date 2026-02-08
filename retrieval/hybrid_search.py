"""
Hybrid search combining BM25 (keyword) and semantic search.
Best practice for production RAG systems.
"""
import logging
from typing import List, Optional
from llama_index.core import VectorStoreIndex, QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever, BM25Retriever
from llama_index.core.schema import NodeWithScore
from config import settings


class HybridRetriever(BaseRetriever):
    """
    Combines semantic search (embeddings) with keyword search (BM25).
    Uses Reciprocal Rank Fusion (RRF) to merge results.
    """
    
    def __init__(
        self,
        vector_index: VectorStoreIndex,
        similarity_top_k: int = 10,
        bm25_top_k: int = 10,
        alpha: float = 0.5  # Weight for semantic vs keyword (0=BM25 only, 1=semantic only)
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_index: LlamaIndex vector store index
            similarity_top_k: Number of results from semantic search
            bm25_top_k: Number of results from BM25 search
            alpha: Weight between semantic and BM25 (0.0 to 1.0)
        """
        self.vector_retriever = VectorIndexRetriever(
            index=vector_index,
            similarity_top_k=similarity_top_k
        )
        
        self.bm25_retriever = BM25Retriever.from_defaults(
            index=vector_index,
            similarity_top_k=bm25_top_k
        )
        
        self.alpha = alpha
        logging.info(f"HybridRetriever initialized (alpha={alpha})")
    
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        """
        Retrieve nodes using hybrid approach.
        """
        # Get results from both retrievers
        semantic_nodes = self.vector_retriever.retrieve(query_bundle)
        bm25_nodes = self.bm25_retriever.retrieve(query_bundle)
        
        # Merge using Reciprocal Rank Fusion (RRF)
        merged_nodes = self._reciprocal_rank_fusion(
            semantic_nodes,
            bm25_nodes,
            alpha=self.alpha
        )
        
        return merged_nodes
    
    @staticmethod
    def _reciprocal_rank_fusion(
        semantic_nodes: List[NodeWithScore],
        bm25_nodes: List[NodeWithScore],
        alpha: float = 0.5,
        k: int = 60  # RRF constant
    ) -> List[NodeWithScore]:
        """
        Merge results using Reciprocal Rank Fusion.
        
        RRF formula: score = alpha * (1/(k + rank_semantic)) + (1-alpha) * (1/(k + rank_bm25))
        """
        # Build node score maps
        node_scores = {}
        
        # Add semantic scores
        for rank, node in enumerate(semantic_nodes, start=1):
            node_id = node.node.node_id
            rrf_score = alpha / (k + rank)
            node_scores[node_id] = {
                'node': node,
                'score': rrf_score
            }
        
        # Add BM25 scores
        for rank, node in enumerate(bm25_nodes, start=1):
            node_id = node.node.node_id
            rrf_score = (1 - alpha) / (k + rank)
            
            if node_id in node_scores:
                node_scores[node_id]['score'] += rrf_score
            else:
                node_scores[node_id] = {
                    'node': node,
                    'score': rrf_score
                }
        
        # Sort by combined score
        sorted_nodes = sorted(
            node_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Return nodes with updated scores
        result = []
        for item in sorted_nodes:
            node = item['node']
            node.score = item['score']
            result.append(node)
        
        return result


def create_hybrid_retriever(vector_index: VectorStoreIndex) -> HybridRetriever:
    """
    Factory function to create hybrid retriever from settings.
    """
    return HybridRetriever(
        vector_index=vector_index,
        similarity_top_k=settings.SIMILARITY_TOP_K,
        bm25_top_k=settings.SIMILARITY_TOP_K,
        alpha=0.5  # Equal weight to semantic and keyword
    )
