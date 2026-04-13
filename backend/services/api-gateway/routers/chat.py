import json
from typing import List

import chatbot_pb2
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
        client = gRPCState.agent_client

        grpc_request = chatbot_pb2.ChatRequest(
            session_id=request.session_id, user_message=request.message
        )

        grpc_response = await client.Chat(grpc_request)

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


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    client = gRPCState.agent_client
    grpc_request = chatbot_pb2.ChatRequest(
        session_id=request.session_id, user_message=request.message
    )

    async def event_generator():
        try:
            async for chunk in client.ChatStream(grpc_request):
                payload_type = chunk.WhichOneof("payload")

                if payload_type == "token":
                    data = json.dumps({"type": "token", "content": chunk.token})
                    yield f"data: {data}\n\n"

                elif payload_type == "final_response":
                    resp = chunk.final_response
                    sources = [
                        {"title": s.title, "theme": s.theme, "content": s.content}
                        for s in resp.sources
                    ]
                    data = json.dumps({
                        "type": "done",
                        "session_id": resp.session_id,
                        "response": resp.ai_message,
                        "sources": sources,
                        "cost": resp.cost,
                    })
                    yield f"data: {data}\n\n"

                elif payload_type == "error":
                    data = json.dumps({"type": "error", "message": chunk.error})
                    yield f"data: {data}\n\n"
        except Exception as e:
            data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
