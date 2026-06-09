import logging
import uuid
from datetime import datetime

from clauseguard.models.clause import ClauseType, ExtractedClause
from clauseguard.models.contract import ContractMetadata, ContractUploadResponse
from clauseguard.services.claude_service import ClaudeService
from clauseguard.services.elasticsearch_service import ElasticsearchService
from clauseguard.services.embedding_service import EmbeddingService
from clauseguard.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class IngestionAgent:
    """Parse uploaded contracts, extract clauses via Claude, embed, and index in ES."""

    def __init__(
        self,
        pdf_service: PDFService,
        claude_service: ClaudeService,
        embedding_service: EmbeddingService,
        es_service: ElasticsearchService,
    ):
        self.pdf = pdf_service
        self.claude = claude_service
        self.embedder = embedding_service
        self.es = es_service

    async def ingest(self, file_bytes: bytes, filename: str) -> ContractUploadResponse:
        """Full ingestion pipeline: parse → extract → embed → index."""
        contract_id = str(uuid.uuid4())

        # 1. Parse document
        text, num_pages = self.pdf.parse(file_bytes, filename)
        logger.info("Parsed %s: %d pages, %d chars", filename, num_pages, len(text))

        # 2. Extract clauses via Claude
        raw_clauses = self.claude.extract_clauses(text)
        logger.info("Claude extracted %d clauses from %s", len(raw_clauses), filename)

        # 3. Post-process: validate types, correct offsets
        clauses = self._post_process(raw_clauses, text, contract_id)

        # 4. Generate embeddings
        clause_texts = [c.text for c in clauses]
        embeddings = self.embedder.encode_batch(clause_texts)

        # 5. Build ES documents
        es_docs = []
        for clause, embedding in zip(clauses, embeddings):
            doc = clause.model_dump()
            doc["text_embedding"] = embedding
            es_docs.append(doc)

        # 6. Index contract metadata
        clause_types = list({c.clause_type for c in clauses})
        metadata = ContractMetadata(
            contract_id=contract_id,
            filename=filename,
            upload_timestamp=datetime.utcnow(),
            num_pages=num_pages,
            num_clauses=len(clauses),
            clause_types_found=clause_types,
            text_length=len(text),
        )
        await self.es.index_contract(metadata.model_dump(mode="json"))

        # 7. Bulk index clauses
        indexed = await self.es.bulk_index_clauses(es_docs)
        logger.info("Indexed %d clauses for contract %s", indexed, contract_id)

        return ContractUploadResponse(
            contract_id=contract_id,
            filename=filename,
            num_clauses=len(clauses),
            clause_types_found=clause_types,
        )

    def _post_process(
        self, raw_clauses: list[dict], source_text: str, contract_id: str
    ) -> list[ExtractedClause]:
        """Validate clause types and correct offsets via string matching."""
        processed = []
        for raw in raw_clauses:
            # Validate clause type
            raw_type = raw.get("clause_type", "other")
            try:
                clause_type = ClauseType(raw_type)
            except ValueError:
                clause_type = ClauseType.OTHER

            clause_text = raw.get("text", "").strip()
            if not clause_text:
                continue

            # Correct offsets by searching for the text in source
            hint_start = raw.get("char_offset_start", 0)
            start, end = self._find_offset(source_text, clause_text, hint_start)

            clause = ExtractedClause(
                clause_id=str(uuid.uuid4()),
                contract_id=contract_id,
                clause_type=clause_type,
                text=clause_text,
                section_number=raw.get("section_number", ""),
                page_number=raw.get("page_number", 1),
                char_offset_start=start,
                char_offset_end=end,
                confidence=min(max(raw.get("confidence", 0.8), 0.0), 1.0),
            )
            processed.append(clause)
        return processed

    def _find_offset(
        self, source: str, clause_text: str, hint: int
    ) -> tuple[int, int]:
        """Find the actual offset of clause_text in source, using hint as starting point."""
        # Try exact match first near the hint
        search_start = max(0, hint - 200)
        idx = source.find(clause_text, search_start)
        if idx != -1:
            return idx, idx + len(clause_text)

        # Try with first 80 chars (Claude may truncate)
        snippet = clause_text[:80]
        idx = source.find(snippet, search_start)
        if idx != -1:
            return idx, idx + len(clause_text)

        # Fallback: use the hint as-is
        return hint, hint + len(clause_text)
