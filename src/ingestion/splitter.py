"""06 · splitter — Chop documents into small, searchable, overlapping chunks.

Uses LangChain's RecursiveCharacterTextSplitter with standardized parameters
(config.CHUNK_SIZE and config.CHUNK_OVERLAP). Metadata (source, policy_category, local_path)
carries over onto every chunk automatically.
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core import config


def split_into_chunks(
    documents: List[Document],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Split documents into small overlapping chunks.

    Metadata from parent documents (e.g., source, policy_category, local_path)
    is preserved across all generated child chunks.

    Args:
        documents: List of LangChain Document instances to split.
        chunk_size: Target maximum chunk size in characters (defaults to config.CHUNK_SIZE).
        chunk_overlap: Number of overlapping characters between adjacent chunks
            (defaults to config.CHUNK_OVERLAP).

    Returns:
        List of split Document chunks ready for embedding.
    """
    resolved_chunk_size = chunk_size or config.CHUNK_SIZE
    resolved_chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=resolved_chunk_size,
        chunk_overlap=resolved_chunk_overlap,
    )
    return text_splitter.split_documents(documents)
