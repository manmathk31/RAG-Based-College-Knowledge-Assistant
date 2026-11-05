"""Context builder: selects top ranked chunks, enforces token budgets, and formats source citations."""

import logging
from typing import List, Optional, Set, Tuple

import tiktoken

from app.core.config import Settings, get_settings
from app.retrieval.models import RetrievalCandidate, SourceCitation

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Assembles ranked retrieval candidate chunks into a structured prompt context

    strictly bounded by a configurable token budget.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        try:
            self._tokenizer = tiktoken.get_encoding(self._settings.TOKENIZER_ENCODING)
        except Exception:
            self._tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken with a safe word-ratio fallback."""
        if not text:
            return 0
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text))
            except Exception:
                pass
        return max(1, len(text.split()) * 4 // 3)

    def build_context(
        self,
        candidates: List[RetrievalCandidate],
        max_tokens: Optional[int] = None,
    ) -> Tuple[str, List[SourceCitation]]:
        """Construct prompt context string and corresponding citation mapping.

        Args:
            candidates: Ranked candidate chunks (e.g. from RRF).
            max_tokens: Optional token ceiling; defaults to Settings.MAX_CONTEXT_TOKENS.

        Returns:
            Tuple of (formatted_context_string, list_of_source_citations).
        """
        token_budget = max_tokens or self._settings.MAX_CONTEXT_TOKENS
        accumulated_tokens = 0

        context_blocks: List[str] = []
        citations: List[SourceCitation] = []
        seen_contents: Set[str] = set()

        citation_num = 1
        for cand in candidates:
            content = cand.content.strip()
            if not content:
                continue

            # Skip exact duplicate or near-identical text
            norm_content = " ".join(content.split()[:20]).lower()
            if norm_content in seen_contents:
                continue
            seen_contents.add(norm_content)

            page_info = f"Page {cand.page_number}" if cand.page_number else "Document Overview"
            section_info = f", Section: {cand.section}" if cand.section else ""
            header = f"[{citation_num}] Document: {cand.document_name} ({page_info}{section_info})"
            block = f"{header}\n{content}"

            block_tokens = self.count_tokens(block)
            if accumulated_tokens + block_tokens > token_budget and context_blocks:
                logger.debug(
                    "Context token ceiling reached: %d/%d tokens used with %d excerpts.",
                    accumulated_tokens,
                    token_budget,
                    len(context_blocks),
                )
                break

            context_blocks.append(block)
            accumulated_tokens += block_tokens

            # Create clean snippet for citation
            snippet = content[:150] + ("..." if len(content) > 150 else "")

            citations.append(
                SourceCitation(
                    citation_id=str(citation_num),
                    document_id=cand.document_id,
                    document_name=cand.document_name,
                    document_version=cand.document_version,
                    page_number=cand.page_number,
                    section=cand.section,
                    chunk_id=cand.chunk_id,
                    snippet=snippet,
                )
            )
            citation_num += 1

        formatted_context = "\n\n".join(context_blocks)
        logger.debug(
            "Built context with %d excerpts, total %d tokens.",
            len(citations),
            accumulated_tokens,
        )
        return formatted_context, citations

