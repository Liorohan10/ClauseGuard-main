from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import fitz
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_elasticsearch import ElasticsearchStore
from elasticsearch import Elasticsearch
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from sentence_transformers import CrossEncoder

from clauseguard.config import settings
from clauseguard.services.embedding_service import EmbeddingService
from langchain_core.embeddings import Embeddings
from clauseguard.models.openai_legal import (
    ClauseAnalysis,
    RiskAssessment,
    ComplianceFinding,
    NegotiationStrategy,
    MissingProtection,
    ContractReviewOutput,
    NDAGenerationOutput,
    schema_instructions,
)

logger = logging.getLogger(__name__)

PRIVACY_TESTS = [
    "Legal Basis for Processing",
    "Consent Management",
    "Direct Marketing Restrictions",
    "Cross-Border Safeguards (e.g. Standard Contractual Clauses)",
    "Data Retention & Deletion",
    "Technical & Organizational Security Measures",
    "Data Breach Notification Timeframe",
    "DPO Designation",
    "Data Subject Rights - Access/Rectification",
    "Data Subject Rights - Erasure/Portability",
    "Data Processing Agreement (DPA) Requirement",
    "Transparency & Disclosures",
    "Subprocessors Consent & Flow-down",
    "Anonymization/Pseudonymization Standards",
    "Children's Data Protections",
]

EXPORT_TESTS = [
    "Item Classification (Dual-use/Military)",
    "Sanctioned Destinations Prohibition",
    "Restricted/Denied Parties Checks",
    "End-Use Verification (Military/WMD)",
    "Export License Responsibility",
    "Intangible Technology Control",
    "Record-Keeping Requirements (e.g. 5 years)",
    "Violations Reporting",
    "Subcontractor Export Flow-Down",
    "Export Auditing Rights",
]


# ----------------------------------------------------------------------
# Pydantic Schemas for Structured Node Outputs
# ----------------------------------------------------------------------

class JurisdictionProfileSchema(BaseModel):
    privacy_jurisdiction: str = Field(description="The primary privacy jurisdiction identified, e.g. EU or Australia or None")
    export_jurisdiction: str = Field(description="The primary export control jurisdiction identified, e.g. EU or Australia or None")
    export_triggered: bool = Field(description="True if export controls apply/are triggered by the contract details (e.g. transfer of technical goods, software, or cross-border tech data)")


class CoordinateMapItem(BaseModel):
    test_name: str = Field(description="Name of the compliance test.")
    target_clause: str = Field(default="", description="Specific section/paragraph number, e.g. 'Section 4.2' or 'Article 10(b)'.")
    contract_excerpt: str = Field(default="", description="Verbatim contract excerpt text associated with this test.")
    source_page: int | None = Field(default=None, description="Page number where the excerpt is found.")
    source_section: str = Field(default="", description="Section heading where the excerpt is found.")
    source_clause_id: str = Field(default="", description="Internal clause identifier if matched from the source map.")


class CoordinateMappingSchema(BaseModel):
    mappings: list[CoordinateMapItem] = Field(description="List of coordinate mappings for the compliance tests.")


class ContractClauseCoordinate(BaseModel):
    clause_id: str = Field(default="", description="Internal clause identifier from the stored source map.")
    section_number: str = Field(default="", description="Contract section or paragraph number.")
    heading: str = Field(default="", description="Clause heading or best available title.")
    exact_verbatim_start: str = Field(default="", description="The first 80-160 verbatim characters of the clause.")
    page_number: int | None = Field(default=None, description="Page number where the clause appears.")


class ContractMapSchema(BaseModel):
    clauses: list[ContractClauseCoordinate] = Field(description="Every identified contract clause with coordinates.")


class PrivacyFindingItemSchema(BaseModel):
    test_name: str = Field(description="One of the 15 privacy control tests being evaluated")
    status: str = Field(description="pass, fail, partial, or not-applicable")
    severity: str = Field(description="high, medium, low, info")
    explanation: str = Field(description="Explanation of why this status was given, citing contract details")
    evidence: str = Field(description="Exact sentence or provision from the contract as evidence")
    remediation: str = Field(description="Actionable mitigation or remediation advice")
    target_clause: str = Field(default="", description="The specific section/paragraph number from the uploaded contract.")
    contract_excerpt: str = Field(default="", description="The exact verbatim text being flagged.")
    regulatory_basis: str = Field(default="", description="The specific Article/Section from the official RAG context that this clause violates.")
    deviation_gap: str = Field(default="", description="A direct comparison: 'Contract says [X], but Regulation [Y] requires [Z].'")
    source_page: int | None = Field(default=None, description="Page number of the evidence")
    source_section: str = Field(default="", description="Section number/heading of the evidence")
    source_clause_id: str = Field(default="", description="Internal clause identifier of the evidence")
    source_excerpt: str = Field(default="", description="Excerpt of the clause text")


class PrivacyAnalysisSchema(BaseModel):
    findings: list[PrivacyFindingItemSchema] = Field(description="A list of evaluations for the 15 data privacy compliance tests")


