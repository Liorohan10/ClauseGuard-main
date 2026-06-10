import logging

from clauseguard.models.clause import ClauseType
from clauseguard.models.cuad import CuadSearchHit, CuadSearchRequest, CuadSearchResponse
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

    async def search_cuad(self, request: CuadSearchRequest) -> CuadSearchResponse:
        """Execute hybrid search over CUAD examples and return ranked results."""
        query_vector = self.embedder.encode(request.query)
        clause_type = request.clause_type.value if request.clause_type else None
        results = await self.es.hybrid_search_cuad_rrf(
            query_text=request.query,
            query_vector=query_vector,
            clause_type=clause_type,
            top_k=request.top_k,
        )

        examples = []
        for doc in results:
            try:
                hit = CuadSearchHit(
                    example_id=doc["example_id"],
                    source_contract_id=doc.get("source_contract_id", ""),
                    title=doc.get("title", ""),
                    paragraph_index=doc.get("paragraph_index", 0),
                    qas_id=doc.get("qas_id", ""),
                    cuad_label=doc.get("cuad_label", ""),
                    clause_type=ClauseType(doc.get("clause_type", "other")),
                    question=doc.get("question", ""),
                    answer_text=doc.get("answer_text", ""),
                    answer_start=doc.get("answer_start", 0),
                    answer_end=doc.get("answer_end", 0),
                    context_excerpt=doc.get("context_excerpt", ""),
                    score=doc.get("_score", 0.0),
                    is_impossible=doc.get("is_impossible", False),
                )
                examples.append(hit)
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed CUAD result: %s", e)

        return CuadSearchResponse(query=request.query, total_hits=len(examples), examples=examples)
