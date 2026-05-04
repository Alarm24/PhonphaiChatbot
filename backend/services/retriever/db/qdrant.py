from __future__ import annotations

import threading
import uuid

from config import get_settings
from langchain_huggingface import HuggingFaceEmbeddings
from logger import log
from qdrant_client import QdrantClient
from qdrant_client.http import models
from tenacity import retry, stop_after_attempt, wait_fixed

UUID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


class QdrantDB:
    _shared_embeddings = None
    _shared_embedding_model_name = None
    _embedding_lock = threading.Lock()

    def __init__(self, host: str | None = None, port: int | None = None):
        settings = get_settings()
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT

        self.embedding_model_name = settings.EMBEDDING_MODEL_NAME
        self.uses_e5_prefixes = "e5" in self.embedding_model_name.lower()
        self.embeddings = self._get_embeddings(self.embedding_model_name)
        self.vector_size = len(self._embed_query("dimension probe"))
        self.client = self._connect()

    @classmethod
    def _get_embeddings(cls, model_name: str):
        if cls._shared_embeddings is None or cls._shared_embedding_model_name != model_name:
            with cls._embedding_lock:
                if cls._shared_embeddings is None or cls._shared_embedding_model_name != model_name:
                    log.info(f"Loading Embedding Model: {model_name} on cpu")
                    cls._shared_embeddings = HuggingFaceEmbeddings(
                        model_name=model_name,
                        model_kwargs={"device": "cpu"},
                    )
                    cls._shared_embedding_model_name = model_name
        return cls._shared_embeddings

    def _prefix_for_e5(self, text: str, prefix: str) -> str:
        if not self.uses_e5_prefixes:
            return text
        normalized = text.lstrip()
        if normalized.startswith(prefix):
            return text
        return f"{prefix}{text}"

    def _embed_query(self, query_text: str):
        with self._embedding_lock:
            return self.embeddings.embed_query(self._prefix_for_e5(query_text, "query: "))

    def _embed_documents(self, documents):
        with self._embedding_lock:
            return self.embeddings.embed_documents(
                [self._prefix_for_e5(document, "passage: ") for document in documents]
            )

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(3))
    def _connect(self):
        try:
            log.info(f"Attempting to connect to Qdrant at {self.host}:{self.port}...")
            client = QdrantClient(host=self.host, port=self.port, prefer_grpc=False)
            client.get_collections()
            log.success("Successfully connected to Qdrant!")
            return client
        except Exception as exc:
            log.warning(f"Qdrant not ready yet. Exception: {type(exc).__name__}. Retrying...")
            raise exc

    def _ensure_collection(self, theme_name: str):
        collection_name = theme_name.lower()
        collections = self.client.get_collections().collections
        if any(item.name == collection_name for item in collections):
            return collection_name

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        return collection_name

    def _to_qdrant_point_id(self, theme_name: str, source_id: str) -> str:
        return str(uuid.uuid5(UUID_NAMESPACE, f"{theme_name}:{source_id}"))

    def add_documents(self, theme_name, documents, metadatas, ids):
        collection_name = self._ensure_collection(theme_name)
        vectors = self._embed_documents(documents)
        points = []
        for idx, document in enumerate(documents):
            point_id = str(ids[idx]) if idx < len(ids) else str(uuid.uuid4())
            payload = dict(metadatas[idx]) if idx < len(metadatas) else {}
            payload["content"] = document
            payload["doc_id"] = point_id
            points.append(
                models.PointStruct(
                    id=self._to_qdrant_point_id(collection_name, point_id),
                    vector=vectors[idx],
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=collection_name, points=points, wait=True)

    def _query_points(self, collection_name: str, query_vector: list[float], limit: int):
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            return response.points if hasattr(response, "points") else response

        if hasattr(self.client, "search"):
            return self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )

        if hasattr(self.client, "search_points"):
            response = self.client.search_points(
                collection_name=collection_name,
                vector=query_vector,
                limit=limit,
                with_payload=True,
            )
            return response.result if hasattr(response, "result") else response

        raise AttributeError(
            "Qdrant client does not support query_points, search, or search_points"
        )

    def search(self, theme_name, query_text, limit=3):
        collection_name = self._ensure_collection(theme_name)
        query_vector = self._embed_query(query_text)
        results = self._query_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
        )

        documents = []
        ids = []
        metadatas = []
        for point in results:
            payload = dict(point.payload or {})
            documents.append(payload.get("content", ""))
            ids.append(str(point.id))
            payload.pop("content", None)
            metadatas.append(payload)

        return {
            "documents": [documents],
            "ids": [ids],
            "metadatas": [metadatas],
        }

    def get_all_documents(self, theme_name):
        collection_name = self._ensure_collection(theme_name)
        all_documents = []
        all_ids = []
        all_metadatas = []
        offset = None

        while True:
            records, offset = self.client.scroll(
                collection_name=collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
            )
            if not records:
                break

            for record in records:
                payload = dict(record.payload or {})
                all_documents.append(payload.get("content", ""))
                all_ids.append(str(record.id))
                payload.pop("content", None)
                all_metadatas.append(payload)

            if offset is None:
                break

        return {
            "documents": all_documents,
            "ids": all_ids,
            "metadatas": all_metadatas,
        }

    def delete_documents(self, theme_name: str, source_filename: str):
        collection_name = self._ensure_collection(theme_name)
        self.client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source",
                            match=models.MatchValue(value=source_filename),
                        )
                    ]
                )
            ),
            wait=True,
        )
