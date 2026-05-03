from db.base import AbstractUserStore


class gRPCState:
    retriever_client = None
    agent_client = None
    user_store: AbstractUserStore | None = None
