"""Ask your local bookmarks a question through the LangGraph agent, showing each step (dev only).

It streams the graph's updates: every time a node finishes, LangGraph hands over what it added to
the state, so you see agent → tools → agent → … as it happens. This calls the real models (free
tier), so it's a tool for us, never run by the tests.

    cd backend
    uv run python -m scripts.ask "what have I saved about postgres?"
    uv run python -m scripts.ask --email you@example.com "react hooks"
    uv run python -m scripts.ask --diagram     # print the graph as a Mermaid diagram
"""

import argparse
import asyncio

from langgraph.errors import GraphRecursionError

from app.ai.agent.graph import STOPPED, build_graph, run_config
from scripts.explore_search import pick_user

PREVIEW = 300  # characters of each tool result to print


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("question", nargs="?")
    parser.add_argument("--email", help="whose bookmarks (default: the user with the most)")
    parser.add_argument("--diagram", action="store_true", help="print the graph and stop")
    args = parser.parse_args()

    graph = build_graph()
    if args.diagram or not args.question:
        print(graph.get_graph().draw_mermaid())
        return

    user = await pick_user(args.email)
    print(f"Asking {user.email}'s bookmarks\n")
    updates = graph.astream(
        {"messages": [("user", args.question)]}, run_config(user.id), stream_mode="updates"
    )
    try:
        async for update in updates:
            for node, change in update.items():
                for message in change["messages"]:
                    if node == "tools":
                        print(f"  tools  ← {message.content[:PREVIEW]}…")
                    elif message.tool_calls:
                        for call in message.tool_calls:
                            print(f"  agent  → {call['name']}({call['args']})")
                    else:
                        print(f"  agent  answers:\n\n{message.text}")
    except GraphRecursionError:
        print(f"\n{STOPPED}")


if __name__ == "__main__":
    asyncio.run(main())
