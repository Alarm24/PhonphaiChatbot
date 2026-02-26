import retriever_pb2
from langchain_core.tools import tool
from state import AgentState


def _execute_search(query: str, theme_enum) -> tuple[str, list]:
    """Helper to perform the raw gRPC call using the persistent connection."""
    try:
        client = AgentState.retriever_client
        request = retriever_pb2.SearchRequest(query=query, theme=theme_enum, limit=5)
        response = client.Search(request)

        raw_chunks = []
        context = ""

        # Enumerate starting at 1 to match the LLM's [1], [2] formatting
        for i, res in enumerate(response.results, start=1):
            # Safely grab the page from the updated protobuf
            page_info = getattr(res, "page", "Unknown")

            # 1. Format the string that the LLM will read
            context += f"\n--- Chunk [{i}] ---\n"
            context += f"Source: {res.file_name} (Page: {page_info})\n"
            context += f"Content: {res.content}\n"

            # 2. Save the raw metadata for the backend to use later
            raw_chunks.append({"file_name": res.file_name, "page": page_info})

        if not raw_chunks:
            return "No relevant documents found.", []

        # Return a tuple: (Text for LLM, Artifact for Backend)
        return context, raw_chunks

    except Exception as e:
        return f"Error connecting to Knowledge Base: {str(e)}", []


# --- The 3 Tools ---
@tool(response_format="content_and_artifact")
def search_remedy_tickets(query: str) -> tuple[str, list]:
    """Use this to find solutions for IT tickets, error logs, or specific remedy IDs."""
    return _execute_search(query, retriever_pb2.REMEDY)


@tool(response_format="content_and_artifact")
def search_disaster_protocols(query: str) -> tuple[str, list]:
    """Use this ONLY for emergency situations, server crashes, or disaster recovery protocols."""
    return _execute_search(query, retriever_pb2.DISASTER)


@tool(response_format="content_and_artifact")
def search_user_manuals(query: str) -> tuple[str, list]:
    """Use this to look up 'How-To' guides, installation steps, or standard operating procedures."""
    return _execute_search(query, retriever_pb2.MANUAL)


# List of tools to bind to the model
TOOLS_LIST = [search_remedy_tickets, search_disaster_protocols, search_user_manuals]
