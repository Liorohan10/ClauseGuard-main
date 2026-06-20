import logging

from clauseguard.models.clause import ClauseType
from clauseguard.models.search import SearchHit, SearchRequest, SearchResponse
from clauseguard.services.elasticsearch_service import ElasticsearchService
from clauseguard.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SearchAgent:
    """Hybrid BM25 + kNN search over indexed clauses."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        es_service: ElasticsearchService,
    ):
        self.embedder = embedding_service
        self.es = es_service

    async def search(self, request: SearchRequest) -> SearchResponse:
        """Execute hybrid search and return ranked results."""
        # Encode query
        query_vector = self.embedder.encode(request.query)

        # Execute hybrid search
        clause_types = [ct.value for ct in request.clause_types] if request.clause_types else None
        results = await self.es.hybrid_search_rrf(
            query_text=request.query,
            query_vector=query_vector,
            clause_types=clause_types,
            contract_ids=request.contract_ids,
            top_k=request.top_k,
        )

        # Map to SearchHit models
        hits = []
        for doc in results:
            try:
                hit = SearchHit(
                    clause_id=doc["clause_id"],
                    contract_id=doc["contract_id"],
                    clause_type=ClauseType(doc["clause_type"]),
                    text=doc["text"],
                    score=doc.get("_score", 0.0),
                    section_number=doc.get("section_number", ""),
                    page_number=doc.get("page_number", 1),
                    highlights=doc.get("highlights", []),
                )
                hits.append(hit)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed search result: %s", e)

        return SearchResponse(
            query=request.query,
            total_hits=len(hits),
            hits=hits,
        )
