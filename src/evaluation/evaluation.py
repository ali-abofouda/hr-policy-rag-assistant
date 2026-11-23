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
# Golden Evaluation Dataset (Question Paper & Reference Answers aligned with policies)
# ---------------------------------------------------------------------------
EVALUATION_DATASET: List[Dict[str, str]] = [
    {
        "question": "What is the standard policy regarding annual leave entitlement?",
        "answer": "Every full-time employee is entitled to 18 days of paid annual leave per calendar year, accrued at a rate of 1.5 days per completed month of service.",
    },
    {
        "question": "Can I carry forward unused annual leave days to the next calendar year?",
        "answer": "Yes, unused annual leave may be carried forward to the next calendar year up to a maximum of 10 days; any remaining balance beyond that is forfeited on December 31st.",
    },
    {
        "question": "What is the required notice period during the probation period?",
        "answer": "During the probation period, either the employee or the company may terminate the employment relationship with 15 days' written notice, or payment in lieu of notice.",
    },
    {
        "question": "What is the standard notice period for confirmed permanent employees?",
        "answer": "The standard notice period for confirmed permanent employees is 60 days (2 calendar months) for both resignation by the employee and termination initiated by the company, except in cases of termination for cause.",
    },
    {
        "question": "How many days per week am I allowed to work from home?",
        "answer": "Eligible employees in approved roles may work from home for up to 2 days per week, subject to manager approval.",
    },
    {
        "question": "What is the paid maternity leave duration?",
        "answer": "Employees who give birth are entitled to 26 weeks of paid maternity leave, which may begin up to 8 weeks before the expected delivery date.",
    },
    {
        "question": "How many days of paid paternity leave do new fathers receive?",
        "answer": "Employees whose partner gives birth are entitled to 2 weeks of paid paternity leave, to be taken within 3 months of the child's birth (may be split into two blocks with manager approval).",
    },
    {
        "question": "What is the policy for taking sick leave and when is a medical certificate needed?",
        "answer": "Employees are entitled to 10 days of paid sick leave per calendar year (does not carry forward). For sick leave of 3 or more consecutive days, a medical certificate must be submitted to HR within 5 working days of returning to work.",
    },
    {
        "question": "What internet reimbursement amount can remote employees claim monthly?",
        "answer": "Employees with a standing work-from-home arrangement may claim up to 1,500 (local currency) per month toward internet costs, provided these are used substantially for work purposes.",
    },
    {
        "question": "What are the requirements for completing the employee exit clearance process?",
        "answer": "The clearance process includes resignation submission, handover of ongoing projects and documentation to a colleague/successor at least 10 days before the last day, return of all company-issued assets (laptops, access cards, mobile devices, physical documents), an optional exit interview, IT access revocation at 11:59 PM on the last day, and final settlement within 45 days.",
    },
]

# Tuned correctness prompt to avoid penalizing additional accurate context from company policies
TUNED_CORRECTNESS_PROMPT = """You are an expert data labeler evaluating model outputs for correctness. Your task is to assign a score based on the following rubric:

<Rubric>
  A correct answer:
  - Provides accurate and complete information covering the reference answer
  - Contains no factual errors
  - Addresses all core parts of the question
  - Is logically consistent
  - Uses precise terminology

  When scoring:
  - DO penalize actual factual errors or direct contradictions with the reference output
  - DO penalize missing critical information that was explicitly asked in the question
  - DO NOT penalize additional accurate details or helpful context from the source document that expand on the answer, provided the core reference answer is satisfied.
</Rubric>

<Instructions>
  - Carefully read the input and output
  - Check for factual accuracy against the reference output
  - Focus on correctness of information rather than brevity or style
</Instructions>

<input>
{inputs}
</input>

<output>
{outputs}
</output>

Use the reference outputs below to help you evaluate the correctness of the response:

<reference_outputs>
{reference_outputs}
</reference_outputs>
"""


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


def ensure_evaluation_dataset(client: Client, dataset_name: str = "hr-policy-qa", force_sync: bool = True) -> Any:
    """Ensure evaluation dataset exists on LangSmith, uploading or synchronizing golden Q&A examples."""
    if client.has_dataset(dataset_name=dataset_name):
        logger.info("Found existing LangSmith evaluation dataset: '%s'", dataset_name)
        dataset = client.read_dataset(dataset_name=dataset_name)
        if force_sync:
            existing_examples = list(client.list_examples(dataset_id=dataset.id))
            for eg in existing_examples:
                try:
                    client.delete_example(eg.id)
                except Exception:
                    pass
            client.create_examples(
                inputs=[{"question": item["question"]} for item in EVALUATION_DATASET],
                outputs=[{"answer": item["answer"]} for item in EVALUATION_DATASET],
                dataset_id=dataset.id,
            )
            logger.info("Synchronized %d golden examples with policy documents.", len(EVALUATION_DATASET))
        return dataset

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
    raw_correctness = create_llm_as_judge(
        prompt=TUNED_CORRECTNESS_PROMPT,
        judge=judge_llm,
        feedback_key="correctness",
    )

    raw_groundedness = create_llm_as_judge(
        prompt=RAG_GROUNDEDNESS_PROMPT,
        judge=judge_llm,
        feedback_key="groundedness",
    )

    def correctness_evaluator(run: Any, example: Any) -> Dict[str, Any]:
        """LangSmith run evaluator for answer correctness against ground truth."""
        inputs = example.inputs if example else (run.inputs or {})
        ref_outputs = example.outputs if example else {}
        outputs = run.outputs or {}
        answer = outputs.get("answer") or outputs.get("outputs", "")
        res = raw_correctness(
            inputs=inputs,
            outputs=answer,
            reference_outputs=ref_outputs,
        )
        if isinstance(res, dict):
            return res
        return {
            "key": "correctness",
            "score": getattr(res, "score", None),
            "comment": getattr(res, "comment", ""),
        }

    def groundedness_evaluator(run: Any, example: Any) -> Dict[str, Any]:
        """LangSmith run evaluator for RAG groundedness against retrieved context."""
        outputs = run.outputs or {}
        context = outputs.get("context", "")
        answer = outputs.get("answer") or outputs.get("outputs", "")
        res = raw_groundedness(
            outputs=answer,
            context=context,
        )
        if isinstance(res, dict):
            return res
        return {
            "key": "groundedness",
            "score": getattr(res, "score", None),
            "comment": getattr(res, "comment", ""),
        }

    return [correctness_evaluator, groundedness_evaluator]


def make_target_function(agent: Any, cache: Any, vector_store: Any) -> Callable:
    """Construct evaluation target that invokes secured ask() and extracts retrieved context."""
    from hr_assistant.semantic_cache import SemanticCache

    retriever = vector_store.as_retriever(search_kwargs={"k": config.TOP_K_RESULTS})

    def target(inputs: Dict[str, Any]) -> Dict[str, Any]:
        question = inputs.get("question") or inputs.get("input", "")
        eval_thread_id = f"eval-{uuid.uuid4().hex[:8]}"

        # Isolated cache with high threshold (0.95) to prevent cross-question collision
        eval_cache = SemanticCache(threshold=0.95)

        # Execute secured pipeline (guardrails + cache + reasoning)
        answer = ask(agent, eval_cache, question, thread_id=eval_thread_id)

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
        max_concurrency=1,
    )

    logger.info("Evaluation experiment finished successfully.")
    return experiment_results
