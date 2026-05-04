"""Re-embed every chunk in a Qdrant collection using the currently
configured embedder.

Run after changing embedding model parameters (notably the e5
"query: " / "passage: " prefixes) so that stored vectors stay aligned
with how queries are now embedded.

Usage (from inside the retriever container, working dir is the retriever
service root):

    python -m scripts.reindex_collection --collection manual

Multiple collections:

    python -m scripts.reindex_collection --collection manual --collection disaster

All non-system collections:

    python -m scripts.reindex_collection --all
"""
from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

# Allow `python scripts/reindex_collection.py` from the service root in
# addition to `python -m scripts.reindex_collection`.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from db.qdrant import QdrantDB  # noqa: E402
from logger import log  # noqa: E402


def reindex(qdrant_db: QdrantDB, theme_name: str, batch_size: int) -> int:
    log.info(f"[{theme_name}] fetching all documents...")
    data = qdrant_db.get_all_documents(theme_name)
    documents = data["documents"]
    metadatas = data["metadatas"]

    if not documents:
        log.warning(f"[{theme_name}] no documents found, skipping.")
        return 0

    original_ids: list[str] = []
    cleaned_metadatas: list[dict] = []
    for meta in metadatas:
        doc_id = meta.get("doc_id") or str(uuid.uuid4())
        original_ids.append(str(doc_id))
        cleaned_metadatas.append({k: v for k, v in meta.items() if k != "doc_id"})

    total = len(documents)
    log.info(f"[{theme_name}] re-embedding and upserting {total} chunks (batch={batch_size})...")
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        qdrant_db.add_documents(
            theme_name,
            documents[start:end],
            cleaned_metadatas[start:end],
            original_ids[start:end],
        )
        log.info(f"[{theme_name}] upserted {end}/{total}")

    log.success(f"[{theme_name}] re-index complete: {total} chunks.")
    return total


def list_collections(qdrant_db: QdrantDB) -> list[str]:
    return [c.name for c in qdrant_db.client.get_collections().collections]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--collection",
        action="append",
        help="Collection name to re-index (repeat for multiple).",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Re-index every Qdrant collection.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Number of chunks to re-embed and upsert per batch (default: 128).",
    )
    args = parser.parse_args()

    qdrant_db = QdrantDB()

    if args.all:
        collections = list_collections(qdrant_db)
        if not collections:
            log.warning("No collections found in Qdrant.")
            return 0
    else:
        collections = args.collection

    log.info(f"Re-indexing collections: {collections}")
    grand_total = 0
    for name in collections:
        grand_total += reindex(qdrant_db, name, args.batch_size)

    log.success(f"Done. Re-indexed {grand_total} chunks across {len(collections)} collection(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
