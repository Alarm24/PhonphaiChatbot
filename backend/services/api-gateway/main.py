from contextlib import asynccontextmanager

import chatbot_pb2_grpc
import grpc
import retriever_pb2_grpc
import uvicorn
from config import get_settings
from fastapi import FastAPI
from routers import chat, files
from state import gRPCState


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    settings = get_settings()

    # 1. Open persistent gRPC channels
    retriever_channel = grpc.aio.insecure_channel(settings.RETRIEVER_HOST)
    agent_channel = grpc.aio.insecure_channel(settings.AGENT_HOST)

    # 2. Attach clients to the app state
    gRPCState.retriever_client = retriever_pb2_grpc.RetrieverServiceStub(retriever_channel)
    gRPCState.agent_client = chatbot_pb2_grpc.AgentServiceStub(agent_channel)

    yield  # App is running and handling requests here

    # --- SHUTDOWN ---
    await retriever_channel.close()
    await agent_channel.close()


# Initialize FastAPI with the lifespan
app = FastAPI(title="Phonphai API", lifespan=lifespan)

# Include your routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
