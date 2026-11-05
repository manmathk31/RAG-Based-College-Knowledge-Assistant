"""Abstract interface for LLM answer generation services."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseGenerationService(ABC):
    """Abstract contract for generative language model answer providers."""

    @abstractmethod
    async def generate_answer(
        self,
        query: str,
        context_text: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generate a grounded answer based on query, document context, and optional history.

        Args:
            query: The student's question.
            context_text: Formatted excerpts from official college documents.
            history: Optional recent conversation turns [{'role': 'user'|'assistant', 'content': '...'}].

        Returns:
            Grounded answer text with citation markers like [1], [2].
        """
        pass

