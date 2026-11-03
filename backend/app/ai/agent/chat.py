"""One Ask turn: the agent answers a question in a chat, streaming what it does as it goes.

Memory (owner: only while a chat is open). LangGraph's checkpointer saves the graph's state after
each step under a "thread id", and a run with the same id starts from that state, so a follow-up
question joins the whole conversation so far. InMemorySaver keeps those states in this process:
nothing reaches the database, and a restart (or the free server going to sleep) forgets every
open chat, after which a follow-up starts afresh. InMemorySaver never forgets on its own, so
OpenChats deletes chats left idle for an hour and keeps at most MAX_CHATS.

Streaming: graph.astream with two stream modes at once.
- "updates": each node's output as it finishes. The agent's tool calls become "step" events
  (running), and the tools' results finish them (done, with how many bookmarks came back).
- "messages": the model's reply token by token, as "token" events, so the answer appears while
  it's written. A model can write a little before deciding to call a tool; a step follows that
  text, and the page shows only the text after the last step.
Last comes "answer": the final text with its citations tidied to [bookmark:ID], the cited ids in
order, and the other bookmarks the tools found.
"""

import json
import re
import time
from collections import OrderedDict
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.agent.graph import STOPPED, build_graph, run_config

# Models don't always copy the format exactly: "[bookmark: 10]" is common.
CITATION = re.compile(r"\[bookmark:\s*(\d+)\s*\]")


class OpenChats:
    """The conversations of open chats, in this server's memory."""

    IDLE_SECONDS = 3600
    MAX_CHATS = 500

    def __init__(self) -> None:
        self.checkpointer = InMemorySaver()
        self.graph = build_graph(self.checkpointer)
        self._last_used: OrderedDict[str, float] = OrderedDict()  # thread id -> last used

    def thread_id(self, user_id: int, chat_id: str) -> str:
        """The chat's key, marked as used now. It includes the user, so a chat id from one
        user can never open another user's chat."""
        thread_id = f"{user_id}:{chat_id}"
        self._last_used[thread_id] = time.monotonic()
        self._last_used.move_to_end(thread_id)
        self._forget_old()
        return thread_id

    def _forget_old(self) -> None:
        now = time.monotonic()
        while self._last_used:
            oldest, used = next(iter(self._last_used.items()))
            if len(self._last_used) <= self.MAX_CHATS and now - used < self.IDLE_SECONDS:
                return
            del self._last_used[oldest]
            self.checkpointer.delete_thread(oldest)


open_chats = OpenChats()


async def turn(
    question: str, *, user_id: int, chat_id: str, sessions: async_sessionmaker[AsyncSession]
) -> AsyncIterator[tuple[str, dict]]:
    """Answer `question` in the chat, yielding ("step" | "token" | "answer", data) events."""
    config = run_config(user_id, sessions)
    config["configurable"]["thread_id"] = open_chats.thread_id(user_id, chat_id)
    stream = open_chats.graph.astream(
        {"messages": [HumanMessage(question)]}, config, stream_mode=["updates", "messages"]
    )
    found: list[int] = []
    answer = ""
    try:
        async for mode, chunk in stream:
            if mode == "messages":
                message, metadata = chunk
                if metadata.get("langgraph_node") == "agent" and isinstance(message, AIMessage):
                    if message.text:
                        yield "token", {"text": message.text}
                continue
            for update in chunk.values():
                for message in update["messages"]:
                    if isinstance(message, ToolMessage):
                        results = _bookmarks_in(message.content)
                        found += [r["id"] for r in results if r["id"] not in found]
                        step = {"id": message.tool_call_id, "status": "done", "found": len(results)}
                        if message.name == "read_bookmark" and results:
                            step["title"] = results[0].get("title")
                        yield "step", step
                    elif message.tool_calls:
                        for call in message.tool_calls:
                            yield (
                                "step",
                                {
                                    "id": call["id"],
                                    "status": "running",
                                    "tool": call["name"],
                                    "args": call["args"],
                                },
                            )
                    else:
                        answer = message.text
    except GraphRecursionError:
        answer = STOPPED

    text = CITATION.sub(r"[bookmark:\1]", answer)
    cited = list(dict.fromkeys(int(i) for i in CITATION.findall(text)))
    yield "answer", {"text": text, "cited": cited, "found": [i for i in found if i not in cited]}


def _bookmarks_in(content) -> list[dict]:
    """The bookmarks in a tool result: a list (search) or one (read), never an error."""
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        return []  # ToolNode's error text, e.g. for a tool that doesn't exist
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, dict) and "id" in item]
