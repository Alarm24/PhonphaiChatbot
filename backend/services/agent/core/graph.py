import os
from operator import add
from typing import Annotated, TypedDict

from config import get_settings
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langsmith import get_current_run_tree
from prompts.prompt import SYSTEM_PROMPT
from pydantic import BaseModel, Field
from tools.retriever_tool import TOOLS_LIST


# --- Output Schema ---
class CitedResponse(BaseModel):
    """ALWAYS use this tool to provide the final answer to the user."""

    answer: str = Field(description="The final response text with inline [x] markers.")
    used_indices: list[str] = Field(
        description="A list of the string chunk IDs actually used in the answer (e.g., ['Remedy-1', 'Manual-2'])."
    )


# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_chunks: list
    final_sources: list
    selected_tools: Annotated[list[str], add]
    cost: float


settings = get_settings()

# --- LangSmith Configuration ---
os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

model = ChatOpenAI(
    model="google/gemini-2.5-flash",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=settings.OPENROUTER_API_KEY,
    temperature=0,
)

model_with_tools = model.bind_tools(TOOLS_LIST + [CitedResponse]).with_config(
    {"metadata": {"ls_provider": "openrouter", "ls_model_name": "google/gemini-2.5-flash"}}
)


def extract_cost(message: AIMessage | ToolMessage | SystemMessage | object) -> float:
    """Best-effort extraction of OpenRouter-reported cost from a LangChain message."""
    response_metadata = getattr(message, "response_metadata", None) or {}
    usage_metadata = getattr(message, "usage_metadata", None) or {}

    candidates = (
        response_metadata.get("cost"),
        response_metadata.get("token_usage", {}).get("cost"),
        response_metadata.get("usage", {}).get("cost"),
        usage_metadata.get("cost"),
        usage_metadata.get("token_usage", {}).get("cost"),
    )
    for value in candidates:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def extract_usage_metadata(message: AIMessage | ToolMessage | SystemMessage | object) -> dict:
    """Map OpenRouter/LangChain response metadata into LangSmith usage_metadata."""
    response_metadata = getattr(message, "response_metadata", None) or {}
    usage = response_metadata.get("token_usage", {}) or {}
    if not usage:
        return {}

    cost_details = usage.get("cost_details", {}) or {}
    usage_metadata: dict[str, object] = {
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "input_token_details": {
            "audio": usage.get("prompt_tokens_details", {}).get("audio_tokens", 0),
            "cache_read": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            "cache_creation": usage.get("prompt_tokens_details", {}).get("cache_write_tokens", 0),
            "video": usage.get("prompt_tokens_details", {}).get("video_tokens", 0),
        },
        "output_token_details": {
            "audio": usage.get("completion_tokens_details", {}).get("audio_tokens", 0),
            "reasoning": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "image": usage.get("completion_tokens_details", {}).get("image_tokens", 0),
        },
        "total_cost": float(usage.get("cost", 0.0) or 0.0),
    }

    prompt_cost = cost_details.get("upstream_inference_prompt_cost")
    completion_cost = cost_details.get("upstream_inference_completions_cost")
    if prompt_cost is not None:
        usage_metadata["input_cost"] = float(prompt_cost)
    if completion_cost is not None:
        usage_metadata["output_cost"] = float(completion_cost)

    return usage_metadata


def agent_node(state: AgentState):
    """The Brain Node: Decides what to do next."""

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    response = model_with_tools.invoke(messages)
    response_cost = extract_cost(response)

    selected_tools = [
        tool_call["name"]
        for tool_call in response.tool_calls
        if tool_call["name"] != "CitedResponse"
    ]

    if response_cost:
        run = get_current_run_tree()
        if run:
            run.set(usage_metadata=extract_usage_metadata(response))
            run.add_outputs({"cost": response_cost})

    if selected_tools:
        return {"messages": [response], "selected_tools": selected_tools, "cost": response_cost}

    return {"messages": [response], "cost": response_cost}


tool_node = ToolNode(TOOLS_LIST)


def format_final_answer(state: AgentState):
    """Intercepts the final response and ensures chunks are saved to state."""
    last_message = state["messages"][-1]

    # 1. Safely extract the answer depending on how the model responded
    cited_calls = [
        tc for tc in getattr(last_message, "tool_calls", []) if tc["name"] == "CitedResponse"
    ]

    if cited_calls:
        answer = cited_calls[0]["args"].get("answer", "")
    else:
        answer = last_message.content

    # 2. Aggregate chunks from ALL tools in the most recent turn
    retrieved_chunks_dict = {}
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            break

        if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
            # Map them by chunk_id for easy lookup
            for chunk in msg.artifact:
                retrieved_chunks_dict[chunk["chunk_id"]] = chunk

    # 3. Compile metadata
    final_sources_metadata = [
        {
            "title": chunk.get("file_name", "Unknown Document"),
            "theme": chunk.get("theme", "Unknown Theme"),
            "content": chunk.get("content", ""),
        }
        for chunk in retrieved_chunks_dict.values()
    ]

    total_cost = round(sum(extract_cost(msg) for msg in state["messages"]), 10)
    run = get_current_run_tree()
    if run:
        run.set(usage_metadata={"total_cost": total_cost})
        run.add_outputs({"cost": total_cost})

    return {
        "messages": [AIMessage(content=answer, id=last_message.id)],
        "retrieved_chunks": list(retrieved_chunks_dict.values()),
        "final_sources": final_sources_metadata,
        "cost": total_cost,
    }


def should_continue(state: AgentState):
    """Decide: Call a tool OR finish?"""
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return "format_answer"

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
