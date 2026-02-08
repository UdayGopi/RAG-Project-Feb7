"""
Intent classification for queries.
"""
import re
import logging
from typing import Tuple
from config.constants import IntentType, GREETING_PATTERNS, DOWNLOAD_KEYWORDS


class IntentClassifier:
    """Classifies user query intent."""
    
    def __init__(self):
        self.greeting_patterns = [re.compile(p, re.IGNORECASE) for p in GREETING_PATTERNS]
    
    def classify(self, query: str) -> Tuple[IntentType, float]:
        """
        Classify query intent.
        
        Args:
            query: User query
            
        Returns:
            Tuple of (intent_type, confidence)
        """
        query_lower = query.lower().strip()
        
        # Check for greetings/small talk
        for pattern in self.greeting_patterns:
            if pattern.search(query_lower):
                return IntentType.SMALL_TALK, 0.9
        
        # Check for download requests
        if any(kw in query_lower for kw in DOWNLOAD_KEYWORDS):
            return IntentType.DOWNLOAD, 0.85
        
        # Check for clarification requests
        if self._is_clarification(query_lower):
            return IntentType.CLARIFY, 0.8
        
        # Check if meaningful question
        if self._is_meaningful_question(query):
            return IntentType.QUESTION, 0.9
        
        return IntentType.UNKNOWN, 0.5
    
    def _is_clarification(self, query: str) -> bool:
        """Check if query is asking for clarification."""
        clarification_words = [
            "what do you mean",
            "can you explain",
            "clarify",
            "elaborate",
            "more details",
            "tell me more"
        ]
        return any(phrase in query for phrase in clarification_words)
    
    def _is_meaningful_question(self, query: str) -> bool:
        """Check if query is a meaningful question."""
        # Remove punctuation and count words
        words = re.findall(r'\w+', query.lower())
        
        # Must have at least 2 meaningful words
        if len(words) < 2:
            return False
        
        # Check for question indicators
        question_words = {'what', 'where', 'when', 'who', 'how', 'why', 'which', 'can', 'do', 'does', 'is', 'are'}
        has_question_word = any(w in question_words for w in words[:3])  # Check first 3 words
        
        # Check for question mark
        has_question_mark = '?' in query
        
        return has_question_word or has_question_mark or len(words) >= 4


# Global instance
_classifier = IntentClassifier()


def classify_intent(query: str) -> Tuple[IntentType, float]:
    """Classify query intent using global classifier."""
    return _classifier.classify(query)
