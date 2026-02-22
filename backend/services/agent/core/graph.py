from typing import Annotated, List, TypedDict

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from prompts.prompt import SYSTEM_PROMPT
from tools.retriever_tool import TOOLS_LIST


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The conversation history"]


model = init_chat_model("gemini-2.5-flash-lite", model_provider="google_genai", temperature=0)

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
