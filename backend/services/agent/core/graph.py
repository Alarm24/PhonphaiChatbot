from typing import Annotated, TypedDict

from config import get_settings
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from prompts.prompt import SYSTEM_PROMPT
from tools.retriever_tool import TOOLS_LIST


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


settings = get_settings()
model = ChatOpenAI(
    model="google/gemini-2.5-flash",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=settings.OPENROUTER_API_KEY,
    temperature=0,
)

model_with_tools = model.bind_tools(TOOLS_LIST)


def agent_node(state: AgentState):
    """The Brain Node: Decides what to do next."""

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    response = model_with_tools.invoke(messages)

    return {"messages": [response]}


tool_node = ToolNode(TOOLS_LIST)


def should_continue(state: AgentState):
    """Decide: Call a tool OR finish?"""
    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})

workflow.add_edge("tools", "agent")

app = workflow.compile()
