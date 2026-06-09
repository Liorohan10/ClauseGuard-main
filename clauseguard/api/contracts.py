from fastapi import APIRouter, Depends, HTTPException, UploadFile

from clauseguard.agents.ingestion import IngestionAgent
from clauseguard.api.deps import get_es_service, get_ingestion_agent
from clauseguard.models.contract import ContractMetadata, ContractUploadResponse
from clauseguard.services.elasticsearch_service import ElasticsearchService

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/upload", response_model=ContractUploadResponse)
async def upload_contract(
    file: UploadFile,
    agent: IngestionAgent = Depends(get_ingestion_agent),
):
    """Upload a PDF or text contract for ingestion."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    allowed = (".pdf", ".txt", ".text")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail="Only PDF and text files are supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    result = await agent.ingest(content, file.filename)
    return result


@router.get("/", response_model=list[ContractMetadata])
async def list_contracts(
    es: ElasticsearchService = Depends(get_es_service),
):
    """List all ingested contracts."""
    docs = await es.list_contracts()
    return [ContractMetadata(**doc) for doc in docs]


@router.get("/{contract_id}", response_model=ContractMetadata)
async def get_contract(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    """Get a specific contract's metadata."""
    doc = await es.get_contract(contract_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractMetadata(**doc)


@router.get("/{contract_id}/clauses")
async def get_contract_clauses(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    """Get all extracted clauses for a contract."""
    contract = await es.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    clauses = await es.get_clauses_by_contract(contract_id)
    return clauses


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    """Delete a contract and all related clauses/reviews."""
    await es.delete_reviews_by_contract(contract_id)
    await es.delete_clauses_by_contract(contract_id)
    await es.delete_contract(contract_id)
    return {"status": "deleted", "contract_id": contract_id}
