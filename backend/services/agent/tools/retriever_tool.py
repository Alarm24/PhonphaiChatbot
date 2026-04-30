import asyncio
import uuid

import retriever_pb2
from langchain_core.tools import tool
from state import AgentState


async def _execute_search(query: str, theme_enum, theme_name: str) -> tuple[str, list]:
    """Helper to perform the raw gRPC call using the persistent connection."""
    try:
        client = AgentState.retriever_client
        request = retriever_pb2.SearchRequest(query=query, theme=theme_enum, limit=5)
        response = await client.Search(request)

        raw_chunks = []
        context = ""

        for i, res in enumerate(response.results, start=1):
            page_info = getattr(res, "page", "Unknown")

            # 1. Create a unique ID e.g., Remedy-1-a4f2
            unique_suffix = str(uuid.uuid4())[:4]
            chunk_id = f"{theme_name}-{i}-{unique_suffix}"

            # 2. Format the string with the new ID
            context += f"\n--- Chunk [{chunk_id}] ---\n"
            context += f"Source: {res.file_name} (Page: {page_info})\n"
            context += f"Content: {res.content}\n"

            # 3. Save the chunk_id into the raw metadata
            raw_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "file_name": res.file_name,
                    "page": page_info,
                    "content": res.content,
                    "theme": theme_name,
                }
            )

        if not raw_chunks:
            return "No relevant documents found.", []

        return context, raw_chunks

    except Exception as e:
        return f"Error connecting to Knowledge Base: {str(e)}", []


async def _execute_ticket_lookup(ticket_code: str) -> tuple[str, list]:
    """Look up structured Remedy ticket data without passing rows back into the LLM."""
    from core.auth_context import get_current_auth

    normalized_code = ticket_code.strip().upper()
    if not normalized_code:
        return "Ticket lookup skipped because no ticket code was provided.", []

    auth = get_current_auth()

    # Anonymous users must not reach this tool (api-gateway also blocks SKN
    # patterns), but enforce server-side as defense-in-depth.
    if auth.is_anonymous:
        return (
            "Ticket lookup denied: the user is not logged in. Please ask them to log in.",
            [],
        )

    # Admins query without filter; regular users may only see their own tickets.
    staff_filter = None if auth.is_admin else auth.staff_id
    if not auth.is_admin and staff_filter is None:
        return (
            "Ticket lookup denied: this account has no staff_id assigned, "
            "so it cannot be linked to any ticket. Ask an administrator to set one.",
            [],
        )

    try:
        ticket_store = AgentState.ticket_store
        rows = await asyncio.to_thread(
            ticket_store.find_ticket_by_code,
            normalized_code,
            staff_filter,
        )
        artifact = [
            {
                "source_type": "ticket_lookup",
                "ticket_code": normalized_code,
                "rows": rows,
            }
        ]

        if not rows:
            return (
                f"No structured Remedy ticket records were found for {normalized_code}.",
                artifact,
            )

        return (
            f"Structured Remedy ticket lookup completed for {normalized_code}. "
            "Raw database rows were withheld from the model and attached as an artifact.",
            artifact,
        )
    except Exception as e:
        return f"Error looking up Remedy ticket data: {str(e)}", []


# --- The 3 Tools ---
@tool(response_format="content_and_artifact")
async def search_remedy_tickets(ticket_code: str) -> tuple[str, list]:
    """Use this ONLY for exact Remedy ticket codes such as SKN-2567-0006."""
    return await _execute_ticket_lookup(ticket_code)


@tool(response_format="content_and_artifact")
async def search_disaster_protocols(query: str) -> tuple[str, list]:
    """Use this ONLY for emergency situations, server crashes, or disaster recovery protocols."""
    return await _execute_search(query, retriever_pb2.DISASTER, "Disaster")


@tool(response_format="content_and_artifact")
async def search_user_manuals(query: str) -> tuple[str, list]:
    """Use this to look up 'How-To' guides, installation steps, or standard operating procedures."""
    return await _execute_search(query, retriever_pb2.MANUAL, "Manual")


# List of tools to bind to the model
TOOLS_LIST = [search_remedy_tickets, search_disaster_protocols, search_user_manuals]
