"""evaluate.py - CLI entrypoint for running LangSmith evaluation experiments.

Executes quality evaluation (Correctness & Groundedness) against the golden dataset
using Groq-powered LLM-as-a-Judge and uploads experiment results to LangSmith.

Run with:
    python evaluate.py
"""

import sys
from hr_assistant.logging_config import configure_logging
from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant.evaluation import run_evaluation


def main():
    configure_logging()
    check_langsmith_tracing()

    print("=" * 80)
    print("HR Policy RAG Assistant - LangSmith Evaluation Harness")
    print("Metrics: Correctness (Accuracy) & Groundedness (Faithfulness)")
    print("=" * 80)

    try:
        results = run_evaluation()
        print("\nEvaluation successfully launched on LangSmith.")
        print(f"Results Summary: {results}")
    except Exception as exc:
        print(f"\nEvaluation failed with error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
