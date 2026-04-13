import asyncio

import chatbot_pb2_grpc
import grpc
import retriever_pb2_grpc
from config import get_settings
from db.postgres import PostgresTicketStore
from logger import log
from server import AgentServicer
from state import AgentState


async def serve():
    settings = get_settings()

    # 1. Establish persistent connection to the Retriever
    retriever_channel = grpc.aio.insecure_channel(settings.RETRIEVER_HOST)
    AgentState.retriever_client = retriever_pb2_grpc.RetrieverServiceStub(retriever_channel)
    log.info(f"[{settings.APP_NAME}] Connected to Retriever at {settings.RETRIEVER_HOST}")

    AgentState.ticket_store = PostgresTicketStore(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
    AgentState.ticket_store.ping()
    log.info(
        f"[{settings.APP_NAME}] Connected to Postgres at "
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    # 2. Start the Agent's own gRPC Server (async)
    server = grpc.aio.server()
    chatbot_pb2_grpc.add_AgentServiceServicer_to_server(AgentServicer(), server)

    listen_addr = f"[::]:{settings.PORT}"
    server.add_insecure_port(listen_addr)
    await server.start()

    log.info(f"[{settings.APP_NAME}] Server started, listening on {listen_addr}")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
