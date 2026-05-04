from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from config import get_settings
from db.qdrant import QdrantDB
from langchain_text_splitters import RecursiveCharacterTextSplitter
from logger import log
from qdrant_client.http import models


def _safe_id_part(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)[:80]


def _load_records(db: QdrantDB, collection_name: str) -> list[dict]:
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
            content = (payload.get("content") or "").strip()
            source = payload.get("source") or "unknown"
            if not content:
                continue
            records.append(
                {
                    "content": content,
                    "source": source,
                    "metadata": payload,
                    "doc_id": payload.get("doc_id") or str(record.id),
                }
            )

        if offset is None:
            break

    return records


def _split_source_records(
    source: str,
    records: list[dict],
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[list[str], list[dict], list[str]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n# ",
            "\n## ",
            "\n* ",
            "\n- ",
            "\n",
            " ",
            "",
        ],
    )

    texts: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    source_part = _safe_id_part(Path(source).stem or source)

    sorted_records = sorted(records, key=lambda item: str(item["doc_id"]))
    for record_index, record in enumerate(sorted_records):
        chunks = splitter.split_text(record["content"])
        for chunk_index, chunk in enumerate(chunks):
            clean_chunk = chunk.strip()
            if not clean_chunk:
                continue

            metadata = dict(record["metadata"])
            metadata["source"] = source
            metadata["rechunked"] = True
            metadata["parent_doc_id"] = str(record["doc_id"])
            metadata["chunk_part"] = chunk_index
            metadata.pop("content", None)
            metadata.pop("doc_id", None)

            texts.append(clean_chunk)
            metadatas.append(metadata)
            ids.append(f"{source_part}_rechunk_{record_index}_{chunk_index}")

    return texts, metadatas, ids


def rechunk_collection(
    db: QdrantDB,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int,
    source_filter: str | None = None,
) -> int:
    records = _load_records(db, collection_name)
    grouped_records: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        source = str(record["source"])
        if source_filter and source_filter != source:
            continue
        grouped_records[source].append(record)

    if not grouped_records:
        log.warning(f"No records found to rechunk in collection '{collection_name}'.")
        return 0

    total_chunks = 0
    for source, source_records in sorted(grouped_records.items()):
        texts, metadatas, ids = _split_source_records(
            source=source,
            records=source_records,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        if not texts:
            continue

        vectors = db._embed_documents(texts)
        points = []
        for index, text in enumerate(texts):
            payload = dict(metadatas[index])
            payload["content"] = text
            payload["doc_id"] = ids[index]
            points.append(
                models.PointStruct(
                    id=db._to_qdrant_point_id(collection_name, ids[index]),
                    vector=vectors[index],
                    payload=payload,
                )
            )

        db.delete_documents(collection_name, source)
        db.client.upsert(collection_name=collection_name, points=points, wait=True)
        total_chunks += len(texts)
        log.info(
            f"Rechunked '{source}' from {len(source_records)} records to {len(texts)} chunks."
        )

    log.info(f"Finished rechunking '{collection_name}': {total_chunks} chunks.")
    return total_chunks


def parse_args() -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Split existing Qdrant documents into smaller chunks without re-parsing PDFs."
    )
    parser.add_argument(
        "--collection",
        choices=["manual", "disaster"],
        default="manual",
        help="Collection to rechunk.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Optional exact source filename to rechunk.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=settings.CHUNK_SIZE,
        help="Target chunk size in characters.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=settings.CHUNK_OVERLAP,
        help="Chunk overlap in characters.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = QdrantDB()
    rechunk_collection(
        db=db,
        collection_name=args.collection,
        chunk_size=max(args.chunk_size, 100),
        chunk_overlap=max(min(args.chunk_overlap, args.chunk_size // 2), 0),
        source_filter=args.source,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
