import asyncio
import re
import uuid

import retriever_pb2
from config import get_settings
from langchain_core.tools import tool
from state import AgentState

ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _contains_thai(text: str) -> bool:
    return any(0x0E00 <= ord(char) <= 0x0E7F for char in text)


def _tokenize_for_overlap(text: str) -> set[str]:
    normalized = (text or "").lower()
    tokens = set(ASCII_TOKEN_RE.findall(normalized))

    if _contains_thai(normalized):
        compact_thai = "".join(
            char for char in normalized if 0x0E00 <= ord(char) <= 0x0E7F
        )
        tokens.update(
            compact_thai[index : index + 3]
            for index in range(max(len(compact_thai) - 2, 0))
        )

    return {token for token in tokens if token}


def _build_focused_excerpt(content: str, query: str, max_chars: int = 1800) -> str:
    """Trim large retrieved chunks to the lines most relevant to the current query."""
    content = (content or "").strip()
    if len(content) <= max_chars:
        return content

    query_tokens = _tokenize_for_overlap(query)
    if not query_tokens:
        return content[:max_chars].rstrip()

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return content[:max_chars].rstrip()

    scored_lines = []
    for index, line in enumerate(lines):
        line_tokens = _tokenize_for_overlap(line)
        overlap = len(query_tokens & line_tokens)
        if overlap:
            scored_lines.append((overlap, index))

    if not scored_lines:
        return content[:max_chars].rstrip()

    selected_indexes: set[int] = set()
    for _score, index in sorted(scored_lines, reverse=True)[:6]:
        for nearby_index in range(max(index - 2, 0), min(index + 3, len(lines))):
            selected_indexes.add(nearby_index)

    excerpt_parts = []
    current_length = 0
    for index in sorted(selected_indexes):
        line = lines[index]
        added_length = len(line) + 1
        if current_length + added_length > max_chars:
            break
        excerpt_parts.append(line)
        current_length += added_length

    return "\n".join(excerpt_parts).strip() or content[:max_chars].rstrip()


async def _execute_search(query: str, theme_enum, theme_name: str) -> tuple[str, list]:
    """Helper to perform the raw gRPC call using the persistent connection."""
    try:
        settings = get_settings()
        search_limit = (
            settings.DISASTER_RETRIEVER_SEARCH_LIMIT
            if theme_name == "Disaster"
            else settings.RETRIEVER_SEARCH_LIMIT
        )
        excerpt_max_chars = (
            settings.DISASTER_EXCERPT_MAX_CHARS
            if theme_name == "Disaster"
            else 1800
        )
        client = AgentState.retriever_client
        request = retriever_pb2.SearchRequest(
            query=query,
            theme=theme_enum,
            limit=search_limit,
        )
        response = await client.Search(request)

        raw_chunks = []
        context = ""

        for i, res in enumerate(response.results, start=1):
            page_info = getattr(res, "page", "Unknown")
            focused_content = _build_focused_excerpt(
                res.content, query, max_chars=excerpt_max_chars
            )

            # 1. Create a unique ID e.g., Remedy-1-a4f2
            unique_suffix = str(uuid.uuid4())[:4]
            chunk_id = f"{theme_name}-{i}-{unique_suffix}"

            # 2. Format the string with the new ID
            context += f"\n--- Chunk [{chunk_id}] ---\n"
            context += f"Source: {res.file_name} (Page: {page_info})\n"
            context += f"Content: {focused_content}\n"

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
