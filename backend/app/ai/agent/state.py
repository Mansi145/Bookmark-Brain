"""What the agent knows while it works: the conversation so far.

In manual_loop.py this was a plain list we appended to. In LangGraph it's the graph's "state":
each node gets it and returns only what changed, e.g. {"messages": [reply]}. The annotation says
how a change joins the state: `add_messages` appends new messages (replacing one with the same
id) instead of overwriting the list.

The user isn't in the state: tools read who's asking from the run's config, which only our code
sets (see tools.py). The system prompt isn't either; the agent node adds it to each model call,
so a saved conversation holds only what was said.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
