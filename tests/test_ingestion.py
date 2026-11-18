"""Unit tests for the SOLID-compliant local ingestion pipeline."""

import unittest
from unittest.mock import MagicMock
from langchain_core.documents import Document

from hr_assistant.ingestion import (
    DocumentLoaderStrategy,
    LocalHRLoaderStrategy,
    LocalNoisyCorpusLoaderStrategy,
    IngestionPipeline,
)


class DummyLoader:
    """Mock loader implementing DocumentLoaderStrategy protocol."""

    def load(self):
        return [
            Document(page_content="Test document content.", metadata={"source": "test.txt"})
        ]


class TestIngestionSOLID(unittest.TestCase):
    """Verify SOLID principles and pipeline orchestration."""

    def test_loader_protocol_compliance(self):
        """Verify that loaders adhere to the DocumentLoaderStrategy protocol (LSP & ISP)."""
        dummy = DummyLoader()
        self.assertIsInstance(dummy, DocumentLoaderStrategy)

        hr_loader = LocalHRLoaderStrategy()
        self.assertIsInstance(hr_loader, DocumentLoaderStrategy)

        noisy_loader = LocalNoisyCorpusLoaderStrategy()
        self.assertIsInstance(noisy_loader, DocumentLoaderStrategy)

    def test_pipeline_skips_when_collection_exists_and_not_force(self):
        """Verify idempotency: existing collection is skipped when force=False."""
        mock_chunker = MagicMock()
        mock_builder = MagicMock()
        mock_checker = MagicMock(return_value=True)  # Collection exists

        pipeline = IngestionPipeline(
            chunker=mock_chunker,
            vector_store_builder=mock_builder,
            collection_checker=mock_checker,
        )

        dummy_loader = DummyLoader()
        result = pipeline.ingest(
            loader=dummy_loader,
            collection_name="test_collection",
            force=False,
        )

        self.assertEqual(result, 0)
        mock_chunker.assert_not_called()
        mock_builder.assert_not_called()

    def test_pipeline_executes_when_force_is_true(self):
        """Verify pipeline executes when force=True even if collection exists."""
        dummy_chunk = Document(page_content="chunk", metadata={"source": "test.txt"})
        mock_chunker = MagicMock(return_value=[dummy_chunk])
        mock_builder = MagicMock()
        mock_checker = MagicMock(return_value=True)

        pipeline = IngestionPipeline(
            chunker=mock_chunker,
            vector_store_builder=mock_builder,
            collection_checker=mock_checker,
        )

        dummy_loader = DummyLoader()
        result = pipeline.ingest(
            loader=dummy_loader,
            collection_name="test_collection",
            force=True,
        )

        self.assertEqual(result, 1)
        mock_chunker.assert_called_once()
        mock_builder.assert_called_once()


if __name__ == "__main__":
    unittest.main()
