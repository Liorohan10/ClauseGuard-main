from fastapi import APIRouter

from clauseguard.api import contracts, review, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(contracts.router)
api_router.include_router(search.router)
api_router.include_router(review.router)


@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}
