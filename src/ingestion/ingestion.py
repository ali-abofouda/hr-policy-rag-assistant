"""09 · ingestion — Orchestration pipeline for document loading, chunking, and vector indexing.

This module coordinates the complete data ingestion lifecycle:
    Local raw/processed data -> Chunking (splitter) -> Embedding & Indexing (Qdrant)

SOLID Principles Applied:
- Single Responsibility Principle (SRP): Decoupled loaders, chunkers, and pipeline orchestrator.
- Open/Closed Principle (OCP): Extensible via DocumentLoaderStrategy protocol.
- Liskov Substitution Principle (LSP): Interchangeable loader strategies.
- Interface Segregation Principle (ISP): Lean and focused Protocol interfaces.
- Dependency Inversion Principle (DIP): IngestionPipeline depends on abstractions.

Zero-Cloud / Cost-Free Architecture:
    Runs 100% on the local filesystem. No Google Cloud Storage (GCS) or GCP billing required.
"""

import logging
import os
from typing import Any, Callable, List, Optional, Protocol, runtime_checkable

from langchain_core.documents import Document

from src.core import config
from src.ingestion.document_loader import (
    load_documents_from_local,
    load_processed_documents_from_local,
)
from src.ingestion.processor import process_local_raw_to_json
from src.ingestion.splitter import split_into_chunks
from src.retrieval.vector_store import build_vector_store, collection_exists

logger = logging.getLogger(__name__)


@runtime_checkable
class DocumentLoaderStrategy(Protocol):
    """Protocol defining the contract for loading documents into LangChain Document instances."""

    def load(self) -> List[Document]:
        """Load and return a list of LangChain Document objects."""
        ...


class LocalHRLoaderStrategy:
    """Strategy for loading clean HR policy text files from local storage."""

    def __init__(self, policies_dir: Optional[str] = None) -> None:
        self.policies_dir = policies_dir or os.path.join("data", "policies")

    def load(self) -> List[Document]:
        logger.info("Loading clean HR policy documents from '%s'...", self.policies_dir) 
        return load_documents_from_local(policies_dir=self.policies_dir)


class LocalNoisyCorpusLoaderStrategy:
    """Strategy for loading multi-format noisy/benchmark records from local disk."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        processed_dir: Optional[str] = None,
        subdirs: tuple = ("hr-policies", "other-data"),
    ) -> None:
        self.data_dir = data_dir or "data"
        self.processed_dir = processed_dir or os.path.join("data", "processed")
        self.subdirs = subdirs

    def ensure_processed(self, force_reprocess: bool = False) -> None:
        """Ensure that raw multi-format files are processed into JSON records. """ 
        has_processed = False
        for sub in self.subdirs:
            target_folder = os.path.join(self.processed_dir, sub)
            if os.path.exists(target_folder) and os.listdir(target_folder):
                has_processed = True
                break

        if force_reprocess or not has_processed:
            logger.info("Parsing raw multi-format files into JSON in '%s'...", self.processed_dir)
            process_local_raw_to_json(data_dir=self.data_dir, output_dir=self.processed_dir)

    def load(self, force_reprocess: bool = False) -> List[Document]:
        """Load processed JSON records from local disk, ensuring processing if needed."""
        self.ensure_processed(force_reprocess=force_reprocess)
        logger.info("Loading processed records from '%s'...", self.processed_dir)
        return load_processed_documents_from_local(
            subdirs=self.subdirs,
            processed_dir=self.processed_dir,
        )


class IngestionPipeline:
    """Orchestrates document loading, chunking, and vector store indexing."""

    def __init__(
        self,
        chunker: Callable[[List[Document]], List[Document]] = split_into_chunks,
        vector_store_builder: Callable[..., Any] = build_vector_store,
        collection_checker: Callable[[str], bool] = collection_exists,
    ) -> None:
        self.chunker = chunker
        self.vector_store_builder = vector_store_builder
        self.collection_checker = collection_checker

    def ingest(
        self,
        loader: DocumentLoaderStrategy,
        collection_name: str,
        force: bool = False,
        hybrid: bool = True,
    ) -> int:
        """Ingest documents into a Qdrant collection, with optional force rebuild. """
        if self.collection_checker(collection_name) and not force:
            logger.info(
                "Collection '%s' already exists with indexed points. Skipping ingestion (use --force to rebuild).",
                collection_name,
            )
            return 0

        logger.info("Starting ingestion for collection '%s' (force=%s, hybrid=%s)...", collection_name, force, hybrid)
        documents = loader.load()
        if not documents:
            logger.warning("No documents retrieved for '%s'. Ingestion aborted.", collection_name)
            return 0

        chunks = self.chunker(documents)
        logger.info("Created %d chunks from %d source document(s).", len(chunks), len(documents))

        self.vector_store_builder(chunks=chunks, hybrid=hybrid, collection_name=collection_name)
        logger.info("Successfully ingested %d chunks into '%s'.", len(chunks), collection_name)
        return len(chunks)


def ingest_hr_policies(force: bool = False) -> int:
    """Ingest clean HR policy documents into the primary Qdrant collection."""
    pipeline = IngestionPipeline()
    loader = LocalHRLoaderStrategy(policies_dir=os.path.join("data", "policies"))
    return pipeline.ingest(
        loader=loader,
        collection_name=config.QDRANT_COLLECTION_NAME,
        force=force,
        hybrid=True,
    )


def ingest_noisy_corpus(force: bool = False) -> int:
    """Ingest mixed/noisy documents into the benchmark collection for stress testing."""
    pipeline = IngestionPipeline()
    loader = LocalNoisyCorpusLoaderStrategy(
        data_dir="data",
        processed_dir=os.path.join("data", "processed"),
    )
    if force:
        loader.ensure_processed(force_reprocess=True)

    return pipeline.ingest(
        loader=loader,
        collection_name=config.QDRANT_NOISY_COLLECTION_NAME,
        force=force,
        hybrid=True,
    )


def run_ingestion(force: bool = False, hr: bool = True, noisy: bool = False) -> None:
    """Top-level coordinator function called by CLI scripts and test harnesses."""
    config.check_api_keys()

    if hr:
        logger.info("--- Phase 1: Ingesting Clean HR Policies ---")
        ingest_hr_policies(force=force)

    if noisy:
        logger.info("--- Phase 2: Ingesting Noisy / Benchmark Corpus ---")
        ingest_noisy_corpus(force=force)

    logger.info("Local Ingestion Pipeline finished successfully.")