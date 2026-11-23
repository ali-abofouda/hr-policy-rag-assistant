"""Unit tests for text splitter, embeddings initialization, and vector store modules."""

import unittest
from langchain_core.documents import Document

from src.ingestion.splitter import split_into_chunks
from src.retrieval.vector_store import _stable_chunk_id


class TestSplitterAndVectorStore(unittest.TestCase):
    def test_split_into_chunks_preserves_metadata(self):
        docs = [
            Document(
                page_content="Policy Category: Leave\n\n" + "This is a detailed paragraph about leave policy. " * 30,
                metadata={"source": "leave_policy.txt", "policy_category": "Leave"},
            )
        ]
        chunks = split_into_chunks(docs, chunk_size=200, chunk_overlap=40)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertEqual(chunk.metadata["source"], "leave_policy.txt")
            self.assertEqual(chunk.metadata["policy_category"], "Leave")
            self.assertLessEqual(len(chunk.page_content), 300)

    def test_stable_chunk_id_determinism(self):
        chunk = Document(
            page_content="Remote work is permitted two days per week.",
            metadata={"source": "wfh_policy.txt"},
        )
        id1 = _stable_chunk_id(chunk)
        id2 = _stable_chunk_id(chunk)
        self.assertEqual(id1, id2)
        self.assertEqual(len(id1), 36)

        diff_chunk = Document(
            page_content="Remote work is permitted three days per week.",
            metadata={"source": "wfh_policy.txt"},
        )
        id3 = _stable_chunk_id(diff_chunk)
        self.assertNotEqual(id1, id3)


if __name__ == "__main__":
    unittest.main()
