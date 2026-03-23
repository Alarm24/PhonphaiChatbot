import os
from operator import add
from typing import Annotated, TypedDict

from config import get_settings
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from prompts.prompt import SYSTEM_PROMPT
from pydantic import BaseModel, Field
from tools.retriever_tool import TOOLS_LIST


# --- Output Schema ---
class CitedResponse(BaseModel):
    """ALWAYS use this tool to provide the final answer to the user."""

    answer: str = Field(description="The final response text with inline [x] markers.")
    used_indices: list[int] = Field(
        description="A list of the integer chunk IDs actually used in the answer."
    )


# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_chunks: list
    final_sources: list
    selected_tools: Annotated[list[str], add]


settings = get_settings()

# --- LangSmith Configuration ---
os.environ["LANGCHAIN_TRACING_V2"] =settings.LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

model = ChatOpenAI(
    model="google/gemini-2.5-flash",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=settings.OPENROUTER_API_KEY,
    temperature=0,
)

model_with_tools = model.bind_tools(TOOLS_LIST + [CitedResponse])


def agent_node(state: AgentState):
    """The Brain Node: Decides what to do next."""

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    response = model_with_tools.invoke(messages)

    selected_tools = [
        tool_call["name"] for tool_call in response.tool_calls if tool_call["name"] != "CitedResponse"
    ]

    if selected_tools:
        return {"messages": [response], "selected_tools": selected_tools}

    return {"messages": [response]}


tool_node = ToolNode(TOOLS_LIST)


def format_final_answer(state: AgentState):
    """Intercepts the CitedResponse tool call and appends real citations."""
    last_message = state["messages"][-1]

    # Extract the structured data the LLM generated
    cited_call = next(tc for tc in last_message.tool_calls if tc["name"] == "CitedResponse")
    args = cited_call["args"]

    answer = args["answer"]
    used_indices = args.get("used_indices", [])

    retrieved_chunks = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage) and msg.artifact:
            retrieved_chunks = msg.artifact
            break  # We found the most recent search results!

    # Append the real citations
    final_sources_metadata = []
    if not used_indices or not retrieved_chunks:
        final_text = answer
    else:
        final_text = answer + "\n\n### Sources:\n"
        unique_indices = sorted(list(set(used_indices)))

        for index in unique_indices:
            actual_idx = index - 1  # LLM output is 1-indexed (e.g., [1]), array is 0-indexed

            # Verify the index actually exists (prevents LLM hallucinating fake indices)
            if 0 <= actual_idx < len(retrieved_chunks):
                chunk = retrieved_chunks[actual_idx]
                final_sources_metadata.append(
                    {
                        "title": chunk.get("file_name", "Unknown Document"),
                        "theme": chunk.get("theme", "Unknown Theme"),
                        "content": chunk.get("content", ""),
                    }
                )

                # Append the guaranteed real citation from the artifact
                final_text += f"* **[{index}]** {chunk['file_name']} (Page {chunk['page']})\n"

    return {
        "messages": [AIMessage(content=final_text)],
        "retrieved_chunks": retrieved_chunks,
        "final_sources": final_sources_metadata,
    }


def should_continue(state: AgentState):
    """Decide: Call a tool OR finish?"""
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return END

    if any(tc["name"] == "CitedResponse" for tc in last_message.tool_calls):
        return "format_answer"

    return "tools"


workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("format_answer", format_final_answer)  # Add new node

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"tools": "tools", "format_answer": "format_answer", END: END}
)

workflow.add_edge("tools", "agent")
workflow.add_edge("format_answer", END)

app = workflow.compile()
