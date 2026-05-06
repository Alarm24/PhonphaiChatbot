from __future__ import annotations

import argparse
import hashlib
import re
from collections import defaultdict

from db.qdrant import QdrantDB
from logger import log
from qdrant_client.http import models

ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize_content(text: str) -> str:
    normalized = (text or "").lower()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[^\w\u0e00-\u0e7f]+", "", normalized)
    return normalized


def _content_key(text: str, window_size: int) -> str:
    normalized = _normalize_content(text)
    if window_size > 0 and len(normalized) > window_size:
        normalized = normalized[:window_size]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _source_priority(source: str, preferred_source: str) -> tuple[int, int, str]:
    source_lower = (source or "").lower()
    preferred_lower = preferred_source.lower()

    if preferred_lower in source_lower:
        priority = 0
    elif "user manual" in source_lower:
        priority = 1
    else:
        priority = 2

    return priority, len(source_lower), source_lower


def _load_records(db: QdrantDB, collection_name: str) -> list[dict]:
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
            content = payload.get("content") or ""
            if not content.strip():
                continue
            records.append(
                {
                    "point_id": record.id,
                    "source": payload.get("source") or "unknown",
                    "page": payload.get("page") or "",
                    "content": content,
                    "doc_id": payload.get("doc_id") or str(record.id),
                }
            )

        if offset is None:
            break

    return records


def find_duplicate_groups(
    records: list[dict],
    preferred_source: str,
    min_chars: int,
    window_size: int,
) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        normalized = _normalize_content(record["content"])
        if len(normalized) < min_chars:
            continue
        buckets[_content_key(record["content"], window_size)].append(record)

    duplicate_groups = []
    for key, group_records in buckets.items():
        if len(group_records) < 2:
            continue

        sorted_group = sorted(
            group_records,
            key=lambda item: _source_priority(item["source"], preferred_source),
        )
        keep = sorted_group[0]
        delete = sorted_group[1:]
        duplicate_groups.append(
            {
                "key": key,
                "keep": keep,
                "delete": delete,
            }
        )

    return duplicate_groups


def delete_points(db: QdrantDB, collection_name: str, point_ids: list[str]) -> None:
    if not point_ids:
        return
    db.client.delete(
        collection_name=collection_name,
        points_selector=models.PointIdsList(points=point_ids),
        wait=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove duplicate Qdrant chunks while preferring User Manual sources."
    )
    parser.add_argument(
        "--collection",
        choices=["manual", "disaster"],
        default="manual",
        help="Collection to deduplicate.",
    )
    parser.add_argument(
        "--preferred-source",
        default="User Manual",
        help="Source substring to keep when duplicates exist.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=220,
        help="Minimum normalized chunk length eligible for dedupe.",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=0,
        help="Only compare the first N normalized chars. 0 compares full normalized content.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicate points. Without this flag, only reports what would happen.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = QdrantDB()
    collection_name = args.collection.lower()
    records = _load_records(db, collection_name)
    duplicate_groups = find_duplicate_groups(
        records=records,
        preferred_source=args.preferred_source,
        min_chars=max(args.min_chars, 1),
        window_size=max(args.window_size, 0),
    )

    delete_ids = [
        str(record["point_id"])
        for group in duplicate_groups
        for record in group["delete"]
    ]

    log.info(
        f"Scanned {len(records)} chunks in '{collection_name}'. "
        f"Found {len(duplicate_groups)} duplicate groups and {len(delete_ids)} deletable chunks."
    )

    for group in duplicate_groups[:25]:
        keep = group["keep"]
        delete_sources = sorted({record["source"] for record in group["delete"]})
        log.info(
            f"Keep source='{keep['source']}' page='{keep['page']}' "
            f"delete_sources={delete_sources}"
        )

    if len(duplicate_groups) > 25:
        log.info(f"... skipped logging {len(duplicate_groups) - 25} more duplicate groups.")

    if not args.apply:
        log.warning("Dry-run only. Re-run with --apply to delete duplicate chunks.")
        return 0

    delete_points(db, collection_name, delete_ids)
    log.info(f"Deleted {len(delete_ids)} duplicate chunks from '{collection_name}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
