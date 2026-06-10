from fastapi import APIRouter, Depends

from clauseguard.agents.search import SearchAgent
from clauseguard.api.deps import get_search_agent
from clauseguard.models.cuad import CuadSearchRequest, CuadSearchResponse
from clauseguard.models.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search_clauses(
    request: SearchRequest,
    agent: SearchAgent = Depends(get_search_agent),
):
    """Hybrid BM25 + kNN search over indexed clauses."""
    return await agent.search(request)


@router.post("/cuad", response_model=CuadSearchResponse)
async def search_cuad_examples(
    request: CuadSearchRequest,
    agent: SearchAgent = Depends(get_search_agent),
):
    """Hybrid BM25 + kNN search over CUAD expert examples."""
    return await agent.search_cuad(request)
