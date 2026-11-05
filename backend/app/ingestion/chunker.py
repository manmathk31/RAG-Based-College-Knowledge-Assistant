"""Structure-aware recursive text chunker with token-counting and heading preservation."""

import logging
import re
from typing import Any, Dict, List, Optional
import tiktoken

from app.core.config import Settings, get_settings
from app.core.exceptions import ChunkingError
from app.ingestion.models import DocumentChunk, ExtractedBlock, ExtractedDocument

logger = logging.getLogger(__name__)


class StructureAwareChunker:
    """Splits extracted documents into structured, token-bounded chunks preserving document context."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        encoding_name: Optional[str] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._chunk_size = chunk_size or self._settings.CHUNK_SIZE
        self._chunk_overlap = chunk_overlap or self._settings.CHUNK_OVERLAP
        self._encoding_name = encoding_name or self._settings.TOKENIZER_ENCODING

        if self._chunk_overlap >= self._chunk_size:
            raise ValueError(f"chunk_overlap ({self._chunk_overlap}) must be smaller than chunk_size ({self._chunk_size}).")

        # Initialize tiktoken BPE encoding with graceful fallback
        try:
            self._tokenizer = tiktoken.get_encoding(self._encoding_name)
        except Exception as exc:
            logger.warning("Could not initialize tiktoken encoding '%s': %s. Using whitespace fallback.", self._encoding_name, exc)
            self._tokenizer = None

        logger.info(
            "Initialized StructureAwareChunker (chunk_size=%d tokens, chunk_overlap=%d tokens, encoding=%s)",
            self._chunk_size,
            self._chunk_overlap,
            self._encoding_name,
        )

    def count_tokens(self, text: str) -> int:
        """Count the number of BPE tokens in a string."""
        if not text:
            return 0
        if self._tokenizer:
            try:
                return len(self._tokenizer.encode(text, disallowed_special=()))
            except Exception:
                pass
        # Fallback heuristic: 1 word ~ 1.33 tokens
        return max(1, int(len(text.split()) * 1.33))

    def chunk_document(self, document: ExtractedDocument) -> List[DocumentChunk]:
        """Split an ExtractedDocument into structured, deterministic DocumentChunk objects.

        Args:
            document: ExtractedDocument containing pages, blocks, and metadata.

        Returns:
            List of DocumentChunk objects with preserved metadata and deterministic chunk_ids.
        """
        if not document.blocks and not document.pages:
            return []

        # If blocks are empty, synthesize blocks from pages
        blocks = document.blocks
        if not blocks:
            blocks = [
                ExtractedBlock(
                    text=p.text,
                    block_type="paragraph",
                    page_number=p.page_number,
                )
                for p in document.pages
                if p.text.strip()
            ]

        if not blocks:
            return []

        chunks: List[DocumentChunk] = []
        chunk_index = 0
        active_heading: Optional[str] = None

        # Accumulator for building the current chunk
        current_content_parts: List[str] = []
        current_pages: List[int] = []
        current_section: Optional[str] = None

        def flush_current_chunk() -> None:
            nonlocal chunk_index, current_content_parts, current_pages, current_section
            if not current_content_parts:
                return

            raw_content = "\n\n".join(p.strip() for p in current_content_parts if p.strip()).strip()
            if not raw_content:
                current_content_parts.clear()
                current_pages.clear()
                return

            # Prepend active heading if not already at the start of content
            final_content = raw_content
            if current_section and not final_content.startswith(current_section):
                # Ensure the heading context is explicitly captured
                final_content = f"[{current_section}]\n{final_content}"

            token_count = self.count_tokens(final_content)
            page_min = min(current_pages) if current_pages else 1
            page_max = max(current_pages) if current_pages else page_min

            chunk_id = f"{document.document_id}_p{page_min}_c{chunk_index}"
            chunk = DocumentChunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                chunk_index=chunk_index,
                content=final_content,
                token_count=token_count,
                char_count=len(final_content),
                page_number=page_min,
                page_range=[page_min, page_max] if page_min != page_max else [page_min],
                section_title=current_section,
                source_filename=document.filename,
                file_type=document.file_type,
                metadata={
                    **document.metadata,
                },
            )
            chunks.append(chunk)
            chunk_index += 1

            # Compute overlap content for next chunk
            overlap_parts = self._compute_overlap_parts(current_content_parts)
            current_content_parts = overlap_parts
            current_pages = [page_max] if overlap_parts else []

        for block in blocks:
            text = block.text.strip()
            if not text:
                continue

            page_no = block.page_number or 1

            # Flush on page boundary to avoid combining unrelated content from different pages
            if current_pages and page_no not in current_pages:
                flush_current_chunk()

            # Update heading context and flush on section boundaries
            if block.block_type == "heading":
                if current_content_parts:
                    flush_current_chunk()
                active_heading = text
                current_section = active_heading
                continue

            if block.section_title:
                current_section = block.section_title
            elif active_heading:
                current_section = active_heading

            block_tokens = self.count_tokens(text)

            # Case A: Block itself exceeds chunk_size -> recursively split it
            if block_tokens > self._chunk_size:
                # Flush existing content first
                if current_content_parts:
                    flush_current_chunk()

                sub_chunks = self._recursive_split_text(text, target_size=self._chunk_size)
                for sub_text in sub_chunks:
                    current_content_parts = [sub_text]
                    current_pages = [page_no]
                    flush_current_chunk()
                continue

            # Case B: Adding this block would exceed chunk_size -> flush and start new chunk
            projected_text = "\n\n".join(current_content_parts + [text])
            if self.count_tokens(projected_text) > self._chunk_size:
                flush_current_chunk()

            current_content_parts.append(text)
            current_pages.append(page_no)

        # Final flush
        flush_current_chunk()

        logger.debug("Document '%s' produced %d chunks.", document.filename, len(chunks))
        return chunks

    def _compute_overlap_parts(self, parts: List[str]) -> List[str]:
        """Select tail parts whose cumulative tokens fit within chunk_overlap."""
        if not parts or self._chunk_overlap <= 0:
            return []

        overlap_parts: List[str] = []
        accumulated_tokens = 0

        # Traverse backwards from the end
        for part in reversed(parts):
            part_tokens = self.count_tokens(part)
            if accumulated_tokens + part_tokens <= self._chunk_overlap:
                overlap_parts.insert(0, part)
                accumulated_tokens += part_tokens
            else:
                # If even 1 part exceeds overlap, but overlap is empty, take tail slice of last part
                if not overlap_parts:
                    tail_text = self._tail_tokens(part, max_tokens=self._chunk_overlap)
                    if tail_text:
                        overlap_parts.append(tail_text)
                break

        return overlap_parts

    def _tail_tokens(self, text: str, max_tokens: int) -> str:
        """Return the trailing portion of text containing approximately max_tokens."""
        sentences = re.split(r"(?<=[.?!])\s+", text)
        tail_sentences: List[str] = []
        tokens = 0
        for s in reversed(sentences):
            st = self.count_tokens(s)
            if tokens + st <= max_tokens:
                tail_sentences.insert(0, s)
                tokens += st
            else:
                break
        return " ".join(tail_sentences)

    def _recursive_split_text(self, text: str, target_size: int) -> List[str]:
        """Recursively split long text by prioritized separators down to target_size tokens."""
        if self.count_tokens(text) <= target_size:
            return [text]

        separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

        for sep in separators:
            if sep in text:
                splits = text.split(sep)
                result: List[str] = []
                current_segment: List[str] = []

                for piece in splits:
                    piece_candidate = sep.join(current_segment + [piece]).strip() if current_segment else piece.strip()
                    if self.count_tokens(piece_candidate) <= target_size:
                        current_segment.append(piece)
                    else:
                        if current_segment:
                            result.append(sep.join(current_segment).strip())
                            current_segment = []

                        # If this single piece is still too large, recurse further
                        if self.count_tokens(piece) > target_size:
                            result.extend(self._recursive_split_text(piece, target_size))
                        else:
                            current_segment.append(piece)

                if current_segment:
                    result.append(sep.join(current_segment).strip())

                # If separation succeeded in reducing chunks, return
                if len(result) > 1:
                    return [r for r in result if r.strip()]

        # Fallback: force character-level split if no separator worked
        char_step = target_size * 3
        return [text[i : i + char_step].strip() for i in range(0, len(text), char_step) if text[i : i + char_step].strip()]
