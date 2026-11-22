"""Unit tests for the evaluation harness and LLM-as-a-judge setup."""

import unittest
from unittest.mock import MagicMock, patch

from hr_assistant.evaluation import (
    EVALUATION_DATASET,
    create_evaluators,
    get_judge_llm,
    make_target_function,
)


class TestEvaluationModule(unittest.TestCase):
    """Validate evaluation dataset, judge model wiring, and evaluator creation."""

    def test_evaluation_dataset_structure(self):
        """Verify evaluation dataset contains valid questions and reference answers."""
        self.assertGreaterEqual(len(EVALUATION_DATASET), 10)
        for item in EVALUATION_DATASET:
            self.assertIn("question", item)
            self.assertIn("answer", item)
            self.assertTrue(len(item["question"].strip()) > 10)
            self.assertTrue(len(item["answer"].strip()) > 10)

    def test_get_judge_llm_initialization(self):
        """Verify judge LLM initializes with Groq OpenAI-compatible settings."""
        judge = get_judge_llm()
        self.assertIsNotNone(judge)
        self.assertEqual(judge.temperature, 0.0)

    def test_evaluators_creation(self):
        """Verify openevals creates correctness and groundedness judge functions."""
        judge = get_judge_llm()
        evaluators = create_evaluators(judge)
        self.assertEqual(len(evaluators), 2)
        for evaluator in evaluators:
            self.assertTrue(callable(evaluator))

    def test_make_target_function(self):
        """Verify target function formats outputs and context correctly for evaluators."""
        mock_agent = MagicMock()
        mock_cache = MagicMock()
        mock_vector_store = MagicMock()

        # Mock retriever
        mock_doc = MagicMock()
        mock_doc.page_content = "Employees get 18 annual leave days."
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = [mock_doc]
        mock_vector_store.as_retriever.return_value = mock_retriever

        with patch("hr_assistant.evaluation.ask", return_value="Employees receive 18 days."):
            target_fn = make_target_function(mock_agent, mock_cache, mock_vector_store)
            output = target_fn({"question": "What is the annual leave entitlement?"})

            self.assertIn("outputs", output)
            self.assertIn("answer", output)
            self.assertIn("context", output)
            self.assertEqual(output["outputs"], "Employees receive 18 days.")
            self.assertIn("18 annual leave days", output["context"])


if __name__ == "__main__":
    unittest.main()
