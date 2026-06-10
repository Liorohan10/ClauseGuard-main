import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from clauseguard.agents.ingestion import IngestionAgent
from clauseguard.agents.review import ReviewAgent
from clauseguard.agents.search import SearchAgent
from clauseguard.api.router import api_router
from clauseguard.config import settings
from clauseguard.openai_assistant import OpenAILegalAssistant
from clauseguard.services.claude_service import ClaudeService
from clauseguard.services.elasticsearch_service import ElasticsearchService
from clauseguard.services.embedding_service import EmbeddingService
from clauseguard.services.pdf_service import PDFService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models, connect ES, create indices. Shutdown: close clients."""
    logger.info("Loading embedding model: %s", settings.embedding_model)
    embedding_service = EmbeddingService(settings.embedding_model)
    logger.info("Embedding model loaded (dim=%d)", embedding_service.dimension)

    logger.info("Connecting to Elasticsearch: %s", settings.elasticsearch_url)
    es_service = ElasticsearchService()
    await es_service.ensure_indices()
    logger.info("Elasticsearch indices ready")

    pdf_service = PDFService()
    claude_service = ClaudeService()
    openai_assistant = OpenAILegalAssistant()

    # Wire up agents
    app.state.es_service = es_service
    app.state.ingestion_agent = IngestionAgent(
        pdf_service=pdf_service,
        claude_service=claude_service,
        embedding_service=embedding_service,
        es_service=es_service,
    )
    app.state.search_agent = SearchAgent(
        embedding_service=embedding_service,
        es_service=es_service,
    )
    app.state.openai_assistant = openai_assistant
    app.state.review_agent = ReviewAgent(
        claude_service=claude_service,
        es_service=es_service,
        search_agent=app.state.search_agent,
    )

    logger.info("ClauseGuard is ready")
    yield

    # Shutdown
    await es_service.close()
    logger.info("ClauseGuard shutdown complete")


app = FastAPI(
    title="ClauseGuard",
    description="Multi-agent legal contract review system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def run():
    import uvicorn
    uvicorn.run(
        "clauseguard.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=[settings.openai_dump_dir],
    )
