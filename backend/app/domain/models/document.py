"""backend/app/domain/models/document.py — Document and Chunk Entities."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentChunk:
    """A semantic chunk of a policy document with metadata and embeddings."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: Optional[str] = None
    dense_vector: Optional[List[float]] = None
    sparse_indices: Optional[List[int]] = None
    sparse_values: Optional[List[float]] = None


@dataclass
class PolicyDocument:
    """An ingested policy document before chunking."""
    title: str
    source: str
    raw_text: str
    department: str = "HR"
    metadata: Dict[str, Any] = field(default_factory=dict)
