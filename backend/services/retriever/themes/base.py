from db.chroma import ChromaDB
from logger import log


class BaseTheme:
    def __init__(self, theme_name):
        self.theme_name = theme_name
        self.chroma = ChromaDB()

    def search(self, query, limit=5):
        """Common search logic"""
        results = self.chroma.search(self.theme_name, query, limit)

        # Normalize Chroma's weird return format
        parsed_results = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                parsed_results.append(
                    {
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "score": results["distances"][0][i] if results["distances"] else 0.0,
                    }
                )
        return parsed_results

    def add_knowledge(self, text_chunks, filename):
        """Common indexing logic"""
        # Create unique IDs for chunks
        ids = [f"{filename}_chunk_{i}" for i in range(len(text_chunks))]
        metadatas = [{"source": filename, "theme": self.theme_name} for _ in text_chunks]

        self.chroma.add_documents(self.theme_name, text_chunks, metadatas, ids)

    def delete_knowledge(self, filename: str):
        """Deletes all vectorized chunks associated with a specific file"""
        try:
            collection = self.chroma.client.get_collection(name=self.theme_name)
            # Delete where metadata 'source' matches the filename
            collection.delete(where={"source": filename})
            log.info(f"Deleted vector chunks for {filename} from {self.theme_name}")
            return True
        except Exception as e:
            log.error(f"Chroma delete error: {e}")
            return False
