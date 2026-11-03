"""The agent loop written by hand, for learning. The app will use the LangGraph version (graph.py).

An "agent" is a model in a loop with tools:
1. Send the conversation so far, with the tools' descriptions, to the model.
2. The model answers with text (it's done), or with tool calls: "run search_bookmarks with
   query='postgres'". It can't run anything itself; it only asks.
3. We run each tool and add its result to the conversation as a ToolMessage, linked to the call
   by the call's id.
4. Back to 1: the model now sees the results and decides again: answer, or look further.

The model remembers nothing between calls. Each call sends the whole conversation again, so that
list of messages is the agent's entire "state", which is why LangGraph is built around it.

Try it on your own bookmarks (this calls the real models and prints each step):
    uv run python -m app.ai.agent.manual_loop "what have I saved about postgres?"
"""

import argparse
import asyncio
import sys
from collections.abc import Callable

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import llm
from app.ai.agent.tools import TOOLS
from app.ai.chains import load_prompt
from app.db import SessionLocal
from app.models import User

MAX_STEPS = 6  # model calls; without a limit, a confused model could loop forever


async def ask(
    question: str,
    user_id: int,
    *,
    sessions: async_sessionmaker[AsyncSession] = SessionLocal,
    show: Callable[[str], None] = print,
) -> str:
    model = llm.get_tool_model(TOOLS)
    tools = {t.name: t for t in TOOLS}
    # Our code decides whose bookmarks the tools see; the model never does (see tools.py).
    config = {"configurable": {"user_id": user_id, "sessions": sessions}}
    messages = [SystemMessage(load_prompt("agent")), HumanMessage(question)]

    for _ in range(MAX_STEPS):
        reply = await model.ainvoke(messages)  # 1. the model decides
        messages.append(reply)
        if not reply.tool_calls:  # 2. plain text: that's the answer
            return reply.text
        for call in reply.tool_calls:  # 3. run what it asked for
            show(f"→ {call['name']}({call['args']})")
            tool = tools.get(call["name"])
            result = (
                await tool.ainvoke(call["args"], config)
                if tool
                else f"Error: there's no tool called {call['name']}."
            )
            show(f"← {result[:300]}{'…' if len(result) > 300 else ''}")
            messages.append(ToolMessage(result, tool_call_id=call["id"]))
        # 4. loop: the next call sends everything, tool results included

    return "I stopped after too many steps without an answer."


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Ask your bookmarks a question.")
    parser.add_argument("question")
    parser.add_argument("--email", help="whose bookmarks (default: the first account)")
    args = parser.parse_args()

    async with SessionLocal() as session:
        if args.email:
            user = await session.scalar(select(User).where(User.email == args.email))
        else:
            user = await session.scalar(select(User).order_by(User.id).limit(1))
    if user is None:
        sys.exit("No such account.")

    answer = await ask(args.question, user.id)
    print(f"\n{answer}")


if __name__ == "__main__":
    asyncio.run(_main())
