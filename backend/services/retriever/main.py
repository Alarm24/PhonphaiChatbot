from concurrent import futures

import grpc
import retriever_pb2_grpc
from config import get_settings
from logger import log
from server import RetrieverServicer


def serve():
    settings = get_settings()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    retriever_pb2_grpc.add_RetrieverServiceServicer_to_server(RetrieverServicer(), server)

    listen_addr = f"[::]:{settings.PORT}"
    server.add_insecure_port(listen_addr)
    server.start()

    log.info(f"[{settings.APP_NAME}] Server started, listening on {listen_addr}")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
