import asyncio

from langchain_core.tools import tool


@tool(response_format="content_and_artifact")
async def load_conversation_history(turns: int = 10) -> tuple[str, list]:
    """Load the last N turns of this conversation.
    Use ONLY if the current question references prior context —
    pronouns ('it', 'that', 'นี้'), follow-ups, clarifications,
    or questions that cannot be answered without knowing what was said before.
    Do NOT call for standalone questions you can answer on their own."""
    from core.session_context import get_current_session_id
    from state import AgentState

    session_id = get_current_session_id()
    if not session_id:
        return "No session context available.", []

    store = AgentState.chat_history_store
    if store is None:
        return "Chat history store not initialized.", []

    limit = min(max(turns, 1), 20)
    records = await asyncio.to_thread(store.load_recent, session_id, limit)
    if not records:
        return "No prior conversation history found for this session.", []

    formatted = "\n".join(
        f"[{r['role'].upper()}]: {r['content']}" for r in records
    )
    return (
        f"Prior conversation history (last {len(records)} turns):\n{formatted}",
        records,
    )
