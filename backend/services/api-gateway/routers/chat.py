from typing import List

import chatbot_pb2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from state import gRPCState

router = APIRouter()


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    session_id: str
    message: str


class SourceModel(BaseModel):
    title: str
    theme: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    sources: List[SourceModel]
    cost: float = 0.0


# --- Endpoints ---
@router.post("/", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    try:
        # 1. Grab the persistent client opened during startup!
        client = gRPCState.agent_client

        # 2. Make the request
        grpc_request = chatbot_pb2.ChatRequest(
            session_id=request.session_id, user_message=request.message
        )

        grpc_response = await client.Chat(grpc_request)

        # 3. Format response
        sources = [
            SourceModel(title=s.title, theme=s.theme, content=s.content)
            for s in grpc_response.sources
        ]

        return ChatResponse(
            session_id=grpc_response.session_id,
            response=grpc_response.ai_message,
            sources=sources,
            cost=grpc_response.cost,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
