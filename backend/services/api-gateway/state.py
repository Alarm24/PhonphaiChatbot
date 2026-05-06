from db.base import AbstractChatHistoryStore, AbstractUserStore


class gRPCState:
    retriever_client = None
    agent_client = None
    user_store: AbstractUserStore | None = None
    chat_history_store: AbstractChatHistoryStore | None = None
