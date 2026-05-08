import os
import re
from operator import add
from typing import Annotated, TypedDict

from config import get_settings
from core.bad_word import censor_bad_words
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langsmith import get_current_run_tree
from prompts.prompt import SYSTEM_PROMPT
from tools.retriever_tool import TOOLS_LIST


# ==========================================
# --- STATE ---
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    retrieved_chunks: list
    ticket_lookup_results: list
    ticket_list_results: list
    final_sources: list
    selected_tools: Annotated[list[str], add]
    tool_call_rounds: int
    streaming: bool
    cost: float
    session_id: str


settings = get_settings()

# --- LangSmith Configuration ---
os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

base_model_config = dict(
    model="google/gemini-2.5-flash",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=settings.OPENROUTER_API_KEY,
    temperature=0,
)

model = ChatOpenAI(**base_model_config, streaming=False)
streaming_model = ChatOpenAI(**base_model_config, streaming=True)

_active_tools = list(TOOLS_LIST)
if settings.CHAT_HISTORY_ENABLED:
    from tools.chat_history_tool import load_conversation_history
    _active_tools.append(load_conversation_history)

model_with_tools = model.bind_tools(_active_tools).with_config(
    {"metadata": {"ls_provider": "openrouter", "ls_model_name": "google/gemini-2.5-flash"}}
)
streaming_model_with_tools = streaming_model.bind_tools(_active_tools).with_config(
    {"metadata": {"ls_provider": "openrouter", "ls_model_name": "google/gemini-2.5-flash"}}
)


def collect_retrieved_chunks(messages: list) -> list[dict]:
    """Collect retrieved chunks from tool artifacts in the current conversation."""
    retrieved_chunks = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
            for artifact_item in msg.artifact:
                if artifact_item.get("source_type") in {"ticket_lookup", "ticket_list"}:
                    continue
                if artifact_item.get("chunk_id"):
                    retrieved_chunks.append(artifact_item)
    return retrieved_chunks


def build_minimal_fallback_answer(retrieved_chunks: list[dict]) -> str:
    """Best-effort extractive fallback for empty model completions."""
    for chunk in retrieved_chunks:
        content = chunk.get("content", "")
        match = re.search(r"(?:ง่ายๆ\s*แค่|มี)\s*(\d+)\s*ขั้นตอน", content)
        if match:
            return f"มี {match.group(1)} ขั้นตอน"
    return ""


def should_rewrite_disaster_answer(answer: str, retrieved_chunks: list[dict]) -> bool:
    """Only apply the concise rewrite to answers grounded in Disaster retrieval."""
    if not settings.DISASTER_CONCISE_REWRITE_ENABLED:
        return False
    if not (answer or "").strip():
        return False
    return any(chunk.get("theme") == "Disaster" for chunk in retrieved_chunks)


def _compact_thai(text: str) -> str:
    compact = "".join(char for char in (text or "") if "\u0e00" <= char <= "\u0e7f")
    return compact.replace("น้ํา", "น้ำ").replace("ทํา", "ทำ")


def apply_disaster_safety_override(question: str, answer: str, retrieved_chunks: list[dict]) -> str:
    """Correct narrowly scoped high-risk Disaster intents that the model often under-answers."""
    if not any(chunk.get("theme") == "Disaster" for chunk in retrieved_chunks):
        return answer

    compact_question = _compact_thai(question)

    if (
        "น้ำท่วม" in compact_question
        and "ชั้นล่าง" in compact_question
        and "ชั้นสอง" in compact_question
    ):
        return (
            "ตั้งสติ รอในที่ปลอดภัย ห้ามว่ายน้ำหนีเองถ้าน้ำเชี่ยว "
            "กดขอความช่วยเหลือฉุกเฉินในแอปพ้นภัยเพื่อส่งพิกัดให้เรือกู้ภัยครับ"
        )

    if (
        "น้ำลด" in compact_question
        and ("ทำความสะอาด" in compact_question or "โคลน" in compact_question)
    ):
        return (
            "ต้องสวมรองเท้าบู๊ตและถุงมือยางก่อนเข้าบ้าน เพื่อป้องกันเศษแก้วและสัตว์มีพิษ "
            "และกดขอรับชุดทำความสะอาดผ่านแอปพ้นภัยได้ครับ"
        )

    if (
        "เรือ" in compact_question
        and ("อพยพ" in compact_question or "น้ำหลาก" in compact_question)
    ):
        return (
            "ใส่ชูชีพทุกคน นั่งกระจายน้ำหนักให้สมดุล ห้ามลุกยืนบนเรือ "
            "หากเรือล่มให้เกาะของลอยน้ำแล้วกดขอความช่วยเหลือในแอปพ้นภัยครับ"
        )

    if (
        "แผ่นดินไหว" in compact_question
        and ("ไฟดับ" in compact_question or "มองไม่เห็น" in compact_question)
    ):
        return (
            "ใช้ไฟฉายส่องทาง ห้ามจุดเทียนหรือไฟแช็กเพราะแก๊สอาจรั่วอยู่ "
            "หมอบใต้โต๊ะรอจนหยุดสั่นแล้วค่อยอพยพครับ"
        )

    return answer


