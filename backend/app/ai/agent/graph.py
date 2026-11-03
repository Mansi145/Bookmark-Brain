"""The agent as a LangGraph graph: the same loop as manual_loop.py, declared as nodes and edges.

    START → agent ──(asked for tools?)── yes → tools ─┐
              ▲                                       │
              └───────────────────────────────────────┘
              └── no → END

- agent node: the model decides (manual_loop's step 1).
- tools node: LangGraph's ToolNode runs every tool call in the reply, at the same time, and adds
  each result as a ToolMessage; an unknown tool or a tool error becomes a message the model can
  read instead of a crash (step 3).
- the conditional edge after agent: plain text ends the run, tool calls go to tools (step 2).
- tools always leads back to agent (step 4).

LangGraph runs the loop, keeps the state (state.py), stops after RECURSION_LIMIT steps, and can
stream each step and token as it happens, which the Ask page will use.

Try it on your own bookmarks: `uv run python -m scripts.ask "what have I saved about postgres?"`
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import llm
from app.ai.agent.state import AgentState
from app.ai.agent.tools import TOOLS
from app.ai.chains import load_prompt
from app.db import SessionLocal

# Every node that runs is one step, so 6 model calls with 5 rounds of tools in between is 11.
# Without a limit, a confused model could loop forever (and use up the free quota).
RECURSION_LIMIT = 12
STOPPED = "I stopped after too many steps without an answer."


async def agent(state: AgentState) -> dict:
    """Ask the model what to do next, given the conversation so far."""
    model = llm.get_tool_model(TOOLS)
    reply = await model.ainvoke([SystemMessage(load_prompt("agent")), *state["messages"]])
    return {"messages": [reply]}  # add_messages appends it to the state


def next_step(state: AgentState) -> str:
    """After the model's reply: run the tools it asked for, or finish."""
    return "tools" if state["messages"][-1].tool_calls else END


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", next_step, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)


def run_config(user_id: int, sessions: async_sessionmaker[AsyncSession] = SessionLocal) -> dict:
    """The run's config: whose bookmarks the tools see (from our code, never the model)."""
    return {
        "configurable": {"user_id": user_id, "sessions": sessions},
        "recursion_limit": RECURSION_LIMIT,
    }


async def ask(
    question: str, user_id: int, *, sessions: async_sessionmaker[AsyncSession] = SessionLocal
) -> str:
    """One question, one answer, no memory (that comes with the checkpointer)."""
    try:
        state = await build_graph().ainvoke(
            {"messages": [HumanMessage(question)]}, run_config(user_id, sessions)
        )
    except GraphRecursionError:
        return STOPPED
    return state["messages"][-1].text
