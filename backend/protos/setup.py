from setuptools import setup

setup(
    name="phonphai-protos",
    version="1.0.0",
    description="Shared gRPC protobufs for Phonphai services",
    py_modules=[
        "chatbot_pb2",
        "chatbot_pb2_grpc",
        "retriever_pb2",
        "retriever_pb2_grpc",
    ],
    install_requires=["grpcio>=1.60.0", "protobuf>=4.25.3"],
)
