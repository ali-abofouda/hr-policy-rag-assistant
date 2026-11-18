"""Pipeline module to wire components into an agent and provide the ask() interface."""

import logging
from typing import Any, Optional

from langgraph.checkpoint.memory import InMemorySaver

from hr_assistant import config
from hr_assistant.agent import create_hr_agent
from hr_assistant.llm import get_llm
from hr_assistant.tools import create_search_tool
from hr_assistant.vector_store import collection_exists, load_vector_store

logger = logging.getLogger(__name__)


# Bootstraps the vector-store collection by running ingestion when it is missing.

def _bootstrap_collection(collection_name: str, ingest_fn) -> None:
    """First-run convenience: if the Qdrant collection isn't there yet,
    run ingestion once locally. After that this is a no-op."""
    if collection_exists(collection_name):
        return

    logger.info("Collection '%s' not found — running first-time local ingestion.", collection_name)
    ingest_fn()


# Builds and configures the HR policy assistant with its tools, model, and persistence.
def build_hr_assistant(checkpointer: Optional[Any] = None):
    """Connect to the hr_policies collection and build the agent.

    Returns the compiled agent ready to be invoked via ask().
    """
    from hr_assistant.ingestion import ingest_hr_policies

    # 1. Validate the required API keys.
    config.check_api_keys()

    # 2. Ensure the collection exists locally, creating it immediately if needed.
    _bootstrap_collection(config.QDRANT_COLLECTION_NAME, ingest_hr_policies)

    # 3. Set up in-memory session persistence.
    if checkpointer is None:
        checkpointer = InMemorySaver()
    elif checkpointer is False:
        checkpointer = None

    # 4. Load the vector store and connect it to the search tool and LLM.
    vector_store = load_vector_store(config.QDRANT_COLLECTION_NAME)
    search_tool = create_search_tool(vector_store)

    return create_hr_agent(
        llm=get_llm(),
        tools=[search_tool],
        checkpointer=checkpointer,
    )


# Sends a question to the assistant and extracts the final response as text.
def ask(agent, question: str, thread_id: str = "default-session") -> str:
    """Run one turn through the agent and return the answer text.

    Args:
        agent: The compiled LangGraph agent.
        question: The user's query.
        thread_id: Session identifier for conversational memory.

    Returns:
        The text answer string.
    """
    response = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    last_message = response["messages"][-1]

    # Extract the text safely across model versions.
    if hasattr(last_message, "text") and last_message.text:
        return last_message.text
    elif isinstance(last_message.content, str):
        return last_message.content
    elif isinstance(last_message.content, list):
        text_parts = [
            part["text"] for part in last_message.content if isinstance(part, dict) and "text" in part
        ]
        return "\n".join(text_parts) if text_parts else str(last_message.content)

    return str(last_message.content)