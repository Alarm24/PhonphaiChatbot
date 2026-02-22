import retriever_pb2
from langchain.tools import tool

# Import the global state where our persistent client lives
from state import AgentState


def _execute_search(query: str, theme_enum) -> str:
    """Helper to perform the raw gRPC call using the persistent connection."""
    try:
        # 1. Grab the persistent client (Zero connection overhead!)
        client = AgentState.retriever_client

        # 2. Make the request
        request = retriever_pb2.SearchRequest(query=query, theme=theme_enum, limit=3)
        response = client.Search(request)

        # 3. Format results for the LLM
        context = ""
        for res in response.results:
            context += f"Source: {res.file_name}\nContent: {res.content}\n---\n"

        return context if context else "No relevant documents found."
    except Exception as e:
        return f"Error connecting to Knowledge Base: {str(e)}"


# --- The 3 Tools ---
@tool
def search_remedy_tickets(query: str) -> str:
    """Use this to find solutions for IT tickets, error logs, or specific remedy IDs."""
    return _execute_search(query, retriever_pb2.REMEDY)


@tool
def search_disaster_protocols(query: str) -> str:
    """Use this ONLY for emergency situations, server crashes, or disaster recovery protocols."""
    return _execute_search(query, retriever_pb2.DISASTER)


@tool
def search_user_manuals(query: str) -> str:
    """Use this to look up 'How-To' guides, installation steps, or standard operating procedures."""
    return _execute_search(query, retriever_pb2.MANUAL)


# List of tools to bind to the model
TOOLS_LIST = [search_remedy_tickets, search_disaster_protocols, search_user_manuals]
