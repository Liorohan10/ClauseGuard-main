import logging
import json

from elasticsearch import AsyncElasticsearch, NotFoundError

from clauseguard.config import settings

logger = logging.getLogger(__name__)

CONTRACTS_MAPPINGS = {
    "properties": {
        "contract_id": {"type": "keyword"},
        "filename": {"type": "keyword"},
        "upload_timestamp": {"type": "date"},
        "num_pages": {"type": "integer"},
        "num_clauses": {"type": "integer"},
        "clause_types_found": {"type": "keyword"},
        "text_length": {"type": "integer"},
        "latest_reviewed_at": {"type": "date"},
        "latest_review_score": {"type": "integer"},
        "latest_review_summary": {"type": "text"},
        "latest_review_id": {"type": "keyword"},
        "latest_review_finding_count": {"type": "integer"},
    }
}

CUAD_SETTINGS = {
    "analysis": {
        "analyzer": {
            "legal_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "stop", "snowball"],
            }
        }
    }
}

CUAD_MAPPINGS = {
    "properties": {
        "example_id": {"type": "keyword"},
        "source_contract_id": {"type": "keyword"},
        "title": {"type": "keyword"},
        "paragraph_index": {"type": "integer"},
        "qas_id": {"type": "keyword"},
        "cuad_label": {"type": "keyword"},
        "clause_type": {"type": "keyword"},
        "question": {"type": "text", "analyzer": "legal_analyzer"},
        "answer_text": {"type": "text", "analyzer": "legal_analyzer"},
        "context": {"type": "text", "analyzer": "legal_analyzer"},
        "context_excerpt": {"type": "text", "analyzer": "legal_analyzer"},
        "text": {"type": "text", "analyzer": "legal_analyzer"},
        "text_embedding": {
            "type": "dense_vector",
            "dims": 384,
            "index": True,
            "similarity": "cosine",
        },
        "answer_start": {"type": "integer"},
        "answer_end": {"type": "integer"},
        "is_impossible": {"type": "boolean"},
    }
}

REVIEWS_MAPPINGS = {
    "properties": {
        "review_id": {"type": "keyword"},
        "contract_id": {"type": "keyword"},
        "contract_filename": {"type": "keyword"},
        "reviewed_at": {"type": "date"},
        "contract_safety_score": {"type": "integer"},
        "summary": {"type": "text"},
        "findings_count": {"type": "integer"},
        "review": {"type": "object", "enabled": True},
    }
}

CLAUSES_SETTINGS = {
    "analysis": {
        "analyzer": {
            "legal_analyzer": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "stop", "snowball"],
            }
        }
    }
}

CLAUSES_MAPPINGS = {
    "properties": {
        "clause_id": {"type": "keyword"},
        "contract_id": {"type": "keyword"},
        "clause_type": {"type": "keyword"},
        "text": {"type": "text", "analyzer": "legal_analyzer"},
        "text_embedding": {
            "type": "dense_vector",
            "dims": 384,
            "index": True,
            "similarity": "cosine",
        },
        "section_number": {"type": "keyword"},
        "page_number": {"type": "integer"},
        "char_offset_start": {"type": "integer"},
        "char_offset_end": {"type": "integer"},
        "confidence": {"type": "float"},
    }
}