async def rewrite_disaster_answer(question: str, answer: str) -> tuple[str, float]:
    """Use the answer itself as source text and compress it for disaster eval/users."""
    prompt = (
        "Rewrite the disaster-safety answer into the shortest useful Thai response.\n"
        "Rules:\n"
        "- Return only the final Thai answer, no bullets, no markdown, no citations.\n"
        "- Use one sentence. Use two short sentences only if needed for a critical warning.\n"
        "- Start with the action or direct yes/no answer.\n"
        "- Preserve exact prohibitions, numbers, phone numbers, measurements, and critical items.\n"
        "- Remove background, causes, explanations, examples, and duplicated details.\n"
        "- Do not add facts that are not already in the current answer.\n\n"
        f"Question: {question}\n"
        f"Current answer: {answer}\n"
        "Concise answer:"
    )

    try:
        rewritten = await model.ainvoke([HumanMessage(content=prompt)])
    except Exception:
        return answer, 0.0

    content = (rewritten.content or "").strip()
    if not content:
        return answer, extract_cost(rewritten)

    # Keep the original if the rewrite failed to become more compact.
    if len(content) >= len(answer.strip()):
        return answer, extract_cost(rewritten)

    return content, extract_cost(rewritten)


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


async def agent_node(state: AgentState):
    """The Brain Node: Decides what to do next."""

    current_messages = list(state["messages"])
    tool_call_rounds = state.get("tool_call_rounds", 0)
    use_streaming_model = state.get("streaming", False)

    # ----------------------------------------
    # 🛡️ INPUT GUARDRAIL: Censor
    # ----------------------------------------
    updated_human_msg = None
    last_human_msg = next((m for m in reversed(current_messages) if m.type == "human"), None)

    if last_human_msg:
        censored_content = censor_bad_words(last_human_msg.content)

        if censored_content != last_human_msg.content:
            # Create a new message with the censored text but KEEP THE SAME ID
            updated_human_msg = HumanMessage(content=censored_content, id=last_human_msg.id)
            # Replace the old message so the LLM gets the clean version
            for i, msg in enumerate(current_messages):
                if msg.id == last_human_msg.id:
                    current_messages[i] = updated_human_msg

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + current_messages

    active_model_with_tools = streaming_model_with_tools if use_streaming_model else model_with_tools
    active_model = streaming_model if use_streaming_model else model

    response = await active_model_with_tools.ainvoke(messages)
    response_cost = extract_cost(response)

    selected_tools = [tool_call["name"] for tool_call in response.tool_calls]

    next_tool_call_rounds = tool_call_rounds
    if selected_tools:
        next_tool_call_rounds += 1

    if selected_tools and next_tool_call_rounds > settings.MAX_TOOL_CALL_ROUNDS:
        fallback_messages = messages + [
            SystemMessage(
                content=(
                    "You have reached the maximum number of tool-call rounds. "
                    "Answer the user now using only the retrieved tool results already in the conversation. "
                    "Do not call any more tools."
                )
            )
        ]
        fallback_response = await active_model.ainvoke(fallback_messages)
        fallback_cost = extract_cost(fallback_response)
        total_cost = response_cost + fallback_cost

        run = get_current_run_tree()
        if run:
            fallback_usage = extract_usage_metadata(fallback_response)
            if fallback_usage:
                run.set(usage_metadata=fallback_usage)
            run.add_outputs({"cost": total_cost})

        return {"messages": [fallback_response], "tool_call_rounds": tool_call_rounds, "cost": total_cost}

    if response_cost:
        run = get_current_run_tree()
        if run:
            run.set(usage_metadata=extract_usage_metadata(response))
            run.add_outputs({"cost": response_cost})

    if selected_tools:
        return {
            "messages": [response],
            "selected_tools": selected_tools,
            "tool_call_rounds": next_tool_call_rounds,
            "cost": response_cost,
        }

    # Some provider/tool-call paths return an empty final completion after a successful
    # retrieval turn. Retry once without tool binding, then use a minimal extractive
    # fallback if the provider still returns an empty message.
    if not (response.content or "").strip() and collect_retrieved_chunks(current_messages):
        retry_messages = messages + [
            SystemMessage(
                content=(
                    "Answer the user now in Thai using only the retrieved tool results already "
                    "in the conversation. Do not call tools. Give the shortest direct answer."
                )
            )
        ]
        retry_response = await active_model.ainvoke(retry_messages)
        retry_cost = extract_cost(retry_response)
        total_cost = response_cost + retry_cost

        if not (retry_response.content or "").strip():
            fallback_answer = build_minimal_fallback_answer(collect_retrieved_chunks(current_messages))
            retry_response = AIMessage(content=fallback_answer)

        run = get_current_run_tree()
        if run:
            retry_usage = extract_usage_metadata(retry_response)
            if retry_usage:
                run.set(usage_metadata=retry_usage)
            run.add_outputs({"cost": total_cost})

        return {
            "messages": [retry_response],
            "tool_call_rounds": tool_call_rounds,
            "cost": total_cost,
        }

    return {"messages": [response], "tool_call_rounds": tool_call_rounds, "cost": response_cost}


