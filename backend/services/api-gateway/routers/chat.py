import asyncio
import json
import re
from typing import List

import chatbot_pb2
from auth.dependencies import CurrentUser, get_optional_user, require_user
from config import get_settings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from state import gRPCState

router = APIRouter()

# Matches Remedy ticket codes such as SKN-2567-0006, BKK-2569-0001, or UTH-2569-0001.
TICKET_CODE_PATTERN = re.compile(r"\b[A-Z]{3}[-\s]?\d{4}[-\s]?\d{4}\b", re.IGNORECASE)


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


def _build_grpc_request(
    req: ChatRequest,
    user: CurrentUser | None,
    session_id: str,
) -> chatbot_pb2.ChatRequest:
    """Embed auth context into the gRPC ChatRequest. Anonymous users get blank role/staff_id."""
    return chatbot_pb2.ChatRequest(
        session_id=session_id,
        user_message=req.message,
        user_role=user.role if user else "",
        staff_id=user.staff_id if (user and user.staff_id is not None) else 0,
        username=user.username if user else "",
    )


def _enforce_ticket_login(message: str, user: CurrentUser | None) -> None:
    """Reject ticket queries from anonymous users; frontend modal is just UX, this is the gate."""
    if user is not None:
        return
    if TICKET_CODE_PATTERN.search(message):
        raise HTTPException(
            status_code=401,
            detail="Login required to query Remedy tickets (PPP-XXXX-XXXX).",
        )


# --- Endpoints ---
@router.post("/", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    _enforce_ticket_login(request.message, user)
    settings = get_settings()
    effective_session_id = user.user_id if user else request.session_id
    try:
        client = gRPCState.agent_client
        grpc_response = await client.Chat(_build_grpc_request(request, user, effective_session_id))

        sources = [
            SourceModel(title=s.title, theme=s.theme, content=s.content)
            for s in grpc_response.sources
        ]

        if settings.CHAT_HISTORY_ENABLED and user and gRPCState.chat_history_store:
            store = gRPCState.chat_history_store
            await asyncio.to_thread(store.append, effective_session_id, user.user_id, "user", request.message)
            await asyncio.to_thread(store.append, effective_session_id, user.user_id, "assistant", grpc_response.ai_message)

        return ChatResponse(
            session_id=grpc_response.session_id,
            response=grpc_response.ai_message,
            sources=sources,
            cost=grpc_response.cost,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user: CurrentUser | None = Depends(get_optional_user),
):
    _enforce_ticket_login(request.message, user)
    settings = get_settings()
    effective_session_id = user.user_id if user else request.session_id

    client = gRPCState.agent_client
    grpc_request = _build_grpc_request(request, user, effective_session_id)

    async def event_generator():
        ai_message_accumulated = ""
        try:
            async for chunk in client.ChatStream(grpc_request):
                payload_type = chunk.WhichOneof("payload")

                if payload_type == "token":
                    data = json.dumps({"type": "token", "content": chunk.token})
                    yield f"data: {data}\n\n"

                elif payload_type == "final_response":
                    resp = chunk.final_response
                    ai_message_accumulated = resp.ai_message
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
        finally:
            if settings.CHAT_HISTORY_ENABLED and user and gRPCState.chat_history_store and ai_message_accumulated:
                store = gRPCState.chat_history_store
                asyncio.create_task(asyncio.to_thread(
                    store.append, effective_session_id, user.user_id, "user", request.message
                ))
                asyncio.create_task(asyncio.to_thread(
                    store.append, effective_session_id, user.user_id, "assistant", ai_message_accumulated
                ))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/history", status_code=204)
async def clear_chat_history(user: CurrentUser = Depends(require_user)):
    settings = get_settings()
    if not settings.CHAT_HISTORY_ENABLED:
        raise HTTPException(status_code=404, detail="Chat history is not enabled.")
    store = gRPCState.chat_history_store
    await asyncio.to_thread(store.delete_for_user, user.user_id)
