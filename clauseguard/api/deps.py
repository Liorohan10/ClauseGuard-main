from fastapi import Request

from clauseguard.agents.ingestion import IngestionAgent
from clauseguard.agents.review import ReviewAgent
from clauseguard.agents.search import SearchAgent
from clauseguard.openai_assistant import OpenAILegalAssistant
from clauseguard.services.elasticsearch_service import ElasticsearchService


def get_ingestion_agent(request: Request) -> IngestionAgent:
    return request.app.state.ingestion_agent


def get_search_agent(request: Request) -> SearchAgent:
    return request.app.state.search_agent


def get_review_agent(request: Request) -> ReviewAgent:
    return request.app.state.review_agent


def get_es_service(request: Request) -> ElasticsearchService:
    return request.app.state.es_service


def get_openai_assistant(request: Request) -> OpenAILegalAssistant:
    return request.app.state.openai_assistant