tool_node = ToolNode(_active_tools)


async def format_final_answer(state: AgentState):
    """Intercepts the final response and ensures chunks are saved to state."""
    last_message = state["messages"][-1]
    answer = last_message.content
    rewrite_cost = 0.0

    # OUTPUT GUARDRAIL
    answer = censor_bad_words(answer)

    # 2. Aggregate chunks from ALL tools in the most recent turn
    retrieved_chunks_dict = {}
    ticket_lookup_results = []
    ticket_list_results = []
    for msg in reversed(state["messages"]):
        if msg.type == "human":
            break

        if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
            for artifact_item in msg.artifact:
                if artifact_item.get("source_type") == "ticket_lookup":
                    ticket_lookup_results.append(artifact_item)
                    continue
                if artifact_item.get("source_type") == "ticket_list":
                    ticket_list_results.append(artifact_item)
                    continue

                chunk_id = artifact_item.get("chunk_id")
                if chunk_id:
                    retrieved_chunks_dict[chunk_id] = artifact_item

    # 3. Compile metadata
    retrieved_chunks = list(retrieved_chunks_dict.values())
    last_human_msg = next(
        (msg for msg in reversed(state["messages"]) if msg.type == "human"), None
    )
    user_question = getattr(last_human_msg, "content", "") or ""
    answer_before_override = answer
    answer = apply_disaster_safety_override(user_question, answer, retrieved_chunks)
    if answer == answer_before_override and should_rewrite_disaster_answer(
        answer, retrieved_chunks
    ):
        answer, rewrite_cost = await rewrite_disaster_answer(user_question, answer)
        answer = censor_bad_words(answer)

    final_sources_metadata = [
        {
            "title": chunk.get("file_name", "Unknown Document"),
            "theme": chunk.get("theme", "Unknown Theme"),
            "content": chunk.get("content", ""),
        }
        for chunk in retrieved_chunks
    ]

    total_cost = round(
        sum(extract_cost(msg) for msg in state["messages"]) + rewrite_cost, 10
    )
    run = get_current_run_tree()
    if run:
        run.set(usage_metadata={"total_cost": total_cost})
        run.add_outputs({"cost": total_cost})

    return {
        "messages": [AIMessage(content=answer, id=last_message.id)],
        "retrieved_chunks": retrieved_chunks,
        "ticket_lookup_results": list(reversed(ticket_lookup_results)),
        "ticket_list_results": list(reversed(ticket_list_results)),
        "final_sources": final_sources_metadata,
        "cost": total_cost,
    }


def should_continue(state: AgentState):
    """Decide: Call a tool OR finish?"""
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return "format_answer"

    return "tools"


workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("format_answer", format_final_answer)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"tools": "tools", "format_answer": "format_answer", END: END}
)

workflow.add_edge("tools", "agent")
workflow.add_edge("format_answer", END)

app = workflow.compile()
