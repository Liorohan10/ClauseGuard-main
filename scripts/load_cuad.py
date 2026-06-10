#!/usr/bin/env python3
"""Load CUADv1 examples into Elasticsearch for hybrid retrieval."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force transformers to use the PyTorch path and skip TensorFlow imports.
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from clauseguard.config import settings
from clauseguard.models.clause import ClauseType
from clauseguard.services.elasticsearch_service import ElasticsearchService
from clauseguard.services.embedding_service import EmbeddingService


CUAD_LABEL_MAP: list[tuple[str, ClauseType]] = [
    ("indemn", ClauseType.INDEMNITY),
    ("liabil", ClauseType.LIABILITY_CAP),
    ("cap on liability", ClauseType.LIABILITY_CAP),
    ("uncapped liability", ClauseType.LIABILITY_CAP),
    ("termination", ClauseType.TERMINATION),
    ("renewal", ClauseType.TERMINATION),
    ("confidential", ClauseType.CONFIDENTIALITY),
    ("non-disclosure", ClauseType.CONFIDENTIALITY),
    ("ip ownership", ClauseType.IP_ASSIGNMENT),
    ("ownership assignment", ClauseType.IP_ASSIGNMENT),
    ("license", ClauseType.IP_ASSIGNMENT),
    ("governing law", ClauseType.GOVERNING_LAW),
    ("data protection", ClauseType.DATA_PROTECTION),
    ("privacy", ClauseType.DATA_PROTECTION),
    ("force majeure", ClauseType.FORCE_MAJEURE),
]


def infer_clause_type(label: str, question: str) -> ClauseType:
    haystack = f"{label} {question}".lower()
    for needle, clause_type in CUAD_LABEL_MAP:
        if needle in haystack:
            return clause_type
    return ClauseType.OTHER


def build_example(title: str, paragraph_index: int, context: str, qas: dict, answer: dict) -> dict:
    answer_text = (answer.get("text") or "").strip()
    answer_start = int(answer.get("answer_start", 0) or 0)
    answer_end = answer_start + len(answer_text)
    excerpt_start = max(0, answer_start - 250)
    excerpt_end = min(len(context), answer_end + 250)
    context_excerpt = context[excerpt_start:excerpt_end].strip()
    qas_id = qas.get("id", "")
    cuad_label = qas_id.split("__", 1)[-1] if "__" in qas_id else qas_id
    clause_type = infer_clause_type(cuad_label, qas.get("question", ""))

    searchable_text = "\n".join(
        part
        for part in [
            title,
            cuad_label,
            qas.get("question", ""),
            answer_text,
            context_excerpt,
        ]
        if part
    )

    return {
        "example_id": f"{qas_id}::{answer_start}",
        "source_contract_id": title,
        "title": title,
        "paragraph_index": paragraph_index,
        "qas_id": qas_id,
        "cuad_label": cuad_label,
        "clause_type": clause_type.value,
        "question": qas.get("question", ""),
        "answer_text": answer_text,
        "answer_start": answer_start,
        "answer_end": answer_end,
        "context": context,
        "context_excerpt": context_excerpt,
        "is_impossible": bool(qas.get("is_impossible", False)),
        "text": searchable_text,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="CUADv1.json", help="Path to CUADv1.json")
    args = parser.parse_args()

    dataset_path = Path(args.path)
    if not dataset_path.exists():
        raise FileNotFoundError(dataset_path)

    with dataset_path.open("r", encoding="utf-8") as handle:
        dataset = json.load(handle)

    documents: list[dict] = []
    for entry in dataset.get("data", []):
        title = entry.get("title", "")
        for paragraph_index, paragraph in enumerate(entry.get("paragraphs", [])):
            context = paragraph.get("context", "")
            for qas in paragraph.get("qas", []):
                if qas.get("is_impossible", False):
                    continue
                for answer in qas.get("answers", []):
                    if not (answer.get("text") or "").strip():
                        continue
                    documents.append(build_example(title, paragraph_index, context, qas, answer))

    if not documents:
        print("No CUAD documents found to index.")
        return

    embedding_service = EmbeddingService(settings.embedding_model)
    es_service = ElasticsearchService()
    try:
        await es_service.ensure_indices()

        texts = [doc["text"] for doc in documents]
        embeddings = embedding_service.encode_batch(texts)
        for doc, embedding in zip(documents, embeddings):
            doc["text_embedding"] = embedding

        indexed = await es_service.bulk_index_cuad_examples(documents)
    finally:
        await es_service.close()

    print(f"Indexed {indexed} CUAD examples into {settings.es_cuad_index}.")


if __name__ == "__main__":
    asyncio.run(main())