class ElasticsearchService:
    """Async Elasticsearch client for index management, CRUD, and hybrid search."""

    def __init__(self, es_url: str | None = None):
        self.es = AsyncElasticsearch(es_url or settings.elasticsearch_url)
        self.contracts_index = settings.es_contracts_index
        self.clauses_index = settings.es_clauses_index
        self.cuad_index = settings.es_cuad_index
        self.reviews_index = f"{self.contracts_index}-reviews"

    async def ensure_indices(self) -> None:
        """Create indices if they don't exist."""
        if not await self.es.indices.exists(index=self.contracts_index):
            await self.es.indices.create(
                index=self.contracts_index, mappings=CONTRACTS_MAPPINGS
            )
            logger.info("Created index: %s", self.contracts_index)

        if not await self.es.indices.exists(index=self.clauses_index):
            await self.es.indices.create(
                index=self.clauses_index,
                settings=CLAUSES_SETTINGS,
                mappings=CLAUSES_MAPPINGS,
            )
            logger.info("Created index: %s", self.clauses_index)

        if not await self.es.indices.exists(index=self.cuad_index):
            await self.es.indices.create(
                index=self.cuad_index,
                settings=CUAD_SETTINGS,
                mappings=CUAD_MAPPINGS,
            )
            logger.info("Created index: %s", self.cuad_index)

        if not await self.es.indices.exists(index=self.reviews_index):
            await self.es.indices.create(
                index=self.reviews_index,
                mappings=REVIEWS_MAPPINGS,
            )
            logger.info("Created index: %s", self.reviews_index)

    async def index_contract(self, contract: dict) -> None:
        """Index a contract metadata document."""
        await self.es.index(
            index=self.contracts_index,
            id=contract["contract_id"],
            document=contract,
        )

    async def update_contract_review_summary(self, contract_id: str, review_doc: dict) -> None:
        """Store latest review summary fields on the contract record for dashboard use."""
        await self.es.update(
            index=self.contracts_index,
            id=contract_id,
            retry_on_conflict=5,
            doc={
                "latest_reviewed_at": review_doc.get("reviewed_at"),
                "latest_review_score": review_doc.get("contract_safety_score"),
                "latest_review_summary": review_doc.get("summary", ""),
                "latest_review_id": review_doc.get("review_id"),
                "latest_review_finding_count": review_doc.get("findings_count", 0),
            },
            refresh="wait_for",
        )

    async def get_contract(self, contract_id: str) -> dict | None:
        """Get a contract by ID."""
        try:
            resp = await self.es.get(index=self.contracts_index, id=contract_id)
            return resp["_source"]
        except NotFoundError:
            return None

    async def list_contracts(self) -> list[dict]:
        """List all contracts."""
        resp = await self.es.search(
            index=self.contracts_index,
            query={"match_all": {}},
            size=100,
            sort=[{"upload_timestamp": {"order": "desc"}}],
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def bulk_index_clauses(self, clauses: list[dict]) -> int:
        """Bulk index clause documents. Returns count indexed."""
        if not clauses:
            return 0
        operations = []
        for clause in clauses:
            operations.append({"index": {"_index": self.clauses_index, "_id": clause["clause_id"]}})
            operations.append(clause)
        resp = await self.es.bulk(operations=operations, refresh="wait_for")
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    logger.error("Bulk index error: %s", item["index"]["error"])
        return len(clauses)

    async def bulk_index_cuad_examples(self, examples: list[dict]) -> int:
        """Bulk index CUAD example documents. Returns count indexed."""
        if not examples:
            return 0

        # Keep each request well below ES http.max_content_length to avoid 413s.
        max_docs_per_batch = 100
        max_batch_bytes = 8 * 1024 * 1024

        indexed = 0
        batch: list[dict] = []
        batch_bytes = 0

        async def flush() -> None:
            nonlocal indexed, batch, batch_bytes
            if not batch:
                return
            resp = await self.es.bulk(operations=batch, refresh="wait_for")
            if resp.get("errors"):
                for item in resp["items"]:
                    if "error" in item.get("index", {}):
                        logger.error("CUAD bulk index error: %s", item["index"]["error"])
            indexed += len(batch) // 2
            batch = []
            batch_bytes = 0

        for example in examples:
            action = {"index": {"_index": self.cuad_index, "_id": example["example_id"]}}
            # Approximate NDJSON bytes for sizing decisions.
            pair_bytes = (
                len(json.dumps(action, ensure_ascii=False).encode("utf-8"))
                + len(json.dumps(example, ensure_ascii=False).encode("utf-8"))
                + 2
            )

            would_exceed_docs = (len(batch) // 2) >= max_docs_per_batch
            would_exceed_bytes = batch_bytes + pair_bytes > max_batch_bytes
            if batch and (would_exceed_docs or would_exceed_bytes):
                await flush()

            batch.append(action)
            batch.append(example)
            batch_bytes += pair_bytes

        await flush()
        logger.info("Indexed %d CUAD examples in batches", indexed)
        return indexed

    async def get_clauses_by_contract(self, contract_id: str) -> list[dict]:
        """Get all clauses for a contract."""
        resp = await self.es.search(
            index=self.clauses_index,
            query={"term": {"contract_id": contract_id}},
            size=500,
        )
        return [hit["_source"] for hit in resp["hits"]["hits"]]

    async def save_review(self, review_doc: dict) -> dict:
        """Persist a contract review and return the stored document."""
        await self.es.index(
            index=self.reviews_index,
            id=review_doc["review_id"],
            document=review_doc,
            refresh="wait_for",
        )
        return review_doc

    async def get_latest_review(self, contract_id: str) -> dict | None:
        """Fetch the latest review for a contract, if one exists."""
        resp = await self.es.search(
            index=self.reviews_index,
            query={"term": {"contract_id": contract_id}},
            size=1,
            sort=[{"reviewed_at": {"order": "desc"}}],
        )
        hits = resp.get("hits", {}).get("hits", [])
        if not hits:
            return None
        return hits[0]["_source"]

    async def list_reviews_by_contract(self, contract_id: str) -> list[dict]:
        """List all reviews for a contract, newest first."""
        resp = await self.es.search(
            index=self.reviews_index,
            query={"term": {"contract_id": contract_id}},
            size=100,
            sort=[{"reviewed_at": {"order": "desc"}}],
        )
        return [hit["_source"] for hit in resp.get("hits", {}).get("hits", [])]

    async def get_review_by_id(self, review_id: str) -> dict | None:
        """Get a specific stored review by review id."""
        try:
            resp = await self.es.get(index=self.reviews_index, id=review_id)
            return resp["_source"]
        except NotFoundError:
            return None

    async def delete_review(self, review_id: str) -> None:
        """Delete a stored review by id if it exists."""
        try:
            await self.es.delete(index=self.reviews_index, id=review_id, refresh="wait_for")
        except NotFoundError:
            return

    async def delete_clauses_by_contract(self, contract_id: str) -> None:
        """Delete all clause documents for a contract."""
        await self.es.delete_by_query(
            index=self.clauses_index,
            query={"term": {"contract_id": contract_id}},
            refresh=True,
            conflicts="proceed",
        )

    async def delete_reviews_by_contract(self, contract_id: str) -> None:
        """Delete all reviews for a contract."""
        await self.es.delete_by_query(
            index=self.reviews_index,
            query={"term": {"contract_id": contract_id}},
            refresh=True,
            conflicts="proceed",
        )

    async def delete_contract(self, contract_id: str) -> None:
        """Delete the contract metadata document."""
        try:
            await self.es.delete(index=self.contracts_index, id=contract_id, refresh="wait_for")
        except NotFoundError:
            return

    async def _hybrid_search_rrf(
        self,
        *,
        index_name: str,
        query_text: str,
        query_vector: list[float],
        text_field: str = "text",
        vector_field: str = "text_embedding",
        filters: list[dict] | None = None,
        top_k: int = 10,
        rank_constant: int = 60,
    ) -> list[dict]:
        """Hybrid BM25 + kNN search with manual Reciprocal Rank Fusion."""
        bm25_query: dict = {
            "bool": {
                "must": [
                    {"match": {text_field: {"query": query_text, "analyzer": "legal_analyzer"}}}
                ]
            }
        }
        if filters:
            bm25_query["bool"]["filter"] = filters

        knn_query: dict = {
            "field": vector_field,
            "query_vector": query_vector,
            "k": top_k * 5,
            "num_candidates": top_k * 10,
        }
        if filters:
            knn_query["filter"] = {"bool": {"must": filters}}

        bm25_resp = await self.es.search(
            index=index_name,
            query=bm25_query,
            size=top_k * 5,
            highlight={
                "fields": {text_field: {"fragment_size": 200, "number_of_fragments": 3}}
            },
        )

        knn_resp = await self.es.search(
            index=index_name,
            knn=knn_query,
            size=top_k * 5,
        )

        rrf_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}
        highlight_map: dict[str, list[str]] = {}

        for rank, hit in enumerate(bm25_resp["hits"]["hits"]):
            doc_id = hit["_id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank_constant + rank + 1)
            doc_map[doc_id] = hit["_source"]
            highlight_map[doc_id] = hit.get("highlight", {}).get(text_field, [])

        for rank, hit in enumerate(knn_resp["hits"]["hits"]):
            doc_id = hit["_id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank_constant + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = hit["_source"]

        sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]

        results = []
        for doc_id in sorted_ids:
            doc = doc_map[doc_id]
            doc["_score"] = rrf_scores[doc_id]
            doc["highlights"] = highlight_map.get(doc_id, [])
            results.append(doc)
        return results

    async def hybrid_search_rrf(
        self,
        query_text: str,
        query_vector: list[float],
        clause_types: list[str] | None = None,
        contract_ids: list[str] | None = None,
        top_k: int = 10,
        rank_constant: int = 60,
    ) -> list[dict]:
        """Hybrid BM25 + kNN search over indexed contract clauses."""
        filters = []
        if clause_types:
            filters.append({"terms": {"clause_type": clause_types}})
        if contract_ids:
            filters.append({"terms": {"contract_id": contract_ids}})

        return await self._hybrid_search_rrf(
            index_name=self.clauses_index,
            query_text=query_text,
            query_vector=query_vector,
            filters=filters or None,
            top_k=top_k,
            rank_constant=rank_constant,
        )

    async def hybrid_search_cuad_rrf(
        self,
        query_text: str,
        query_vector: list[float],
        clause_type: str | None = None,
        top_k: int = 5,
        rank_constant: int = 60,
    ) -> list[dict]:
        """Hybrid BM25 + kNN search over CUAD expert examples."""
        filters = []
        if clause_type:
            filters.append({"term": {"clause_type": clause_type}})

        return await self._hybrid_search_rrf(
            index_name=self.cuad_index,
            query_text=query_text,
            query_vector=query_vector,
            filters=filters or None,
            top_k=top_k,
            rank_constant=rank_constant,
        )

    async def close(self) -> None:
        """Close the ES client."""
        await self.es.close()
