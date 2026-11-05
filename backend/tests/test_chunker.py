"""Unit tests for structure-aware recursive chunking and metadata preservation."""

import pytest

from app.ingestion.chunker import StructureAwareChunker
from app.ingestion.models import ExtractedBlock, ExtractedDocument, ExtractedPage


@pytest.fixture
def test_chunker() -> StructureAwareChunker:
    # Use smaller chunk_size (100 tokens) and overlap (20 tokens) for crisp test assertions
    return StructureAwareChunker(
        chunk_size=100,
        chunk_overlap=20,
        encoding_name="cl100k_base",
    )


def test_chunk_normal_paragraphs(test_chunker: StructureAwareChunker) -> None:
    """Verify small paragraphs are grouped together up to chunk_size."""
    doc = ExtractedDocument(
        document_id="doc_normal_1",
        filename="college_rules.pdf",
        file_type="pdf",
        pages=[ExtractedPage(page_number=1, text="Page 1 text", char_count=11)],
        blocks=[
            ExtractedBlock(text="First paragraph of general instructions.", block_type="paragraph", page_number=1),
            ExtractedBlock(text="Second paragraph with specific fee schedules.", block_type="paragraph", page_number=1),
        ],
    )

    chunks = test_chunker.chunk_document(doc)

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.document_id == "doc_normal_1"
    assert chunk.source_filename == "college_rules.pdf"
    assert chunk.chunk_index == 0
    assert chunk.page_number == 1
    assert "First paragraph" in chunk.content
    assert "Second paragraph" in chunk.content
    assert chunk.token_count <= 100


def test_chunk_long_paragraph_recursive_splitting(test_chunker: StructureAwareChunker) -> None:
    """Verify long paragraphs (> 100 tokens) are recursively split across sentences."""
    # Build a long repetitive sentence block (~150 tokens)
    sentence = "The student disciplinary committee oversees all campus regulation violations and reports to the Dean. "
    long_text = sentence * 12

    doc = ExtractedDocument(
        document_id="doc_long_1",
        filename="disciplinary_code.pdf",
        file_type="pdf",
        blocks=[
            ExtractedBlock(text=long_text, block_type="paragraph", page_number=2),
        ],
    )

    chunks = test_chunker.chunk_document(doc)

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.token_count <= 100
        assert chunk.page_number == 2
        assert len(chunk.content.strip()) > 0

    # Verify deterministic sequence ordering
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.chunk_id == f"doc_long_1_p2_c{idx}"


def test_chunk_heading_preservation_and_context(test_chunker: StructureAwareChunker) -> None:
    """Verify section headings are preserved in section_title and contextualized in chunks."""
    doc = ExtractedDocument(
        document_id="doc_headings",
        filename="syllabus.docx",
        file_type="docx",
        blocks=[
            ExtractedBlock(text="Module 1: Natural Language Processing", block_type="heading", page_number=1),
            ExtractedBlock(text="This module covers tokenization, n-grams, and language modeling.", block_type="paragraph", page_number=1),
            ExtractedBlock(text="Module 2: Vector Embeddings", block_type="heading", page_number=1),
            ExtractedBlock(text="This module covers dense vector search and approximate nearest neighbors.", block_type="paragraph", page_number=1),
        ],
    )

    chunks = test_chunker.chunk_document(doc)

    assert len(chunks) >= 2
    assert chunks[0].section_title == "Module 1: Natural Language Processing"
    assert "[Module 1: Natural Language Processing]" in chunks[0].content

    assert chunks[1].section_title == "Module 2: Vector Embeddings"
    assert "[Module 2: Vector Embeddings]" in chunks[1].content


def test_chunk_empty_input_returns_empty_list(test_chunker: StructureAwareChunker) -> None:
    """Verify document with no blocks or pages returns an empty chunk list."""
    doc = ExtractedDocument(
        document_id="empty_doc",
        filename="empty.pdf",
        file_type="pdf",
        blocks=[],
        pages=[],
    )
    chunks = test_chunker.chunk_document(doc)
    assert chunks == []


def test_chunk_stable_identifiers_and_hash(test_chunker: StructureAwareChunker) -> None:
    """Verify stable chunk IDs and deterministic content hashing."""
    doc = ExtractedDocument(
        document_id="doc_stable",
        filename="regulations.pdf",
        file_type="pdf",
        blocks=[
            ExtractedBlock(text="Sample paragraph for deterministic testing.", block_type="paragraph", page_number=3),
        ],
    )

    chunks_run_1 = test_chunker.chunk_document(doc)
    chunks_run_2 = test_chunker.chunk_document(doc)

    assert chunks_run_1[0].chunk_id == chunks_run_2[0].chunk_id == "doc_stable_p3_c0"
    assert chunks_run_1[0].content_hash == chunks_run_2[0].content_hash
    assert len(chunks_run_1[0].content_hash) == 64  # SHA-256 length


def test_chunk_to_qdrant_payload(test_chunker: StructureAwareChunker) -> None:
    """Verify chunk converts into a dictionary compatible with Qdrant vector payload format."""
    doc = ExtractedDocument(
        document_id="doc_payload_test",
        filename="handbook.pdf",
        file_type="pdf",
        metadata={"institution": "Engineering College"},
        blocks=[
            ExtractedBlock(text="Hostel rules and curfew hours.", block_type="paragraph", page_number=4),
        ],
    )

    chunks = test_chunker.chunk_document(doc)
    payload = chunks[0].to_qdrant_payload(embedding_model="BAAI/bge-small-en-v1.5", document_version="2.0")

    assert payload["document_id"] == "doc_payload_test"
    assert payload["document_name"] == "handbook.pdf"
    assert payload["document_version"] == "2.0"
    assert payload["chunk_id"] == "doc_payload_test_p4_c0"
    assert payload["chunk_index"] == 0
    assert payload["page_number"] == 4
    assert payload["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert payload["content"] == "Hostel rules and curfew hours."
    assert payload["institution"] == "Engineering College"

