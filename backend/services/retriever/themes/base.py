import numpy as np
from config import get_settings
from db.chroma import ChromaDB
from logger import log
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


class BaseTheme:
    _shared_reranker = None

    def __init__(self, theme_name):
        self.theme_name = theme_name
        self.chroma = ChromaDB()
        self.settings = get_settings()

        # Load the reranker once and share it across all theme instances.
        if BaseTheme._shared_reranker is None:
            log.info(f"Loading Reranker Model: {self.settings.RERANK_MODEL_NAME}")
            BaseTheme._shared_reranker = CrossEncoder(
                self.settings.RERANK_MODEL_NAME,
                device="cuda",
            )
        self.reranker = BaseTheme._shared_reranker

        # 2. Initialize variables for local BM25 indexing
        self.corpus_docs = []
        self.corpus_ids = []
        self.corpus_metadata = []
        self.bm25 = None
        self._sync_bm25_index()

    def _tokenize(self, text):
        """Simple tokenizer for BM25 keyword matching"""
        return text.lower().split()

    def _sync_bm25_index(self):
        """Pulls all docs from Chroma and builds an in-memory BM25 index."""
        data = self.chroma.get_all_documents(self.theme_name)
        if data and data.get("documents"):
            self.corpus_docs = data["documents"]
            self.corpus_ids = data["ids"]
            self.corpus_metadata = data["metadatas"]

            tokenized_corpus = [self._tokenize(doc) for doc in self.corpus_docs]
            self.bm25 = BM25Okapi(tokenized_corpus)
            log.info(f"✅ BM25 Index synced with {len(self.corpus_docs)} documents.")
        else:
            self.bm25 = None

    def search(self, query, limit=None, fetch_k=None):
        """Hybrid Search (Dense + Sparse) with Reciprocal Rank Fusion and Reranking"""

        # Override with config values if not explicitly passed
        limit = limit or self.settings.RERANK_TOP_K
        fetch_k = fetch_k or self.settings.RETRIEVAL_K

        # --- 1. DENSE RETRIEVAL (ChromaDB) ---
        dense_results = self.chroma.search(self.theme_name, query, limit=fetch_k)
        dense_docs = []
        if dense_results["documents"]:
            for i in range(len(dense_results["documents"][0])):
                dense_docs.append(
                    {
                        "id": dense_results["ids"][0][i],
                        "content": dense_results["documents"][0][i],
                        "metadata": dense_results["metadatas"][0][i],
                    }
                )

        # --- 2. SPARSE RETRIEVAL (BM25) ---
        sparse_docs = []
        if self.bm25:
            tokenized_query = self._tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)

            top_n_idx = np.argsort(bm25_scores)[::-1][:fetch_k]
            for idx in top_n_idx:
                if bm25_scores[idx] > 0:
                    sparse_docs.append(
                        {
                            "id": self.corpus_ids[idx],
                            "content": self.corpus_docs[idx],
                            "metadata": self.corpus_metadata[idx],
                        }
                    )

        # --- 3. WEIGHTED RECIPROCAL RANK FUSION (RRF) ---
        rrf_map = {}
        k_rrf = 60

        # 1. Apply Semantic (Dense) Weight
        semantic_weight = self.settings.HYBRID_SEMANTIC_WEIGHT
        for rank, doc in enumerate(dense_docs):
            # Calculate base RRF and multiply by the semantic weight
            score = (1 / (k_rrf + rank + 1)) * semantic_weight
            rrf_map[doc["id"]] = {"doc": doc, "rrf_score": score}

        # 2. Apply Keyword (BM25) Weight
        bm25_weight = self.settings.HYBRID_BM25_WEIGHT
        for rank, doc in enumerate(sparse_docs):
            # Calculate base RRF and multiply by the BM25 weight
            score_addition = (1 / (k_rrf + rank + 1)) * bm25_weight

            # Add to existing score if the document was found in both searches
            if doc["id"] in rrf_map:
                rrf_map[doc["id"]]["rrf_score"] += score_addition
            else:
                rrf_map[doc["id"]] = {"doc": doc, "rrf_score": score_addition}

        fused_results = sorted(rrf_map.values(), key=lambda x: x["rrf_score"], reverse=True)
        candidates = [item["doc"] for item in fused_results[:fetch_k]]

        if not candidates:
            return []

        # --- 4. RERANKING (Cross-Encoder) ---
        pairs = [[query, doc["content"]] for doc in candidates]
        rerank_scores = self.reranker.predict(pairs)

        for idx, doc in enumerate(candidates):
            doc["score"] = float(rerank_scores[idx])

        # Final sort based on the Cross-Encoder's score
        final_results = sorted(candidates, key=lambda x: x["score"], reverse=True)

        parsed_results = []
        for doc in final_results[:limit]:  # Cut off exactly at RERANK_TOP_K limit
            parsed_results.append(
                {"content": doc["content"], "metadata": doc["metadata"], "score": doc["score"]}
            )

        return parsed_results

    def add_knowledge(self, chunks_data, filename):
        """Indexes data. Accepts either a list of strings OR a list of dictionaries with metadata."""
        texts = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks_data):
            if isinstance(chunk, str):
                # Fallback for plain text arrays (LangChain text splitter)
                texts.append(chunk)
                metadatas.append({"source": filename, "theme": self.theme_name})
            else:
                # Handling Gemini's structured dictionary output
                texts.append(chunk["content"])
                meta = chunk.get("metadata", {})
                meta["source"] = filename  # Ensure source is always set
                meta["theme"] = self.theme_name
                metadatas.append(meta)

            ids.append(f"{filename}_chunk_{i}")

        self.chroma.add_documents(self.theme_name, texts, metadatas, ids)
        self._sync_bm25_index()

    def delete_knowledge(self, filename: str):
        success = False
        try:
            collection = self.chroma.client.get_collection(name=self.theme_name)
            collection.delete(where={"source": filename})
            log.info(f"Deleted vector chunks for {filename} from {self.theme_name}")
            success = True
        except Exception as e:
            log.error(f"Chroma delete error: {e}")

        if success:
            self._sync_bm25_index()

        return success
