from concurrent import futures

import chatbot_pb2_grpc
import grpc
import retriever_pb2_grpc
from config import get_settings
from logger import log
from server import AgentServicer
from state import AgentState


def serve():
    settings = get_settings()

    # 1. Establish persistent connection to the Retriever
    retriever_channel = grpc.insecure_channel(settings.RETRIEVER_HOST)
    AgentState.retriever_client = retriever_pb2_grpc.RetrieverServiceStub(retriever_channel)
    log.info(f"[{settings.APP_NAME}] Connected to Retriever at {settings.RETRIEVER_HOST}")

    # 2. Start the Agent's own gRPC Server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chatbot_pb2_grpc.add_AgentServiceServicer_to_server(AgentServicer(), server)

    listen_addr = f"[::]:{settings.PORT}"
    server.add_insecure_port(listen_addr)
    server.start()

    log.info(f"[{settings.APP_NAME}] Server started, listening on {listen_addr}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
