"""backend/eval/run_eval.py — Automated Evaluation Runner with External Prompts."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langsmith import Client

from backend.app.core.config import settings
from backend.eval.dataset import get_golden_dataset
from src.evaluation.evaluation import evaluate_rag_pipeline

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt_template(filename: str) -> str:
    """Read prompt markdown template from disk."""
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt template '{filename}' not found at {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def run_evaluation_suite(experiment_prefix: Optional[str] = None):
    """Execute complete RAG triad evaluation."""
    logger.info("Executing evaluation suite against golden dataset...")
    return evaluate_rag_pipeline(experiment_prefix=experiment_prefix)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_evaluation_suite()