class ExportFindingItemSchema(BaseModel):
    test_name: str = Field(description="The export control test being evaluated")
    status: str = Field(description="pass, fail, partial, or not-applicable")
    severity: str = Field(description="high, medium, low, info")
    explanation: str = Field(description="Explanation of why this status was given, citing contract details")
    evidence: str = Field(description="Exact sentence or provision from the contract as evidence")
    remediation: str = Field(description="Actionable mitigation or remediation advice")
    target_clause: str = Field(default="", description="The specific section/paragraph number from the uploaded contract.")
    contract_excerpt: str = Field(default="", description="The exact verbatim text being flagged.")
    regulatory_basis: str = Field(default="", description="The specific Article/Section from the official RAG context that this clause violates.")
    deviation_gap: str = Field(default="", description="A direct comparison: 'Contract says [X], but Regulation [Y] requires [Z].'")
    source_page: int | None = Field(default=None, description="Page number of the evidence")
    source_section: str = Field(default="", description="Section number/heading of the evidence")
    source_clause_id: str = Field(default="", description="Internal clause identifier of the evidence")
    source_excerpt: str = Field(default="", description="Excerpt of the clause text")


class ExportAnalysisSchema(BaseModel):
    findings: list[ExportFindingItemSchema] = Field(description="A list of evaluations for export control compliance tests")


class VerifiedFindingItemSchema(BaseModel):
    test_name: str
    status: str = Field(description="pass, fail, partial, or not-applicable. Corrected status if it was a false positive.")
    severity: str
    explanation: str
    evidence: str
    remediation: str
    verification_notes: str = Field(description="Detailed verification comments based on regulations or web search citations.")
    citation_source: str = Field(description="Specific legal article or web URL cited.")
    target_clause: str = Field(default="", description="The specific section/paragraph number from the uploaded contract.")
    contract_excerpt: str = Field(default="", description="The exact verbatim text being flagged.")
    regulatory_basis: str = Field(default="", description="The specific Article/Section from the official RAG context that this clause violates.")
    deviation_gap: str = Field(default="", description="A direct comparison: 'Contract says [X], but Regulation [Y] requires [Z].'")
    source_page: int | None = None
    source_section: str = ""
    source_clause_id: str = ""
    source_excerpt: str = ""


class VerificationSchema(BaseModel):
    verified_findings: list[VerifiedFindingItemSchema] = Field(description="List of verified and corrected findings")


class DecisionNodeResponse(BaseModel):
    summary: str = Field(description="A qualitative executive summary of the contract review, stating the final decision (PASS/FAIL) and the main grounds.")
    clause_analyses: list[ClauseAnalysis] = Field(default_factory=list, description="A list of 5-12 significant clauses analyzed from the contract.")
    risk_assessments: list[RiskAssessment] = Field(default_factory=list, description="A list of identified risks based on failed compliance findings.")
    compliance_findings: list[ComplianceFinding] = Field(default_factory=list, description="A list of compliance findings mapped from verified findings.")
    negotiation_strategies: list[NegotiationStrategy] = Field(default_factory=list, description="A list of proposed redlines / replacement language for failed findings.")
    missing_protections: list[MissingProtection] = Field(default_factory=list, description="A list of missing or weak protections identified.")


# ----------------------------------------------------------------------
# Local Embeddings Wrapper
# ----------------------------------------------------------------------

