"""18 · evaluation — Automated RAG answer quality evaluation using LLM-as-a-Judge and LangSmith.

Evaluates the secured HR Policy assistant against a golden Q&A dataset on two core dimensions:
1. Correctness: Does the generated answer factually match the reference ground truth?
2. Groundedness (Faithfulness): Is every claim in the answer supported by retrieved context?

Judge Model:
  Groq-hosted high-capacity open-weight model (e.g. llama-3.3-70b-versatile or openai/gpt-oss-120b)
  using OpenAI-compatible chat completions API.
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from langchain_openai import ChatOpenAI
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import CORRECTNESS_PROMPT, RAG_GROUNDEDNESS_PROMPT

from hr_assistant import config
from hr_assistant.pipeline import ask, build_hr_assistant
from hr_assistant.tracing import check_langsmith_tracing
from hr_assistant.vector_store import load_vector_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Golden Evaluation Dataset (Question Paper & Reference Answers)
# ---------------------------------------------------------------------------
EVALUATION_DATASET: List[Dict[str, str]] = [
    {
        "question": "What is the standard policy regarding annual leave entitlement?",
        "answer": "Full-time employees receive 18 days of paid annual leave per calendar year, accrued at 1.5 days per completed month of service.",
    },
    {
        "question": "Can I carry forward unused annual leave days to the next calendar year?",
        "answer": "Yes, up to a maximum of 10 unused annual leave days may be carried forward into the next calendar year. Any remaining balance beyond 10 days will lapse.",
    },
    {
        "question": "What is the required notice period during the probation period?",
        "answer": "The notice period during the probationary period is 15 calendar days for either the employee or the company.",
    },
    {
        "question": "What is the standard notice period for confirmed permanent employees?",
        "answer": "Confirmed employees must provide a notice period of 60 calendar days (2 months) upon resignation.",
    },
    {
        "question": "How many days per week am I allowed to work from home?",
        "answer": "Eligible employees in approved roles may work from home for up to 2 days per week, subject to manager approval.",
    },
    {
        "question": "What is the paid maternity leave duration?",
        "answer": "Female employees are entitled to 26 weeks of fully paid maternity leave for up to two surviving children.",
    },
    {
        "question": "How many days of paid paternity leave do new fathers receive?",
        "answer": "Male employees are entitled to 5 working days of paid paternity leave, to be taken within 6 months of the child's birth.",
    },
    {
        "question": "What is the policy for taking sick leave and when is a medical certificate needed?",
        "answer": "Employees receive 12 days of paid sick leave per year. A medical certificate from a registered practitioner is mandatory for absences of 2 or more consecutive days.",
    },
    {
        "question": "What internet reimbursement amount can remote employees claim monthly?",
        "answer": "Employees approved for remote or hybrid work can claim up to $50 per month for home internet expenses with a valid tax invoice or receipt.",
    },
    {
        "question": "What are the requirements for completing the employee exit clearance process?",
        "answer": "Employees must return all company property (laptop, access card, tokens) and obtain sign-off clearances from IT, Finance, and HR before final settlement.",
    },
]


def get_judge_llm() -> ChatOpenAI:
    """Initialize Groq-hosted OpenAI-compatible chat model for evaluation judging."""
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is required to initialize the evaluation judge LLM.")

    return ChatOpenAI(
        model=config.JUDGE_MODEL_NAME,
        openai_api_key=config.GROQ_API_KEY,
        openai_api_base=config.GROQ_BASE_URL,
        temperature=0.0,
    )


def ensure_evaluation_dataset(client: Client, dataset_name: str = "hr-policy-qa") -> Any:
    """Ensure evaluation dataset exists on LangSmith, uploading golden Q&A examples if absent."""
    if client.has_dataset(dataset_name=dataset_name):
        logger.info("Found existing LangSmith evaluation dataset: '%s'", dataset_name)
        return client.read_dataset(dataset_name=dataset_name)

    logger.info("Creating new LangSmith evaluation dataset: '%s'", dataset_name)
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Golden Q&A evaluation dataset for HR Policy Assistant quality scoring.",
    )

    client.create_examples(
        inputs=[{"question": item["question"]} for item in EVALUATION_DATASET],
        outputs=[{"answer": item["answer"]} for item in EVALUATION_DATASET],
        dataset_id=dataset.id,
    )
    logger.info("Uploaded %d evaluation examples to LangSmith dataset '%s'.", len(EVALUATION_DATASET), dataset_name)
    return dataset


def create_evaluators(judge_llm: ChatOpenAI) -> List[Callable]:
    """Create correctness and groundedness LLM-as-a-judge evaluators using openevals."""
    correctness_evaluator = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        judge=judge_llm,
        feedback_key="correctness",
    )

    groundedness_evaluator = create_llm_as_judge(
        prompt=RAG_GROUNDEDNESS_PROMPT,
        judge=judge_llm,
        feedback_key="groundedness",
    )

    return [correctness_evaluator, groundedness_evaluator]


def make_target_function(agent: Any, cache: Any, vector_store: Any) -> Callable:
    """Construct evaluation target that invokes secured ask() and extracts retrieved context."""
    retriever = vector_store.as_retriever(search_kwargs={"k": config.TOP_K_RESULTS})

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs.get("question") or inputs.get("input", "")
        eval_thread_id = f"eval-{uuid.uuid4().hex[:8]}"

        # Execute secured pipeline (guardrails + cache + reasoning)
        answer = ask(agent, cache, question, thread_id=eval_thread_id)

        # Retrieve relevant policy chunks for groundedness validation
        candidates = retriever.invoke(question)
        context_text = "\n\n".join(doc.page_content for doc in candidates)

        return {
            "outputs": answer,
            "answer": answer,
            "context": context_text,
        }

    return target


def run_evaluation(
    dataset_name: str = "hr-policy-qa",
    limit: Optional[int] = None,
) -> Any:
    """Execute end-to-end evaluation experiment on LangSmith."""
    check_langsmith_tracing()
    config.check_api_keys()

    client = Client()
    dataset = ensure_evaluation_dataset(client, dataset_name=dataset_name)

    logger.info("Initializing Judge LLM (%s via Groq)...", config.JUDGE_MODEL_NAME)
    judge = get_judge_llm()
    evaluators = create_evaluators(judge)

    logger.info("Initializing production guarded HR assistant for evaluation...")
    agent, cache = build_hr_assistant()
    vector_store = load_vector_store(config.QDRANT_COLLECTION_NAME)

    target_fn = make_target_function(agent, cache, vector_store)

    logger.info("Running evaluation against dataset '%s'...", dataset_name)
    experiment_results = client.evaluate(
        target_fn,
        data=dataset.name,
        evaluators=evaluators,
        experiment_prefix="hr-policy-quality",
        description="Groundedness and Correctness evaluation for HR Policy RAG Assistant",
        max_concurrency=2,
    )

    logger.info("Evaluation experiment finished successfully.")
    return experiment_results
