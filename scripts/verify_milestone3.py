"""Verification script for Milestone 3: Document Extraction and Chunking."""

import asyncio
import io
import os
import sys

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

import docx
import pymupdf

from app.core.config import get_settings
from app.ingestion.chunker import StructureAwareChunker
from app.ingestion.extractors.docx import DOCXExtractor
from app.ingestion.extractors.ocr import TesseractOCRExtractor
from app.ingestion.extractors.pdf import PDFExtractor
from app.ingestion.service import DocumentIngestionService


def generate_sample_pdf() -> bytes:
    doc = pymupdf.open()
    # Page 1
    p1 = doc.new_page()
    p1.insert_text((50, 72), "1. Academic Policies and Attendance Regulations.\nStudents must attend at least 75% of classes to be eligible for final exams.")
    # Page 2
    p2 = doc.new_page()
    p2.insert_text((50, 72), "2. Examination Grading System and CGPA Calculation.\nA letter grade of A represents 9 points, and A+ represents 10 points.")
    data = doc.tobytes()
    doc.close()
    return data


def generate_sample_docx() -> bytes:
    doc = docx.Document()
    doc.add_heading("Admission Guidelines 2025", level=1)
    doc.add_paragraph("Applicants must submit transcripts, proof of identity, and entrance examination scores.")
    doc.add_heading("Fee Structure", level=2)
    doc.add_paragraph("Tuition fee is payable at the start of each semester.")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Fee Component"
    table.cell(0, 1).text = "Amount (USD)"
    table.cell(1, 0).text = "Tuition"
    table.cell(1, 1).text = "2500"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


async def verify_milestone3() -> int:
    print("=" * 70)
    print("Verifying Milestone 3: Document Extraction & Structure-Aware Chunking")
    print("=" * 70)

    settings = get_settings()
    print(f"\n1. Ingestion Settings:")
    print(f"   [OK] Target Chunk Size:      {settings.CHUNK_SIZE} tokens")
    print(f"   [OK] Chunk Overlap:         {settings.CHUNK_OVERLAP} tokens")
    print(f"   [OK] Tokenizer Encoding:    {settings.TOKENIZER_ENCODING}")
    print(f"   [OK] Selective OCR Enabled: {settings.OCR_ENABLED}")
    print(f"   [OK] OCR Min Page Chars:    {settings.OCR_MIN_PAGE_CHARS} chars")
    print(f"   [OK] OCR Rendering DPI:     {settings.OCR_DPI} DPI")
    print(f"   [OK] Tesseract Command:     {settings.TESSERACT_CMD}")

    # Check OCR Availability
    ocr = TesseractOCRExtractor(settings=settings)
    ocr_available = ocr.is_available()
    print(f"   [INFO] Tesseract Installed Locally: {ocr_available}")
    if not ocr_available:
        print("   [NOTE] Tesseract not found in system PATH. Digital extraction works normally;")
        print("          for scanned documents, install Tesseract OCR binary.")

    service = DocumentIngestionService(settings=settings)

    # 2. Test PDF Extraction & Chunking
    print(f"\n2. Testing PDF Extraction & Chunking:")
    pdf_bytes = generate_sample_pdf()
    pdf_doc, pdf_chunks = await service.process_document(pdf_bytes, filename="regulations_sample.pdf")
    print(f"   [OK] PDF extracted {pdf_doc.total_pages} page(s), {pdf_doc.total_chars} total characters")
    print(f"   [OK] PDF produced {len(pdf_chunks)} chunk(s)")
    for c in pdf_chunks:
        print(f"        -> Chunk {c.chunk_id}: {c.token_count} tokens, Page {c.page_number}, Section: '{c.section_title}'")
    assert len(pdf_chunks) >= 2, "PDF should produce chunks for the 2 distinct pages/sections"

    # 3. Test DOCX Extraction & Chunking
    print(f"\n3. Testing DOCX Extraction & Chunking:")
    docx_bytes = generate_sample_docx()
    docx_doc, docx_chunks = await service.process_document(docx_bytes, filename="admissions_sample.docx")
    print(f"   [OK] DOCX extracted {len(docx_doc.blocks)} block(s), {len(docx_doc.sections)} section(s)")
    print(f"   [OK] DOCX produced {len(docx_chunks)} chunk(s)")
    for c in docx_chunks:
        print(f"        -> Chunk {c.chunk_id}: {c.token_count} tokens, Section: '{c.section_title}'")
        # Verify table markdown conversion is present
        if "Tuition" in c.content:
            print("        -> Table markdown snippet successfully preserved in chunk content:")
            for line in c.content.splitlines():
                if "|" in line:
                    print(f"           {line}")
    assert len(docx_chunks) >= 2, "DOCX should produce separate chunks for separate sections"

    # 4. Verify Qdrant Payload Compatibility
    print(f"\n4. Verifying Qdrant Payload Compatibility:")
    sample_payload = pdf_chunks[0].to_qdrant_payload(
        embedding_model=settings.EMBEDDING_MODEL,
        document_version="1.0",
    )
    assert "document_id" in sample_payload
    assert "document_name" in sample_payload
    assert "chunk_id" in sample_payload
    assert "content" in sample_payload
    assert "page_number" in sample_payload
    assert "embedding_model" in sample_payload
    print(f"   [OK] Payload keys verified: {list(sample_payload.keys())[:8]}...")

    print("\n" + "=" * 70)
    print("Milestone 3 Extraction and Chunking: ALL CHECKS PASSED")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(verify_milestone3()))

