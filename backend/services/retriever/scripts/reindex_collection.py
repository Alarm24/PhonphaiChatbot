from __future__ import annotations

import argparse
from typing import Iterable

from db.qdrant import QdrantDB
from logger import log
from qdrant_client.http import models


def _batched(items: list[dict], batch_size: int) -> Iterable[list[dict]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def _load_collection(db: QdrantDB, collection_name: str) -> list[dict]:
    collection_name = collection_name.lower()
    records = []
    offset = None

    while True:
        batch, offset = db.client.scroll(
            collection_name=collection_name,
            limit=256,
            offset=offset,
            with_payload=True,
        )
        if not batch:
            break

        for record in batch:
            payload = dict(record.payload or {})
            content = payload.get("content", "")
            if not content:
                continue
            records.append(
                {
                    "point_id": record.id,
                    "content": content,
                    "payload": payload,
                }
            )

        if offset is None:
            break

    return records


def reindex_collection(db: QdrantDB, collection_name: str, batch_size: int) -> int:
    records = _load_collection(db, collection_name)
    if not records:
        log.warning(f"No records found in collection '{collection_name}'.")
        return 0

    total = 0
    for batch in _batched(records, batch_size):
        vectors = db._embed_documents([item["content"] for item in batch])
        points = [
            models.PointStruct(
                id=item["point_id"],
                vector=vectors[index],
                payload=item["payload"],
            )
            for index, item in enumerate(batch)
        ]
        db.client.upsert(collection_name=collection_name, points=points, wait=True)
        total += len(points)
        log.info(f"Reindexed {total}/{len(records)} points in '{collection_name}'.")

    return total


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-embed existing Qdrant points with the current embedding settings."
    )
    parser.add_argument(
        "--collection",
        choices=["manual", "disaster"],
        help="Collection to reindex.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Reindex all supported knowledge collections.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding/upsert batch size.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.all and not args.collection:
        raise SystemExit("Provide --collection manual|disaster or --all.")

    collections = ["manual", "disaster"] if args.all else [args.collection]
    db = QdrantDB()
    for collection in collections:
        count = reindex_collection(db, collection, max(args.batch_size, 1))
        log.info(f"Finished '{collection}': {count} points reindexed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
