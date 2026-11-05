"""Data models for candidate retrieval results and context citations."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RetrievalCandidate(BaseModel):
    """Represents a retrieved document chunk candidate from dense or keyword search."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document UUID")
    document_name: str = Field(description="Original document filename")
    document_version: int = Field(default=1, description="Document version number")
    page_number: Optional[int] = Field(default=None, description="Page number where chunk appears")
    section: Optional[str] = Field(default=None, description="Section heading or title")
    content: str = Field(description="Text content of the chunk")
    score: float = Field(default=0.0, description="Raw search score (similarity or ts_rank)")
    rank: int = Field(default=0, description="1-based rank in its individual retrieval system")
    retrieval_source: str = Field(default="dense", description="'dense', 'keyword', or 'fused'")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional payload metadata")


class SourceCitation(BaseModel):
    """Source citation displayed on frontend citation cards."""

    citation_id: str = Field(description="Numeric or alphanumeric citation marker e.g. '1', '2'")
    document_id: str = Field(description="Document UUID")
    document_name: str = Field(description="Document filename")
    document_version: int = Field(default=1, description="Document version number")
    page_number: Optional[int] = Field(default=None, description="Page number reference")
    section: Optional[str] = Field(default=None, description="Section heading reference")
    chunk_id: str = Field(description="Originating chunk identifier")
    snippet: str = Field(description="Representative text excerpt from chunk")

