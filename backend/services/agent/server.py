import json

import chatbot_pb2
import chatbot_pb2_grpc
from context import current_user_id
from core.graph import app as langgraph_app
from langchain_core.messages import HumanMessage
from logger import log


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
    def Chat(self, request, context):
        log.info(f"🧠 Processing query: {request.user_message} (Session: {request.session_id})")

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
            f"🧠 [Stream] Processing query: {request.user_message} (Session: {request.session_id})"
        )

        current_user_id.set(request.user_id)
        initial_state = {"messages": [HumanMessage(content=request.user_message)]}

        try:
            # Run the graph to completion using astream to get node-level updates
            final_state = {}
            async for chunk in langgraph_app.astream(
                initial_state, stream_mode="updates"
            ):
                for node_name, update in chunk.items():
                    # Merge each node's output into final_state
                    for key, value in update.items():
                        final_state[key] = value

            # Extract the final answer text
            messages = final_state.get("messages", [])
            ai_text = messages[-1].content if messages else ""

            sources, ticket_override = _build_sources(final_state)
            if ticket_override:
                ai_text = ticket_override

            # Stream the answer text word-by-word for typewriter effect
            words = ai_text.split(" ")
            for i, word in enumerate(words):
                token = word if i == 0 else " " + word
                yield chatbot_pb2.ChatStreamChunk(
                    session_id=request.session_id,
                    token=token,
                )

            # Send final response with sources and cost
            cost = float(final_state.get("cost") or 0.0)
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
