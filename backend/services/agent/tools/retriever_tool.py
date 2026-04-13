import uuid

import retriever_pb2
from context import current_user_id
from langchain_core.tools import tool
from state import AgentState


def _execute_search(query: str, theme_enum, theme_name: str) -> tuple[str, list]:
    """Helper to perform the raw gRPC call using the persistent connection."""
    try:
        client = AgentState.retriever_client
        request = retriever_pb2.SearchRequest(query=query, theme=theme_enum, limit=5)
        response = client.Search(request)

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
                    "chunk_id": chunk_id,  # Added this key
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


def _execute_ticket_lookup(ticket_code: str) -> tuple[str, list]:
    """Look up structured Remedy ticket data without passing rows back into the LLM."""
    user_id = current_user_id.get("")
    if not user_id:
        return (
            "ผู้ใช้ยังไม่ได้เข้าสู่ระบบ กรุณาเข้าสู่ระบบก่อนเพื่อค้นหาข้อมูลคำร้อง",
            [],
        )

    normalized_code = ticket_code.strip().upper()
    if not normalized_code:
        return "Ticket lookup skipped because no ticket code was provided.", []

    try:
        ticket_store = AgentState.ticket_store
        rows = ticket_store.find_ticket_by_code(normalized_code)
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
def search_remedy_tickets(ticket_code: str) -> tuple[str, list]:
    """Use this ONLY for exact Remedy ticket codes such as SKN-2567-0006."""
    return _execute_ticket_lookup(ticket_code)


@tool(response_format="content_and_artifact")
def search_disaster_protocols(query: str) -> tuple[str, list]:
    """Use this ONLY for emergency situations, server crashes, or disaster recovery protocols."""
    return _execute_search(query, retriever_pb2.DISASTER, "Disaster")


@tool(response_format="content_and_artifact")
def search_user_manuals(query: str) -> tuple[str, list]:
    """Use this to look up 'How-To' guides, installation steps, or standard operating procedures."""
    return _execute_search(query, retriever_pb2.MANUAL, "Manual")


# List of tools to bind to the model
TOOLS_LIST = [search_remedy_tickets, search_disaster_protocols, search_user_manuals]
