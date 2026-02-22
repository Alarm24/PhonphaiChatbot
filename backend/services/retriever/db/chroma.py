import chromadb
from chromadb.utils import embedding_functions
from logger import log
from tenacity import retry, stop_after_attempt, wait_fixed


class ChromaDB:
    def __init__(self, host="chroma"):
        self.host = host
        self.client = self._connect()
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

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
