import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from config import get_settings
from langchain_huggingface import HuggingFaceEmbeddings
from logger import log
from tenacity import retry, stop_after_attempt, wait_fixed


class LangChainEmbeddingAdapter(EmbeddingFunction):
    """Adapts a LangChain Embedding model to Chroma's required EmbeddingFunction interface."""

    def __init__(self, lc_embeddings):
        self.lc_embeddings = lc_embeddings

    def __call__(self, input: Documents) -> Embeddings:
        return self.lc_embeddings.embed_documents(input)


class ChromaDB:
    def __init__(self, host="chroma"):
        self.host = host

        settings = get_settings()

        lc_ef = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL_NAME,
            model_kwargs={'device': 'cuda'} 
        )
        self.ef = LangChainEmbeddingAdapter(lc_ef)

        self.client = self._connect()

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(3))
    def _connect(self):
        try:
            log.info(f"Attempting to connect to ChromaDB at {self.host}:8000...")
            client = chromadb.HttpClient(host=self.host, port=8000)

            # Ping the database to ensure it's actually alive before returning
            client.heartbeat()

            log.success("✅ Successfully connected to ChromaDB!")
            return client
        except Exception as e:
            log.warning(f"⏳ ChromaDB not ready yet. Exception: {type(e).__name__}. Retrying...")
            raise e

    def get_collection(self, theme_name):
        """Get or create a collection for a specific theme"""
        return self.client.get_or_create_collection(
            name=theme_name.lower(),  # e.g., "remedy", "disaster"
            embedding_function=self.ef,
        )

    def add_documents(self, theme_name, documents, metadatas, ids):
        collection = self.get_collection(theme_name)
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

    def search(self, theme_name, query_text, limit=3):
        collection = self.get_collection(theme_name)
        results = collection.query(query_texts=[query_text], n_results=limit)
        return results

    def get_all_documents(self, theme_name):
        """Fetches all documents to sync the BM25 index"""
        collection = self.get_collection(theme_name)
        return collection.get()
