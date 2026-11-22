"""Entry point: command-line demo for HR Policy Assistant."""

from hr_assistant.logging_config import configure_logging
from hr_assistant.pipeline import ask, build_hr_assistant
from hr_assistant.tracing import check_langsmith_tracing


def main():
    configure_logging()
    check_langsmith_tracing()

    print("\nConnecting to the HR policy assistant...")
    agent, cache = build_hr_assistant()
    print("Assistant and Semantic Cache ready!\n")

    demo_questions = [
        "How many paid annual leave days do I get?",
        "What is the notice period during probation?",
        "Can I work from home every day?",
        "What happens to my leave during my notice period?",
        "How many weeks of maternity leave am I entitled to?",
    ]

    for question in demo_questions:
        print("=" * 60)
        print("QUESTION:", question)
        print("-" * 60)
        answer = ask(agent, cache, question)
        print("ANSWER:\n", answer)
        print("=" * 60)
        print()


if __name__ == "__main__":
    main()