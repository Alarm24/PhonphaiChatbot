import asyncio
import json

import chatbot_pb2
import chatbot_pb2_grpc
from context import current_user_id
from core.graph import (
    FINAL_STREAM_SYSTEM_PROMPT,
    app as langgraph_app,
    extract_cost,
    extract_stream_text,
    run_tool_phase,
    streaming_answer_model,
)
from langchain_core.messages import HumanMessage, SystemMessage
from logger import log


def _format_ticket_lookup_message(ticket_lookups: list[dict]) -> str:
    blocks = []

    for lookup in ticket_lookups:
        ticket_code = lookup.get("ticket_code", "Unknown")
        rows = lookup.get("rows", [])
        if not rows:
            blocks.append(f"à¹„à¸¡à¹ˆà¸žà¸šà¸‚à¹‰à¸­à¸¡à¸¹à¸¥à¸„à¸³à¸£à¹‰à¸­à¸‡à¸«à¸¡à¸²à¸¢à¹€à¸¥à¸‚ {ticket_code}")
            continue

        first_row = rows[0]
        status = first_row.get("status") or "-"
        process_level = first_row.get("process_level") or "-"
        blocks.append(
            f"à¸„à¸³à¸£à¹‰à¸­à¸‡à¸«à¸¡à¸²à¸¢à¹€à¸¥à¸‚ {ticket_code} à¸¡à¸µà¸ªà¸–à¸²à¸™à¸° {status} à¹à¸¥à¸°à¸¡à¸µà¸à¸²à¸£à¸”à¸³à¹€à¸™à¸´à¸™à¸à¸²à¸£à¸£à¸°à¸”à¸±à¸š {process_level}"
        )

    return "\n\n".join(blocks)


def _build_sources(final_state: dict) -> tuple[list, str | None]:
    """Build protobuf Source list and optional ticket override text from final graph state."""
    source_items = final_state.get("final_sources", [])
    sources = [
        chatbot_pb2.Source(
            title=source.get("title", "Retrieved Document"),
            theme=source.get("theme", "Unknown Theme"),
            content=source.get("content", ""),
        )
        for source in source_items
    ]
    retrieved_chunks = final_state.get("retrieved_chunks", [])
    for chunk in retrieved_chunks:
        sources.append(
            chatbot_pb2.Source(
                title=chunk.get("file_name", "Retrieved Chunk"),
                theme="__retrieved_chunk__",
                content=chunk.get("content", ""),
            )
        )

    ticket_override = None
    ticket_lookups = final_state.get("ticket_lookup_results", [])
    if ticket_lookups:
        ticket_override = _format_ticket_lookup_message(ticket_lookups)
        for lookup in ticket_lookups:
            sources.append(
                chatbot_pb2.Source(
                    title=lookup.get("ticket_code", "Ticket Lookup"),
                    theme="ticket_lookup",
                    content=json.dumps(lookup.get("rows", []), ensure_ascii=False),
                )
            )

    selected_tools = final_state.get("selected_tools", [])
    if selected_tools:
        sources.append(
            chatbot_pb2.Source(
                title="__selected_tools__",
                theme="__meta__",
                content="|".join(selected_tools),
            )
        )

    return sources, ticket_override


class AgentServicer(chatbot_pb2_grpc.AgentServiceServicer):
    def Chat(self, request, context):
        log.info(f"ðŸ§  Processing query: {request.user_message} (Session: {request.session_id})")

        current_user_id.set(request.user_id)
        initial_state = {"messages": [HumanMessage(content=request.user_message)]}
        final_state = langgraph_app.invoke(initial_state)

        final_message = final_state["messages"][-1]
        ai_text = final_message.content

        sources, ticket_override = _build_sources(final_state)
        if ticket_override:
            ai_text = ticket_override

        cost = float(final_state.get("cost") or 0.0)

        return chatbot_pb2.ChatResponse(
            session_id=request.session_id,
            ai_message=ai_text,
            sources=sources,
            cost=cost,
        )

    async def ChatStream(self, request, context):
        log.info(
            f"ðŸ§  [Stream] Processing query: {request.user_message} (Session: {request.session_id})"
        )

        current_user_id.set(request.user_id)

        try:
            tool_phase = await asyncio.to_thread(run_tool_phase, request.user_message)
            sources, ticket_override = _build_sources(tool_phase)
            total_cost = float(tool_phase.get("cost") or 0.0)

            if ticket_override:
                ai_text = ticket_override
                words = ai_text.split(" ")
                for i, word in enumerate(words):
                    token = word if i == 0 else " " + word
                    yield chatbot_pb2.ChatStreamChunk(
                        session_id=request.session_id,
                        token=token,
                    )
                    await asyncio.sleep(0)
            else:
                context_block = tool_phase.get("retrieved_context", "")
                stream_messages = [
                    SystemMessage(content=FINAL_STREAM_SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            f"User question:\n{request.user_message}\n\n"
                            f"Retrieved context:\n{context_block or 'No retrieved context provided.'}"
                        )
                    ),
                ]

                streamed_parts = []
                async for chunk in streaming_answer_model.astream(stream_messages):
                    total_cost += extract_cost(chunk)
                    token = extract_stream_text(chunk)
                    if not token:
                        continue

                    streamed_parts.append(token)
                    yield chatbot_pb2.ChatStreamChunk(
                        session_id=request.session_id,
                        token=token,
                    )
                    await asyncio.sleep(0)

                ai_text = "".join(streamed_parts)

            yield chatbot_pb2.ChatStreamChunk(
                session_id=request.session_id,
                final_response=chatbot_pb2.ChatResponse(
                    session_id=request.session_id,
                    ai_message=ai_text,
                    sources=sources,
                    cost=total_cost,
                ),
            )
        except Exception as e:
            log.error(f"[Stream] Error: {e}")
            yield chatbot_pb2.ChatStreamChunk(
                session_id=request.session_id,
                error=str(e),
            )
