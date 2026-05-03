import asyncio
import json

import chatbot_pb2
import chatbot_pb2_grpc
from core.auth_context import RequestAuth, set_current_auth
from core.graph import app as langgraph_app
from langchain_core.messages import HumanMessage
from logger import log


def _auth_from_request(request) -> RequestAuth:
    """Extract auth context from a gRPC ChatRequest. Empty role == anonymous."""
    raw_staff_id = getattr(request, "staff_id", 0) or 0
    return RequestAuth(
        role=getattr(request, "user_role", "") or "",
        staff_id=int(raw_staff_id) if raw_staff_id else None,
        username=getattr(request, "username", "") or "",
    )


def _format_ticket_lookup_message(ticket_lookups: list[dict]) -> str:
    blocks = []

    for lookup in ticket_lookups:
        ticket_code = lookup.get("ticket_code", "Unknown")
        rows = lookup.get("rows", [])
        if not rows:
            blocks.append(f"ไม่พบข้อมูลคำร้องหมายเลข {ticket_code}")
            continue

        first_row = rows[0]
        status = first_row.get("status") or "-"
        process_level = first_row.get("process_level") or "-"
        blocks.append(
            f"คำร้องหมายเลข {ticket_code} มีสถานะ {status} และมีการดำเนินการระดับ {process_level}"
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
    async def Chat(self, request, context):
        log.info(
            f"🧠 Processing query: {request.user_message} "
            f"(Session: {request.session_id}, "
            f"User: {request.username or 'anonymous'} role={request.user_role or '-'})"
        )

        set_current_auth(_auth_from_request(request))

        initial_state = {
            "messages": [HumanMessage(content=request.user_message)],
            "tool_call_rounds": 0,
        }
        final_state = await langgraph_app.ainvoke(initial_state)

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
            f"🧠 [Stream] Processing query: {request.user_message} "
            f"(Session: {request.session_id}, "
            f"User: {request.username or 'anonymous'} role={request.user_role or '-'})"
        )

        set_current_auth(_auth_from_request(request))

        initial_state = {
            "messages": [HumanMessage(content=request.user_message)],
            "tool_call_rounds": 0,
        }

        # Smooth typewriter pacing — emit small fixed-size chunks at a consistent
        # interval so bursty LLM output (e.g. Gemini sometimes sends 30+ chars at
        # once) becomes a steady stream on the client.
        SMOOTH_CHUNK_SIZE = 2
        SMOOTH_DELAY_SEC = 0.025

        try:
            final_state: dict = {}
            any_token_streamed: bool = False

            async for mode, data in langgraph_app.astream(
                initial_state,
                stream_mode=["updates", "messages"],
            ):
                if mode == "messages":
                    msg_chunk, metadata = data

                    if metadata.get("langgraph_node") != "agent":
                        continue

                    if getattr(msg_chunk, "tool_call_chunks", None):
                        continue

                    content = getattr(msg_chunk, "content", "") or ""
                    if isinstance(content, list):
                        content = "".join(
                            part.get("text", "")
                            for part in content
                            if isinstance(part, dict)
                        )
                    if not content:
                        continue

                    any_token_streamed = True
                    for i in range(0, len(content), SMOOTH_CHUNK_SIZE):
                        yield chatbot_pb2.ChatStreamChunk(
                            session_id=request.session_id,
                            token=content[i:i + SMOOTH_CHUNK_SIZE],
                        )
                        await asyncio.sleep(SMOOTH_DELAY_SEC)

                elif mode == "updates":
                    for _node_name, update in data.items():
                        for key, value in update.items():
                            final_state[key] = value

            messages = final_state.get("messages", [])
            ai_text = messages[-1].content if messages else ""

            sources, ticket_override = _build_sources(final_state)
            if ticket_override:
                ai_text = ticket_override

            cost = float(final_state.get("cost") or 0.0)

            if not any_token_streamed and ai_text:
                for i in range(0, len(ai_text), SMOOTH_CHUNK_SIZE):
                    yield chatbot_pb2.ChatStreamChunk(
                        session_id=request.session_id,
                        token=ai_text[i:i + SMOOTH_CHUNK_SIZE],
                    )
                    await asyncio.sleep(SMOOTH_DELAY_SEC)

            yield chatbot_pb2.ChatStreamChunk(
                session_id=request.session_id,
                final_response=chatbot_pb2.ChatResponse(
                    session_id=request.session_id,
                    ai_message=ai_text,
                    sources=sources,
                    cost=cost,
                ),
            )
        except Exception as e:
            log.error(f"[Stream] Error: {e}")
            yield chatbot_pb2.ChatStreamChunk(
                session_id=request.session_id,
                error=str(e),
            )