class EmbeddingWrapper(Embeddings):
    """LangChain Embeddings wrapper around our custom EmbeddingService."""
    def __init__(self, service: EmbeddingService):
        self.service = service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.service.encode_batch(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.service.encode(text)


# ----------------------------------------------------------------------
# LangGraph State Definition
# ----------------------------------------------------------------------

class AgentState(TypedDict):
    contract_text: str
    source_context: str
    contract_map: list
    privacy_mappings: list
    export_mappings: list
    jurisdiction_profile: dict
    privacy_findings: list
    export_findings: list
    verification_results: list
    redlines: list
    final_decision: dict
    export_triggered: bool


@dataclass(slots=True)
class DocumentPayload:
    filename: str
    file_type: str
    text: str
    page_count: int = 1
    content: list[dict[str, Any]] | str | None = None
    source_context: str = ""


# ----------------------------------------------------------------------
# Assistant Implementation
# ----------------------------------------------------------------------

class OpenAILegalAssistant:
    """Async legal assistant powered by the LangGraph sequential agent workflow."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        vision_model: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url,
        )
        self.model = model or settings.openai_model
        self.vision_model = vision_model or settings.openai_vision_model
        
        # Initialize LangChain OpenAI LLM
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url,
            temperature=0.2,
        )
        
        # Initialize CrossEncoder for RAG reranking
        try:
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("Successfully loaded CrossEncoder: cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            logger.warning("Failed to load CrossEncoder model: %s", e)
            self.cross_encoder = None
        
        # Build the sequential LangGraph
        self.graph = self._build_graph()

    def _format_mapping_rag_context(self, mappings: list[dict]) -> str:
        blocks: list[str] = []
        for mapping in mappings:
            contexts = mapping.get("rag_context") or []
            if not contexts:
                blocks.append(
                    f"Test: {mapping.get('test_name', '')}\n"
                    "Official PDF Context: No matching official regulation context was retrieved."
                )
                continue
            blocks.append(
                f"Test: {mapping.get('test_name', '')}\n"
                f"Target Clause: {mapping.get('target_clause', '')}\n"
                f"Contract Excerpt: {mapping.get('contract_excerpt', '')}\n"
                "Official PDF Context:\n"
                + "\n\n".join(contexts)
            )
        return "\n\n---\n\n".join(blocks)

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        llm = self.llm

        # Node 1: Jurisdiction Identification
        def jurisdiction_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Jurisdiction Node")
            prompt = (
                "Analyze the following contract text. Identify the applicable data privacy and export control jurisdictions "
                "based on the contracting parties, the governing law, and the scope of work. Also determine whether export controls "
                "are triggered (e.g. transfer of technical goods, software, or cross-border tech data).\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}"
            )
            structured_llm = llm.with_structured_output(JurisdictionProfileSchema)
            profile = structured_llm.invoke(prompt)
            return {
                "jurisdiction_profile": profile.model_dump(),
                "export_triggered": profile.export_triggered
            }

        # Node 2: Contract Coordinate Map
        def contract_map_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Contract Map Node")
            prompt = (
                "You are a forensic legal auditor. Build a Contract Map before any compliance analysis.\n"
                "Identify every discrete contract clause available in the SOURCE MAP or CONTRACT TEXT. "
                "For each clause, return its section_number, heading, page_number, clause_id if present, "
                "and exact_verbatim_start copied exactly from the clause text. Do not summarize.\n\n"
                f"SOURCE MAP:\n{state['source_context']}\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}"
            )
            structured_llm = llm.with_structured_output(ContractMapSchema)
            response = structured_llm.invoke(prompt)
            return {"contract_map": [c.model_dump() for c in response.clauses]}

        # Node 3: Compliance Test Coordinate Mapping
        def coordinate_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Coordinate Mapping Node")
            tests = PRIVACY_TESTS + (EXPORT_TESTS if state.get("export_triggered", False) else [])
            tests_text = "\n".join(f"{idx}. {test}" for idx, test in enumerate(tests, start=1))
            prompt = (
                "You are a forensic legal auditor. For every compliance test, identify the exact contract clause "
                "that addresses the requirement. If no clause addresses it, leave target_clause and contract_excerpt empty. "
                "Use only the Contract Map and Source Map; do not infer a clause from general background text.\n\n"
                f"COMPLIANCE TESTS:\n{tests_text}\n\n"
                f"CONTRACT MAP:\n{json.dumps(state.get('contract_map', []), indent=2)}\n\n"
                f"SOURCE MAP:\n{state['source_context']}\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}"
            )
            structured_llm = llm.with_structured_output(CoordinateMappingSchema)
            response = structured_llm.invoke(prompt)
            mappings = [m.model_dump() for m in response.mappings]
            return {
                "privacy_mappings": [m for m in mappings if m.get("test_name") in PRIVACY_TESTS],
                "export_mappings": [m for m in mappings if m.get("test_name") in EXPORT_TESTS],
            }

        # Node 5: Privacy Compliance Check
        def privacy_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Privacy Node")
            profile = state["jurisdiction_profile"]
            mappings_dict = state.get("privacy_mappings", [])

            # Pass 2: Evidence-First Analysis
            logger.info("[LangGraph] Privacy Node - Pass 2: Evidence-First Analysis")
            pass2_prompt = (
                f"You are a forensic legal privacy auditor. The identified privacy jurisdiction profile is: {profile}.\n"
                "Do not summarize. For every compliance test, identify the specific contract clause that addresses the requirement. "
                "If the clause is missing, mark it as 'Missing Protection' in the explanation, set status to fail or partial, "
                "and cite the specific Article/Section from the provided OFFICIAL REGULATORY RAG CONTEXT that mandates its inclusion.\n"
                "You are prohibited from issuing a finding unless you first extract contract_excerpt or explicitly mark it as Missing Protection.\n\n"
                f"COORDINATE MAPPINGS:\n{json.dumps(mappings_dict, indent=2)}\n\n"
                f"OFFICIAL REGULATORY RAG CONTEXT:\n{self._format_mapping_rag_context(mappings_dict)}\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}\n\n"
                f"SOURCE MAP:\n{state['source_context']}\n\n"
                "Operating Rules:\n"
                "- Use only the OFFICIAL REGULATORY RAG CONTEXT sourced from the provided PDFs.\n"
                "- Populate target_clause, contract_excerpt, regulatory_basis, deviation_gap, source_page, source_section, source_clause_id, and source_excerpt.\n"
                "- regulatory_basis must be a specific article/section visible in the RAG context.\n"
                "- deviation_gap must follow: Contract says [X], but Regulation [Y] requires [Z]."
            )
            structured_llm_pass2 = llm.with_structured_output(PrivacyAnalysisSchema)
            response = structured_llm_pass2.invoke(pass2_prompt)
            rag_by_test = {m.get("test_name"): m.get("rag_context", []) for m in mappings_dict}
            coord_by_test = {m.get("test_name"): m for m in mappings_dict}
            findings = []
            for finding in response.findings:
                item = finding.model_dump()
                coord = coord_by_test.get(item.get("test_name"), {})
                item["rag_context"] = rag_by_test.get(item.get("test_name"), [])
                for field in ["target_clause", "contract_excerpt", "source_page", "source_section", "source_clause_id"]:
                    if not item.get(field) and coord.get(field):
                        item[field] = coord[field]
                if not item.get("source_excerpt") and item.get("contract_excerpt"):
                    item["source_excerpt"] = item["contract_excerpt"]
                findings.append(item)
            return {
                "privacy_findings": findings
            }

        # Node 6: Export Control Compliance Check (Conditional)
        def export_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Export Node")
            profile = state["jurisdiction_profile"]
            mappings_dict = state.get("export_mappings", [])

            # Pass 2: Evidence-First Analysis
            logger.info("[LangGraph] Export Node - Pass 2: Evidence-First Analysis")
            pass2_prompt = (
                f"You are a forensic legal export-control auditor. The identified export jurisdiction profile is: {profile}.\n"
                "Do not summarize. For every compliance test, identify the specific contract clause that addresses the requirement. "
                "If the clause is missing, mark it as 'Missing Protection' in the explanation, set status to fail or partial, "
                "and cite the specific Article/Section from the provided OFFICIAL REGULATORY RAG CONTEXT that mandates its inclusion.\n"
                "You are prohibited from issuing a finding unless you first extract contract_excerpt or explicitly mark it as Missing Protection.\n\n"
                f"COORDINATE MAPPINGS:\n{json.dumps(mappings_dict, indent=2)}\n\n"
                f"OFFICIAL REGULATORY RAG CONTEXT:\n{self._format_mapping_rag_context(mappings_dict)}\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}\n\n"
                f"SOURCE MAP:\n{state['source_context']}\n\n"
                "Operating Rules:\n"
                "- Use only the OFFICIAL REGULATORY RAG CONTEXT sourced from the provided PDFs.\n"
                "- Populate target_clause, contract_excerpt, regulatory_basis, deviation_gap, source_page, source_section, source_clause_id, and source_excerpt.\n"
                "- regulatory_basis must be a specific article/section visible in the RAG context.\n"
                "- deviation_gap must follow: Contract says [X], but Regulation [Y] requires [Z]."
            )
            structured_llm_pass2 = llm.with_structured_output(ExportAnalysisSchema)
            response = structured_llm_pass2.invoke(pass2_prompt)
            rag_by_test = {m.get("test_name"): m.get("rag_context", []) for m in mappings_dict}
            coord_by_test = {m.get("test_name"): m for m in mappings_dict}
            findings = []
            for finding in response.findings:
                item = finding.model_dump()
                coord = coord_by_test.get(item.get("test_name"), {})
                item["rag_context"] = rag_by_test.get(item.get("test_name"), [])
                for field in ["target_clause", "contract_excerpt", "source_page", "source_section", "source_clause_id"]:
                    if not item.get(field) and coord.get(field):
                        item[field] = coord[field]
                if not item.get("source_excerpt") and item.get("contract_excerpt"):
                    item["source_excerpt"] = item["contract_excerpt"]
                findings.append(item)
            return {
                "export_findings": findings
            }

        # Node 4: Regulatory RAG
        def rag_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to RAG Node")
            
            # Setup Elasticsearch vector store connection
            embedding_service = EmbeddingService(settings.embedding_model)
            embeddings = EmbeddingWrapper(embedding_service)
            
            try:
                es_client = Elasticsearch(settings.elasticsearch_url)
                vector_store = ElasticsearchStore(
                    index_name="clauseguard-official-regs",
                    embedding=embeddings,
                    client=es_client
                )
            except Exception as e:
                logger.warning("Failed to connect to Elasticsearch for RAG: %s", e)
                vector_store = None

            # Mapping of 3 distinct semantic queries for each compliance test
            expanded_queries_mapping = {
                # Privacy Compliance Tests
                "Legal Basis for Processing": [
                    "lawful basis for processing GDPR Article 6",
                    "consent legitimate interest contract performance legal basis",
                    "conditions for processing personal data requirements"
                ],
                "Consent Management": [
                    "conditions for consent GDPR Article 7 withdrawal of consent",
                    "freely given specific informed unambiguous consent request",
                    "obtaining and managing user consent rules"
                ],
                "Direct Marketing Restrictions": [
                    "direct marketing opt-out opt-in consent requirements",
                    "unsolicited commercial communications marketing restrictions",
                    "objection to processing for direct marketing purposes"
                ],
                "Cross-Border Safeguards (e.g. Standard Contractual Clauses)": [
                    "cross-border data transfers standard contractual clauses SCCs GDPR",
                    "transfer of personal data to third countries adequacy decision safeguards",
                    "international data transfer mechanisms and agreements"
                ],
                "Data Retention & Deletion": [
                    "storage limitation period data retention deletion requirements",
                    "right to erasure retention schedule personal data disposal",
                    "duration of data storage and criteria for retention"
                ],
                "Technical & Organizational Security Measures": [
                    "technical and organizational security measures GDPR Article 32 encryption",
                    "security of processing data protection measures confidentiality integrity",
                    "appropriate level of security and technical controls"
                ],
                "Data Breach Notification Timeframe": [
                    "personal data breach notification to supervisory authority 72 hours",
                    "notification of data breach to data subjects timeframe",
                    "breach detection response and communication requirements"
                ],
                "DPO Designation": [
                    "designation of data protection officer DPO requirement tasks",
                    "when is DPO mandatory for controllers processors",
                    "position and duties of the data protection officer"
                ],
                "Data Subject Rights - Access/Rectification": [
                    "right of access by the data subject GDPR Article 15 rectification",
                    "information to be provided to data subjects access requests",
                    "correcting inaccurate personal data rights"
                ],
                "Data Subject Rights - Erasure/Portability": [
                    "right to erasure right to be forgotten GDPR Article 17",
                    "right to data portability requirements machine readable format",
                    "erasure of personal data and portability rights"
                ],
                "Data Processing Agreement (DPA) Requirement": [
                    "data processing agreement DPA requirements processor GDPR Article 28",
                    "contractual obligations between controller and processor clauses",
                    "mandatory processor clauses and subprocessor flow-down"
                ],
                "Transparency & Disclosures": [
                    "transparency information communication GDPR Article 12 13 14",
                    "privacy policy disclosures to data subjects clear language",
                    "information to be provided to data subjects transparent information"
                ],
                "Subprocessors Consent & Flow-down": [
                    "subprocessor authorization prior written consent controller GDPR",
                    "flow down of data protection obligations to subprocessors",
                    "rules for engaging other processors sub-processing"
                ],
                "Anonymization/Pseudonymization Standards": [
                    "anonymisation and pseudonymisation techniques data protection",
                    "definition of pseudonymisation GDPR security measure",
                    "de-identification of personal data standards and guidance"
                ],
                "Children's Data Protections": [
                    "conditions applicable to child consent GDPR Article 8 parental consent",
                    "processing of children personal data age requirements verification",
                    "information security and consent rules for minors"
                ],
                # Export Control Compliance Tests
                "Item Classification (Dual-use/Military)": [
                    "export control item classification dual-use military list ECCN",
                    "classification of strategic goods technology control list",
                    "determining dual-use or military status of items"
                ],
                "Sanctioned Destinations Prohibition": [
                    "sanctioned destinations countries embargoes export restrictions",
                    "prohibited exports to embargoed jurisdictions and territories",
                    "trade sanctions compliance and export prohibitions"
                ],
                "Restricted/Denied Parties Checks": [
                    "denied parties list restricted parties screening compliance",
                    "sanctioned entity screening list of persons groups and entities",
                    "restricted party screening requirements export controls"
                ],
                "End-Use Verification (Military/WMD)": [
                    "end-use and end-user controls military WMD proliferation",
                    "end-use certificate requirement export licensing",
                    "proliferation of weapons of mass destruction end-user screening"
                ],
                "Export License Responsibility": [
                    "export authorization licensing requirements responsibility",
                    "applying for export licenses permits strategic goods",
                    "obligations for obtaining and maintaining export licenses"
                ],
                "Intangible Technology Control": [
                    "intangible transfer of technology ITT control software electronic transfer",
                    "technical assistance export controls controlled technology transmission",
                    "controls on digital transmission of technical data"
                ],
                "Record-Keeping Requirements (e.g. 5 years)": [
                    "record-keeping requirements export control documentation five years",
                    "retention of commercial documents export registers invoices",
                    "maintenance of records for export transactions compliance"
                ],
                "Violations Reporting": [
                    "reporting export violations voluntary self-disclosure penalties",
                    "notification of export control breaches and compliance failures",
                    "reporting requirements for export non-compliance"
                ],
                "Subcontractor Export Flow-Down": [
                    "flow down of export control obligations to subcontractors third parties",
                    "contractual provisions for subcontractor export control compliance",
                    "subcontractor requirements and strategic trade restrictions"
                ],
                "Export Auditing Rights": [
                    "export compliance auditing rights inspections and access",
                    "right to audit and review subcontractor export controls",
                    "internal audit program and export control compliance reviews"
                ]
            }

            def process_mappings(mappings):
                updated = []
                for f in mappings:
                    rag_context = []
                    if vector_store:
                        # Get expanded queries for this test
                        queries = expanded_queries_mapping.get(f["test_name"])
                        if not queries:
                            queries = [
                                f"{f['test_name']} compliance regulations",
                                f"{f['test_name']} legal requirements",
                                f"{f.get('contract_excerpt', '')[:150]}"
                            ]
                        
                        # Fetch candidate chunks from Elasticsearch for all 3 queries
                        combined_docs = []
                        seen_content = set()
                        for q in queries:
                            try:
                                docs = vector_store.similarity_search(query=q, k=10)
                                for doc in docs:
                                    if doc.page_content not in seen_content:
                                        seen_content.add(doc.page_content)
                                        combined_docs.append(doc)
                            except Exception as ex:
                                logger.warning("RAG query search failed: %s", ex)
                        
                        # Rerank top 20 candidate chunks against the contract clause text/evidence using Cross-Encoder
                        candidate_docs = combined_docs[:20]
                        contract_text_for_rerank = f.get("contract_excerpt") or f.get("target_clause") or f.get("test_name") or ""
                        
                        if self.cross_encoder and candidate_docs and contract_text_for_rerank:
                            try:
                                pairs = [(contract_text_for_rerank, doc.page_content) for doc in candidate_docs]
                                scores = self.cross_encoder.predict(pairs)
                                scored_docs = sorted(zip(candidate_docs, scores), key=lambda x: x[1], reverse=True)
                                ranked_docs = [doc for doc, score in scored_docs]
                            except Exception as ex:
                                logger.warning("Cross-Encoder scoring failed: %s", ex)
                                ranked_docs = candidate_docs
                        else:
                            ranked_docs = candidate_docs
                        
                        # Return the parent context (parent_text) of the top 2 ranked chunks
                        top_docs = ranked_docs[:2]
                        for doc in top_docs:
                            source = doc.metadata.get("source_name", "Official Regulations")
                            p_text = doc.metadata.get("parent_text") or doc.page_content
                            
                            # Truncate parent text to a reasonable context window centered around the child chunk
                            if len(p_text) > 15000:
                                child_content = doc.page_content
                                if "\n\n" in child_content:
                                    parts = child_content.split("\n\n", 1)
                                    child_content = parts[1]
                                    
                                idx = p_text.find(child_content[:100])
                                if idx == -1:
                                    idx = p_text.find(child_content[:30])
                                    
                                if idx != -1:
                                    start_idx = max(0, idx - 7000)
                                    end_idx = min(len(p_text), idx + len(child_content) + 7000)
                                    prefix = "... [Truncated Parent Context] ...\n" if start_idx > 0 else ""
                                    suffix = "\n... [Truncated Parent Context] ..." if end_idx < len(p_text) else ""
                                    p_text = f"{prefix}{p_text[start_idx:end_idx]}{suffix}"
                                else:
                                    p_text = p_text[:15000] + "\n... [Truncated Parent Context] ..."
                            
                            art_num = doc.metadata.get("article_number")
                            art_str = f" ({art_num})" if art_num else ""
                            provision_type = doc.metadata.get("provision_type", "")
                            hierarchy = doc.metadata.get("full_hierarchy", "")
                            rag_context.append(
                                f"Source: {source}{art_str}\n"
                                f"Provision Type: {provision_type}\n"
                                f"Hierarchy: {hierarchy}\n"
                                f"Excerpt: {p_text}"
                            )
                    f["rag_context"] = rag_context
                    updated.append(f)
                return updated

            return {
                "privacy_mappings": process_mappings(state.get("privacy_mappings", [])),
                "export_mappings": process_mappings(state.get("export_mappings", []))
            }

        # Node 7: Authoritative Verification against provided official PDFs
        async def verification_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Verification Node")
            findings = state.get("privacy_findings", []) + state.get("export_findings", [])
            verified = []
            
            for f in findings:
                rag_str = "\n\n".join(f.get("rag_context", []))
                
                prompt = (
                    "You are the authoritative verification agent. Validate the Deviation Gap identified in the previous step "
                    "using only the provided official regulatory RAG context from the embedded PDFs. "
                    "If the cited regulatory basis is not present in the RAG context, correct the finding to not-applicable or partial. "
                    "Your Verification Citation must identify the source document, article/section, and hierarchy from the RAG context. "
                    "Do not cite websites or unstated legal knowledge.\n\n"
                    f"FINDING:\n- Test: {f['test_name']}\n- Status: {f['status']}\n- Explanation: {f['explanation']}\n- Evidence: {f['evidence']}\n"
                    f"- Target Clause: {f.get('target_clause', '')}\n- Contract Excerpt: {f.get('contract_excerpt', '')}\n"
                    f"- Regulatory Basis: {f.get('regulatory_basis', '')}\n- Deviation Gap: {f.get('deviation_gap', '')}\n\n"
                    f"OFFICIAL REGULATORY RAG CONTEXT:\n{rag_str or 'None'}"
                )
                
                structured_llm = llm.with_structured_output(VerifiedFindingItemSchema)
                verified_item = structured_llm.invoke(prompt)
                
                v_dict = verified_item.model_dump()
                # Ensure the high-precision legal analysis fields carry over from the finding if not updated
                for field in ["target_clause", "contract_excerpt", "regulatory_basis", "deviation_gap", "source_page", "source_section", "source_clause_id", "source_excerpt"]:
                    if not v_dict.get(field) and f.get(field):
                        v_dict[field] = f[field]
                verified.append(v_dict)

            return {
                "verification_results": verified
            }

        # Node 6: Qualitative Decision and Redline proposal
        def decision_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Decision Node")
            prompt = (
                "You are the Lead Legal Compliance Decision Agent. Your role is to formulate a final qualitative "
                "decision (PASS/FAIL) and propose redlines for all failed compliance findings.\n"
                "Ensure all suggested redlines specify clearly the replacement language needed.\n\n"
                "Operating Rules & Guardrails:\n"
                "- State only objective, verifiable facts based on the contract text and verification results.\n"
                "- Explicitly include a legal disclaimer exactly: 'Disclaimer: This review is for informational purposes only "
                "and does not constitute formal legal advice. Please consult with qualified legal counsel.'\n"
                "- Cite the exact source_page, source_section, source_clause_id, and source_excerpt for each item from the SOURCE MAP.\n"
                "- For every generated item in clause_analyses, risk_assessments, compliance_findings, negotiation_strategies, and missing_protections, "
                "ensure you populate the following fields with their exact matched coordinates:\n"
                "  * target_clause\n"
                "  * contract_excerpt\n"
                "  * regulatory_basis\n"
                "  * deviation_gap\n"
                "- To guarantee visual display on the frontend, also append a formatted 'Precision Analysis Details' section at the end of:\n"
                "  * clause_analyses item's 'summary' field\n"
                "  * risk_assessments item's 'rationale' field\n"
                "  * compliance_findings item's 'explanation' field\n"
                "  * negotiation_strategies item's 'rationale' field\n"
                "  * missing_protections item's 'why_missing' field\n"
                "Format the appended section exactly like this:\n"
                "\\n\\n**Precision Analysis Details:**\\n"
                "- **Target Clause**: [value of target_clause]\\n"
                "- **Contract Excerpt**: \\\"[value of contract_excerpt]\\\"\\n"
                "- **Regulatory Basis**: [value of regulatory_basis]\\n"
                "- **Deviation Gap**: [value of deviation_gap]\n\n"
                f"VERIFIED FINDINGS:\n{state['verification_results']}\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}\n\n"
                f"SOURCE MAP:\n{state['source_context']}"
            )
            
            structured_llm = llm.with_structured_output(DecisionNodeResponse)
            decision_resp = structured_llm.invoke(prompt)
            
            return {
                "redlines": [n.model_dump() for n in decision_resp.negotiation_strategies],
                "final_decision": {
                    "summary": decision_resp.summary,
                    "clause_analyses": [c.model_dump() for c in decision_resp.clause_analyses],
                    "risk_assessments": [r.model_dump() for r in decision_resp.risk_assessments],
                    "compliance_findings": [cf.model_dump() for cf in decision_resp.compliance_findings],
                    "negotiation_strategies": [n.model_dump() for n in decision_resp.negotiation_strategies],
                    "missing_protections": [m.model_dump() for m in decision_resp.missing_protections],
                }
            }

        # Define graph transitions
        workflow.add_node("jurisdiction_node", jurisdiction_node)
        workflow.add_node("contract_map_node", contract_map_node)
        workflow.add_node("coordinate_node", coordinate_node)
        workflow.add_node("rag_node", rag_node)
        workflow.add_node("privacy_node", privacy_node)
        workflow.add_node("export_node", export_node)
        workflow.add_node("verification_node", verification_node)
        workflow.add_node("decision_node", decision_node)

        workflow.set_entry_point("jurisdiction_node")
        workflow.add_edge("jurisdiction_node", "contract_map_node")
        workflow.add_edge("contract_map_node", "coordinate_node")
        workflow.add_edge("coordinate_node", "rag_node")
        workflow.add_edge("rag_node", "privacy_node")

        def check_export_trigger(state: AgentState):
            if state.get("export_triggered", False):
                return "export_node"
            return "verification_node"

        workflow.add_conditional_edges(
            "privacy_node",
            check_export_trigger,
            {
                "export_node": "export_node",
                "verification_node": "verification_node"
            }
        )

        workflow.add_edge("export_node", "verification_node")
        workflow.add_edge("verification_node", "decision_node")
        workflow.add_edge("decision_node", END)

        return workflow.compile()

    async def analyze_contract(self, file_path: str) -> ContractReviewOutput:
        document = await self._load_document(file_path)
        return await self.analyze_contract_text(
            contract_text=document.text,
            filename=document.filename,
        )

    async def analyze_contract_text(
        self,
        contract_text: str,
        filename: str = "",
        source_context: str = "",
    ) -> ContractReviewOutput:
        initial_state = {
            "contract_text": contract_text,
            "source_context": source_context,
            "contract_map": [],
            "privacy_mappings": [],
            "export_mappings": [],
            "jurisdiction_profile": {},
            "privacy_findings": [],
            "export_findings": [],
            "verification_results": [],
            "redlines": [],
            "final_decision": {},
            "export_triggered": False
        }
        
        # Run graph sequentially
        final_state = await self.graph.ainvoke(initial_state)
        decision = final_state.get("final_decision", {})
        
        # Map findings to response classes
        clause_analyses = [ClauseAnalysis.model_validate(x) for x in decision.get("clause_analyses", [])]
        risk_assessments = [RiskAssessment.model_validate(x) for x in decision.get("risk_assessments", [])]
        compliance_findings = [ComplianceFinding.model_validate(x) for x in decision.get("compliance_findings", [])]
        negotiation_strategies = [NegotiationStrategy.model_validate(x) for x in decision.get("negotiation_strategies", [])]
        missing_protections = [MissingProtection.model_validate(x) for x in decision.get("missing_protections", [])]
        
        return ContractReviewOutput(
            summary=decision.get("summary", "No summary available."),
            clause_analyses=clause_analyses,
            risk_assessments=risk_assessments,
            compliance_findings=compliance_findings,
            negotiation_strategies=negotiation_strategies,
            missing_protections=missing_protections,
            source_filename=filename,
            document_type="contract",
        )

    async def assess_risks(self, file_path: str) -> list[RiskAssessment]:
        # Re-use the graph execution for risk assessment compatibility
        review = await self.analyze_contract(file_path)
        return review.risk_assessments

    async def generate_nda(self, description: str) -> NDAGenerationOutput:
        system_message = (
            "You are a legal drafting assistant. Draft a practical, business-friendly NDA from the user's description. "
            "Return only JSON that matches the schema exactly. "
            f"{schema_instructions(NDAGenerationOutput)}"
        )
        response = await self._chat_json(
            model=self.model,
            system_message=system_message,
            user_content=description,
        )
        return self._parse_model(response, NDAGenerationOutput)

    async def _chat_json(
        self,
        model: str,
        system_message: str,
        user_content: str | list[dict[str, Any]],
    ) -> str:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ]
        try:
            logger.info("OpenAI request: model=%s, sys_len=%d, user_len=%d", model, len(system_message), len(str(user_content)))
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            resp_id = getattr(response, "id", None) or (response.to_dict().get("id") if hasattr(response, "to_dict") else None)
            logger.info("OpenAI response received: id=%s", resp_id)
            content = response.choices[0].message.content or "{}"
            return content.strip()
        except Exception:
            logger.exception("OpenAI request failed for model %s", model)
            raise

    def _parse_model(self, raw_json: str, schema: type):
        try:
            sanitized_json = self._sanitize_json_for_schema(raw_json, schema)
            return schema.model_validate_json(sanitized_json)
        except Exception:
            logger.exception("Failed to parse OpenAI JSON for %s", schema.__name__)
            return schema.model_validate(self._fallback_payload(schema))

    def _sanitize_json_for_schema(self, raw_json: str, schema: type) -> str:
        try:
            payload = json.loads(raw_json)
        except Exception:
            return raw_json

        if isinstance(payload, dict):
            payload = self._coerce_nullable_citations(payload)
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            return raw_json

    def _coerce_nullable_citations(self, payload: dict[str, Any]) -> dict[str, Any]:
        items = payload.get("items")
        if not isinstance(items, list):
            return payload

        for item in items:
            if not isinstance(item, dict):
                continue
            for field in ("source_section", "source_clause_id", "source_excerpt"):
                if item.get(field) is None:
                    item[field] = ""
        return payload

    def _fallback_payload(self, schema: type) -> dict[str, Any]:
        fallback = {
            "NDAGenerationOutput": {
                "title": "Non-Disclosure Agreement",
                "party_a": "Party A",
                "party_b": "Party B",
                "effective_date": "Effective Date",
                "confidentiality_terms": [],
                "mutuality": "mutual",
                "governing_law": "Governing law to be specified",
                "full_text": "",
            },
        }
        return fallback.get(schema.__name__, {})

    async def _load_document(self, file_path: str) -> DocumentPayload:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        suffix = path.suffix.lower()
        if suffix in {".txt", ".text", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            return DocumentPayload(filename=path.name, file_type="text", text=text, content=text)

        if suffix == ".pdf":
            return self._load_pdf(path)

        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            content = self._image_content(path)
            return DocumentPayload(
                filename=path.name,
                file_type="image",
                text="",
                content=content,
            )

        text = path.read_text(encoding="utf-8", errors="replace")
        return DocumentPayload(filename=path.name, file_type="text", text=text, content=text)

    def _load_pdf(self, path: Path) -> DocumentPayload:
        doc = fitz.open(path)
        try:
            page_texts: list[str] = []
            page_images: list[dict[str, Any]] = []
            for index, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    page_texts.append(f"[Page {index + 1}]\n{text}")
                elif index < 3:
                    page_images.append(self._page_image_content(page, index + 1))

            extracted_text = "\n\n".join(page_texts).strip()
            if extracted_text:
                return DocumentPayload(
                    filename=path.name,
                    file_type="pdf",
                    text=extracted_text,
                    page_count=max(doc.page_count, 1),
                    content=extracted_text,
                )

            return DocumentPayload(
                filename=path.name,
                file_type="pdf",
                text="",
                page_count=max(doc.page_count, 1),
                content=page_images,
            )
        finally:
            doc.close()

    def _page_image_content(self, page: fitz.Page, page_number: int) -> dict[str, Any]:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_bytes = pixmap.tobytes("png")
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded}"},
        }

    def _image_content(self, path: Path) -> list[dict[str, Any]]:
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        mime = "image/png"
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif path.suffix.lower() == ".webp":
            mime = "image/webp"
        return [
            {"type": "text", "text": "Analyze this contract image and extract the key legal clauses and risks."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]
