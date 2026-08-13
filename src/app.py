"""Interactive CLI for the Retail SQL Data Analyst Agent."""

from src.graph import build_graph

EXIT_COMMANDS = {"exit", "quit"}


def main():
    app = build_graph()
    history: list[dict] = []

    print("Retail SQL Data Analyst Agent")
    print("Ask a business question about the retail data. Type 'exit' to quit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not question:
            continue
        if question.lower() in EXIT_COMMANDS:
            print("Goodbye.")
            break

        result = app.invoke({"question": question, "history": history})
        history = result["history"]

        print(f"\nSQL: {result.get('sql', '')}")
        if result.get("error"):
            print(f"Safety/Error: {result['error']}")
        print(f"Answer: {result['answer']}\n")


if __name__ == "__main__":
    main()
