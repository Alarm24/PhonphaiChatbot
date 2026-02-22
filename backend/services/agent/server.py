import chatbot_pb2
import chatbot_pb2_grpc
from core.graph import app as langgraph_app
from langchain_core.messages import HumanMessage
from logger import log


class AgentServicer(chatbot_pb2_grpc.AgentServiceServicer):
    def Chat(self, request, context):
        log.info(f"🧠 Processing query: {request.user_message} (Session: {request.session_id})")

        # 1. Prepare Input for LangGraph
        initial_state = {"messages": [HumanMessage(content=request.user_message)]}

        # 2. Run the Graph
        final_state = langgraph_app.invoke(initial_state)
        final_message = final_state["messages"][-1]
        ai_text = final_message.content

        # 3. Extract Sources (Citations)
        sources = []
        for msg in final_state["messages"]:
            if msg.type == "tool":
                sources.append(
                    chatbot_pb2.Source(
                        title="Retrieved Document",
                        theme="UNKNOWN",
                        content=msg.content[:200] + "...",
                    )
                )

        # 4. Return correct fields based on your chatbot.proto
        return chatbot_pb2.ChatResponse(
            session_id=request.session_id, ai_message=ai_text, sources=sources
        )
