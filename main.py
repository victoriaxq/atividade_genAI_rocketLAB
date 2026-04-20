import asyncio
import os
import sys

from dotenv import load_dotenv

from agent import agent, AgentDeps
from database_manager import DatabaseManager

load_dotenv()

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          DataBot — Text-to-SQL Agent 🤖                  ║
║          Visagio Rocket Lab 2026                          ║
║  Type your question in Portuguese or English.            ║
║  Commands: 'exit' or 'quit' to stop, 'clear' to reset.  ║
╚══════════════════════════════════════════════════════════╝
"""


async def run_conversation() -> None:
    print(BANNER)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌  GEMINI_API_KEY not found. Add it to your .env file.")
        sys.exit(1)

    try:
        db = DatabaseManager()
    except FileNotFoundError as exc:
        print(f"❌  {exc}")
        sys.exit(1)

    deps = AgentDeps(db=db)
    message_history: list = []

    print("Connected to banco.db")
    tables = db.list_tables()
    print(f"📋  Tables found: {', '.join(tables)}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋  Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "sair"}:
            print("👋  Goodbye!")
            break

        if user_input.lower() == "clear":
            message_history = []
            print("🧹  Conversation history cleared.\n")
            continue

        print("\n🤔  Thinking...\n")

        try:
            result = await agent.run(
                user_input,
                deps=deps,
                message_history=message_history,
            )
            message_history = result.all_messages()

            resp = result.output
            print(f"DataBot: {resp.answer}")

            if resp.data_summary:
                print(f"\n📊  Summary:\n{resp.data_summary}")

            if resp.sql_used:
                print(f"\n🔍  SQL executed:\n{resp.sql_used}")

            if resp.row_count is not None:
                print(f"\n📦  Rows returned: {resp.row_count}")

        except Exception as exc:  # noqa: BLE001
            print(f"\n⚠️  An error occurred: {exc}")

        print()


def main() -> None:
    asyncio.run(run_conversation())


if __name__ == "__main__":
    main()
