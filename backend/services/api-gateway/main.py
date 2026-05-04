from contextlib import asynccontextmanager

import chatbot_pb2_grpc
import grpc
import retriever_pb2_grpc
import uvicorn
from auth.passwords import hash_password
from config import get_settings
from db import AbstractUserStore, make_user_store
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logger import log
from routers import auth, chat, files
from state import gRPCState


def _bootstrap_admin(store: AbstractUserStore, username: str, password: str) -> None:
    """Seed an admin account on first start if none exists. Idempotent."""
    if store.admin_exists():
        return
    if not username or not password:
        log.warning(
            "No admin exists and INITIAL_ADMIN_USERNAME/PASSWORD are not set — "
            "the system has no admin until one is created manually."
        )
        return
    if store.find_by_username(username):
        log.warning(f"User '{username}' already exists but is not admin; skipping bootstrap.")
        return
    store.create_user(
        username=username,
        password_hash=hash_password(password),
        role="admin",
        staff_id=None,
    )
    log.info(f"Bootstrapped initial admin account '{username}'.")


def _bootstrap_user(
    store: AbstractUserStore,
    username: str,
    password: str,
    staff_id: int,
) -> None:
    """Seed a regular user account on first start. Idempotent — skips if username exists."""
    if not username or not password:
        return
    if staff_id <= 0:
        log.warning(
            f"Skipping bootstrap of '{username}': INITIAL_USER_STAFF_ID is not set "
            "(regular users need a staff_id to query their tickets)."
        )
        return
    if store.find_by_username(username):
        return
    store.create_user(
        username=username,
        password_hash=hash_password(password),
        role="user",
        staff_id=staff_id,
    )
    log.info(f"Bootstrapped initial user account '{username}' (staff_id={staff_id}).")


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

    # 3. Connect to the user-data backend (mongo or postgres) and seed accounts
    gRPCState.user_store = make_user_store(settings)
    _bootstrap_admin(
        gRPCState.user_store,
        settings.INITIAL_ADMIN_USERNAME,
        settings.INITIAL_ADMIN_PASSWORD,
    )
    _bootstrap_user(
        gRPCState.user_store,
        settings.INITIAL_USER_USERNAME,
        settings.INITIAL_USER_PASSWORD,
        settings.INITIAL_USER_STAFF_ID,
    )

    yield  # App is running and handling requests here

    # --- SHUTDOWN ---
    await retriever_channel.close()
    await agent_channel.close()


# Initialize FastAPI with the lifespan
app = FastAPI(title="Phonphai API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["POST", "GET", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include your routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
