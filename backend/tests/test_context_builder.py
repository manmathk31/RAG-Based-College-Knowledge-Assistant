"""Unit tests for ContextBuilder: token budget enforcement, deduplication, and citation mapping."""

import pytest

from app.core.config import Settings
from app.retrieval.context import ContextBuilder
from app.retrieval.models import RetrievalCandidate


def make_cand(chunk_id: str, content: str, page: int = 1, doc_name: str = "Doc.pdf"):
    return RetrievalCandidate(
        chunk_id=chunk_id,
        document_id="doc-test",
        document_name=doc_name,
        document_version=1,
        page_number=page,
        section="Regulations",
        content=content,
        score=0.9,
        rank=1,
        retrieval_source="dense",
    )


def test_context_builder_empty_candidates_returns_empty():
    """Verify that empty candidate list yields empty context and empty citations."""
    builder = ContextBuilder()
    context_text, citations = builder.build_context([])
    assert context_text == ""
    assert citations == []


def test_context_builder_citation_numbering_and_snippets():
    """Verify that chunks are formatted with [1], [2] headers and citations are properly mapped."""
    builder = ContextBuilder()
    cands = [
        make_cand("c1", "First excerpt discussing exam registration.", page=2, doc_name="Exam_Rules.pdf"),
        make_cand("c2", "Second excerpt discussing attendance policy.", page=5, doc_name="Academic_Policy.pdf"),
    ]

    context_text, citations = builder.build_context(cands, max_tokens=1000)

    assert "[1] Document: Exam_Rules.pdf (Page 2, Section: Regulations)" in context_text
    assert "[2] Document: Academic_Policy.pdf (Page 5, Section: Regulations)" in context_text
    assert "First excerpt discussing exam registration." in context_text
    assert "Second excerpt discussing attendance policy." in context_text

    assert len(citations) == 2
    assert citations[0].citation_id == "1"
    assert citations[0].document_name == "Exam_Rules.pdf"
    assert citations[0].page_number == 2
    assert "First excerpt" in citations[0].snippet

    assert citations[1].citation_id == "2"
    assert citations[1].document_name == "Academic_Policy.pdf"
    assert citations[1].page_number == 5


def test_context_builder_token_budget_enforcement():
    """Verify that chunks exceeding the token budget ceiling are omitted."""
    builder = ContextBuilder()
    long_text = "This is a sentence containing several words to fill up the token budget. " * 30
    cands = [
        make_cand("c1", long_text, page=1),
        make_cand("c2", long_text, page=2),
        make_cand("c3", long_text, page=3),
    ]

    # Very small token budget: should include 1 excerpt and stop
    context_text, citations = builder.build_context(cands, max_tokens=80)

    assert len(citations) == 1
    assert citations[0].citation_id == "1"


def test_context_builder_skips_near_duplicate_content():
    """Verify that duplicate content chunks are skipped to preserve context quality."""
    builder = ContextBuilder()
    content = "Identical policy wording for campus hostel fee payments."
    cands = [
        make_cand("c1", content, page=1),
        make_cand("c2", content, page=2),
    ]

    context_text, citations = builder.build_context(cands, max_tokens=1000)

    assert len(citations) == 1
    assert citations[0].chunk_id == "c1"

