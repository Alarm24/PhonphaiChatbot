from __future__ import annotations

import argparse
from collections import Counter

from db.qdrant import QdrantDB
from logger import log


def list_sources(db: QdrantDB, collection_name: str) -> Counter[str]:
    collection_name = collection_name.lower()
    counter: Counter[str] = Counter()
    offset = None

    while True:
        records, offset = db.client.scroll(
            collection_name=collection_name,
            limit=256,
            offset=offset,
            with_payload=True,
        )
        if not records:
            break

        for record in records:
            payload = dict(record.payload or {})
            counter[payload.get("source") or "unknown"] += 1

        if offset is None:
            break

    return counter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List source filenames and chunk counts in a Qdrant collection."
    )
    parser.add_argument(
        "--collection",
        choices=["manual", "disaster"],
        default="manual",
        help="Collection to inspect.",
    )
    parser.add_argument(
        "--contains",
        default="",
        help="Optional case-insensitive substring filter for source names.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = QdrantDB()
    counter = list_sources(db, args.collection)
    contains = args.contains.lower().strip()

    rows = [
        (source, count)
        for source, count in counter.most_common()
        if not contains or contains in source.lower()
    ]

    log.info(f"Found {len(rows)} sources in collection '{args.collection}'.")
    for source, count in rows:
        print(f"{count}\t{source}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
