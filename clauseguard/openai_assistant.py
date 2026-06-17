from __future__ import annotations

import base64
import json
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict, Literal
import typing
import types

import fitz
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langchain_elasticsearch import ElasticsearchStore
from elasticsearch import Elasticsearch
from langgraph.graph import StateGraph, END
from sentence_transformers import CrossEncoder
from pydantic import BaseModel, Field

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


APPLICABILITY_GATES = {
    "Children's Data Protections": ["child", "children", "minor", "student", "school", "parental consent", "age verification", "under 13", "under 16", "guardian"],
    "Direct Marketing Restrictions": ["marketing", "advertising", "promotional", "profiling", "targeted advertising", "commercial communications"],
    "Automated Decision Making / Profiling": ["automated decision", "profiling", "algorithm", "algorithmic", "ai decision"],
    "Consent Management": ["consent", "opt-in", "opt-out", "withdraw consent"],
}


RETRIEVAL_MAPS = {
    # Privacy Compliance Tests
    "Legal Basis for Processing": {
        "keywords": ["lawful", "basis", "processing", "legal basis", "consent", "legitimate interest", "contract performance"],
        "concepts": ["lawful basis for processing", "processing legal grounds", "GDPR Article 6 requirements"]
    },
    "Consent Management": {
        "keywords": ["consent", "withdraw", "withdrawal", "opt-in", "opt-out", "freely given"],
        "concepts": ["consent withdrawal mechanisms", "obtaining user consent", "consent conditions"]
    },
    "Direct Marketing Restrictions": {
        "keywords": ["marketing", "advertising", "opt-out", "promotional", "direct marketing", "objection"],
        "concepts": ["unsolicited marketing communications", "direct marketing opt-out rights", "marketing restriction laws"]
    },
    "Cross-Border Safeguards (e.g. Standard Contractual Clauses)": {
        "keywords": ["standard contractual clauses", "sccs", "transfer", "cross-border", "safeguards", "adequacy", "uk addendum", "framework", "third country"],
        "concepts": ["international data transfer mechanisms", "transfer of personal data to third countries", "cross-border transfer safeguards"]
    },
    "Data Retention & Deletion": {
        "keywords": ["retention period", "retention schedule", "return or delete", "erase upon request", "destroy complete", "delete termination", "deletion return", "purge data"],
        "concepts": ["right to erasure", "return or deletion", "retention limitation", "disposal of personal data"]
    },
    "Technical & Organizational Security Measures": {
        "keywords": ["technical", "organizational", "security", "confidentiality", "integrity", "availability", "protect", "incident", "measures", "toms"],
        "concepts": ["technical and organizational measures", "security of processing", "appropriate security controls"]
    },
    "Data Breach Notification Timeframe": {
        "keywords": ["72 hours", "undue delay", "seventy-two", "breach notification", "notify breach", "notification period", "notification timeframe"],
        "concepts": ["incident response timing", "regulator notification timeframe", "personal data breach communication timeframe"]
    },
    "DPO Designation": {
        "keywords": ["data protection officer", "dpo", "privacy officer", "compliance officer"],
        "concepts": ["designation of data protection officer", "mandatory dpo appointment", "position of dpo"]
    },
    "Data Subject Rights - Access/Rectification": {
        "keywords": ["access request", "correction", "rectification", "data subject", "erase", "access"],
        "concepts": ["right of access by data subject", "rectification rights", "data subject request handling"]
    },
    "Data Subject Rights - Erasure/Portability": {
        "keywords": ["delete", "deletion", "erase", "erasure", "portability", "data subject", "right to erasure"],
        "concepts": ["erasure rights", "portability rights", "data subject request handling"]
    },
    "Data Processing Agreement (DPA) Requirement": {
        "keywords": ["data processing agreement", "data processing addendum", "dpa", "controller", "processor", "subprocessor", "sub-processor"],
        "concepts": ["dpa requirements", "processor obligations", "controller processor relationship"]
    },
    "Transparency & Disclosures": {
        "keywords": ["privacy notice", "transparency", "clear language", "disclose", "privacy policy", "information provided"],
        "concepts": ["transparency information", "information disclosures", "clear and plain language"]
    },
    "Subprocessors Consent & Flow-down": {
        "keywords": ["sub-processor", "subprocessor", "sub-processing", "written agreement", "flow down", "liable", "remain liable", "authorisation", "authorization"],
        "concepts": ["subprocessor authorization", "flow down of data protection obligations", "rules for engaging other processors"]
    },
    "Anonymization/Pseudonymization Standards": {
        "keywords": ["anonym", "pseudonym", "de-identify", "mask", "obfuscate"],
        "concepts": ["anonymisation standards", "pseudonymisation techniques"]
    },
    "Children's Data Protections": {
        "keywords": ["child", "children", "minor", "parental consent"],
        "concepts": ["children data protection", "consent for minors"]
    },
    # Export Control Compliance Tests
    "Item Classification (Dual-use/Military)": {
        "keywords": ["classification", "dual-use", "dual use", "military list", "eccn", "category", "control list"],
        "concepts": ["item classification", "strategic goods classification"]
    },
    "Sanctioned Destinations Prohibition": {
        "keywords": ["sanctioned", "embargo", "prohibited", "restricted destination", "countries", "territories"],
        "concepts": ["sanctioned destinations", "embargoed jurisdictions"]
    },
    "Restricted/Denied Parties Checks": {
        "keywords": ["denied parties", "restricted parties", "screening", "list of persons", "sanctioned entity"],
        "concepts": ["denied party screening", "restricted party checks"]
    },
    "End-Use Verification (Military/WMD)": {
        "keywords": ["end-use", "end-user", "military", "wmd", "weapons of mass destruction", "certificate"],
        "concepts": ["end-use verification", "military end-use controls"]
    },
    "Export License Responsibility": {
        "keywords": ["license", "permit", "responsibility", "obtain", "authorization", "authority"],
        "concepts": ["export licensing responsibility", "obtaining export licenses"]
    },
    "Intangible Technology Control": {
        "keywords": ["intangible", "transfer of technology", "software", "electronic transfer", "transmission", "technical data"],
        "concepts": ["intangible technology transfer", "electronic transfer controls"]
    },
    "Record-Keeping Requirements (e.g. 5 years)": {
        "keywords": ["record", "keeping", "records", "retention", "5 years", "five years", "register", "invoice"],
        "concepts": ["export control record-keeping", "retention of transaction records"]
    },
    "Violations Reporting": {
        "keywords": ["violation", "violations", "reporting", "self-disclosure", "breach", "non-compliance"],
        "concepts": ["reporting export violations", "voluntary self-disclosure"]
    },
    "Subcontractor Export Flow-Down": {
        "keywords": ["subcontractor", "flow-down", "flow down", "third party", "obligations", "provision"],
        "concepts": ["subcontractor export compliance", "export control flow-down"]
    },
    "Export Auditing Rights": {
        "keywords": ["audit", "auditing", "rights", "inspection", "access", "review"],
        "concepts": ["export auditing rights", "right to audit subcontractors"]
    }
}


EXPANDED_QUERIES_MAP = {
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


# ----------------------------------------------------------------------
# Pydantic Schemas for Structured Node Outputs
# ----------------------------------------------------------------------

class JurisdictionProfileSchema(BaseModel):
    privacy_jurisdiction: str = Field(default="None", description="The primary privacy jurisdiction identified, e.g. EU or Australia or None")
    export_jurisdiction: str = Field(default="None", description="The primary export control jurisdiction identified, e.g. EU or Australia or None")
    privacy_triggered: bool = Field(default=False, description="True only if the contract contains personal-data processing, controller/processor, cross-border data transfer, privacy notice, data security, or similar privacy-regulated obligations tied to the supported EU/Australia regimes.")
    export_triggered: bool = Field(default=False, description="True if export controls apply/are triggered by the contract details (e.g. transfer of technical goods, software, or cross-border tech data)")
    rationale: str = Field(default="", description="Brief contract-grounded rationale for which supported regulatory regimes are or are not triggered.")


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


class EvidenceControlAssessment(BaseModel):
    control: str = Field(description="Compliance control being reviewed.")
    applicable: bool = Field(description="Whether the control is triggered by the contract facts.")
    applicability_reason: str = Field(description="Contract-grounded reason for applicability or non-applicability.")
    contract_evidence: list[str] = Field(default_factory=list, description="Verbatim contract excerpts reviewed for this control.")
    law_evidence: list[str] = Field(default_factory=list, description="Specific official-regulation excerpts or article references reviewed.")
    evidence_status: str = Field(description="PRESENT, PARTIALLY_PRESENT, ABSENT, or NOT_APPLICABLE.")
    adequacy_evaluation: str = Field(description="Assessment of whether the contract evidence addresses the regulatory obligation and whether it is materially weaker.")
    finding: str = Field(description="Final evidence-grounded finding.")
    remediation: str = Field(default="", description="Remediation only for PARTIALLY_PRESENT or ABSENT controls.")
    target_clause: str = Field(default="", description="Specific contract section or paragraph number.")
    regulatory_basis: str = Field(default="", description="Specific regulation article or section from official RAG context.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    is_relevant_match: bool = Field(default=True, description="True if the contract evidence is a relevant match for the control, False if it is a false positive (e.g. general storage or transfer clause for deletion control).")


class EvidenceAssessmentSchema(BaseModel):
    controls: list[EvidenceControlAssessment] = Field(description="Evidence-grounded assessment for every control.")


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
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


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
    privacy_triggered: bool
    export_triggered: bool
    document_type: str


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
            temperature=0.0,
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

    def _reconstruct_clauses(self, contract_text: str, source_context: str) -> list[dict]:
        # Parse source context lines
        context_lines = []
        if source_context:
            for line in source_context.splitlines():
                if not line.strip():
                    continue
                parts = {}
                for item in line.split(" | "):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        parts[k.strip()] = v.strip()
                context_lines.append(parts)
                
        # Reconstruct blocks
        # Note: contract_text blocks are joined by "\n\n" and prefixed with [clause_type]
        blocks = contract_text.split("\n\n")
        clauses = []
        
        for idx, block in enumerate(blocks):
            block = block.strip()
            if not block:
                continue
            clause_type = "other"
            text = block
            match = re.match(r"^\[([^\]]+)\]\s*(.*)$", block, re.DOTALL)
            if match:
                clause_type = match.group(1)
                text = match.group(2).strip()
                
            # Match with context line
            meta = {}
            if context_lines:
                if idx < len(context_lines):
                    meta = context_lines[idx]
                else:
                    for cl in context_lines:
                        exc = cl.get("excerpt", "")
                        if exc.replace("...", "") in text:
                            meta = cl
                            break
            
            # Build clause representation
            clauses.append({
                "clause_id": meta.get("clause_id", f"clause_{idx}"),
                "page_number": int(meta.get("page", 1)) if meta.get("page") and meta.get("page").isdigit() else 1,
                "section_number": meta.get("section", ""),
                "clause_type": clause_type,
                "text": text
            })
            
        if not clauses:
            # Fallback to splitting by paragraphs if empty
            segments = re.split(r"\n\s*\n", contract_text)
            for idx, seg in enumerate(segments):
                seg = seg.strip()
                if len(seg) > 10:
                    clauses.append({
                        "clause_id": f"clause_{idx}",
                        "page_number": 1,
                        "section_number": f"Paragraph {idx+1}",
                        "clause_type": "other",
                        "text": seg
                    })
        return clauses

    def _calibrate_confidence(self, status: str, has_evidence: bool, applicability_confirmed: bool, adequacy_evaluated: bool, current_confidence: float) -> float:
        status_upper = status.upper().replace(" ", "_").replace("-", "_")
        if status_upper == "ABSENT":
            return min(current_confidence, 0.40)
        elif status_upper == "PARTIALLY_PRESENT":
            return min(current_confidence, 0.70)
        elif status_upper == "PRESENT":
            # 90%+ confidence only when applicability confirmed, evidence retrieved and cited, adequacy evaluated
            if applicability_confirmed and has_evidence and adequacy_evaluated:
                return min(current_confidence, 0.95)
            else:
                return min(current_confidence, 0.85)
        return current_confidence

    def _hybrid_retrieve_and_rank(self, control_name: str, all_clauses: list[dict], queries: list[str]) -> list[dict]:
        control_map = RETRIEVAL_MAPS.get(control_name, {})
        keywords = control_map.get("keywords", [])
        concepts = control_map.get("concepts", [])
        
        # 1. Keyword search matches
        keyword_matches = []
        for c in all_clauses:
            text_lower = c["text"].lower()
            matches = 0
            for kw in keywords:
                if " " in kw:
                    if kw.lower() in text_lower:
                        matches += 1
                else:
                    if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                        matches += 1
            if matches > 0:
                keyword_matches.append({
                    "clause": c,
                    "score": matches / len(keywords),
                    "strategy": "keyword"
                })
                
        # 2. Concept search matches
        concept_matches = []
        for c in all_clauses:
            text_lower = c["text"].lower()
            matches = 0
            for cp in concepts:
                if cp.lower() in text_lower:
                    matches += 1
            if matches > 0:
                concept_matches.append({
                    "clause": c,
                    "score": matches / len(concepts),
                    "strategy": "concept"
                })
                
        # 3. Semantic search matches (CrossEncoder)
        semantic_matches = []
        if self.cross_encoder and queries:
            clause_scores = {}
            for q in queries:
                try:
                    pairs = [(q, c["text"]) for c in all_clauses]
                    scores = self.cross_encoder.predict(pairs)
                    for idx, score in enumerate(scores):
                        clause_scores[idx] = max(clause_scores.get(idx, -99.0), float(score))
                except Exception as ex:
                    logger.warning("CrossEncoder scoring failed: %s", ex)
            
            for idx, c in enumerate(all_clauses):
                score = clause_scores.get(idx, -99.0)
                # Sigmoid scaling
                scaled_score = 1.0 / (1.0 + math.exp(-score)) if score != -99.0 else 0.0
                semantic_matches.append({
                    "clause": c,
                    "score": scaled_score,
                    "strategy": "semantic"
                })
        else:
            # Fallback semantic score based on keywords and concepts if cross_encoder is missing
            for idx, c in enumerate(all_clauses):
                semantic_matches.append({
                    "clause": c,
                    "score": 0.1,
                    "strategy": "semantic"
                })
                
        # Union the results
        union_dict = {}
        for item in keyword_matches + concept_matches + semantic_matches:
            cid = item["clause"]["clause_id"]
            if cid not in union_dict:
                union_dict[cid] = item
            else:
                if item["score"] > union_dict[cid]["score"]:
                    union_dict[cid] = item
                    
        # Sort and rank descending
        ranked_list = sorted(union_dict.values(), key=lambda x: x["score"], reverse=True)

        # Rerank/Boost based on heading/section keywords matching control domain
        boosted_list = []
        for item in ranked_list:
            c = item["clause"]
            score = item["score"]
            text_prefix = c["text"][:100].lower()
            section_lower = str(c.get("section_number", "")).lower()
            
            boost = 0.0
            if "Retention" in control_name or "Deletion" in control_name:
                if any(kw in section_lower or kw in text_prefix for kw in ["retention", "deletion", "terminate", "termination", "return", "destroy"]):
                    boost = 0.3
            elif "Breach" in control_name or "Notification" in control_name:
                if any(kw in section_lower or kw in text_prefix for kw in ["breach", "incident", "notify", "notification", "security"]):
                    boost = 0.3
                    
            item["score"] = score + boost
            boosted_list.append(item)

        ranked_list = sorted(boosted_list, key=lambda x: x["score"], reverse=True)
        return ranked_list[:3]

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

    def _looks_like_regulatory_coordinate(self, value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        lowered = text.lower()
        return bool(
            lowered.startswith(("article ", "chapter ", "gdpr art", "gdpr article"))
            or lowered in {"chapter ii", "chapter iii", "chapter iv", "chapter v"}
            or "australian privacy principle" in lowered
        )

    def _normalize_evidence_first_item(self, item: dict, coord: dict) -> dict:
        for field in ["target_clause", "contract_excerpt", "source_page", "source_section", "source_clause_id"]:
            if not item.get(field) and coord.get(field):
                item[field] = coord[field]

        if self._looks_like_regulatory_coordinate(item.get("target_clause")):
            item["target_clause"] = ""
        if self._looks_like_regulatory_coordinate(item.get("source_section")):
            item["source_section"] = ""
        if self._looks_like_regulatory_coordinate(item.get("source_clause_id")):
            item["source_clause_id"] = ""

        if not item.get("source_excerpt") and item.get("contract_excerpt"):
            item["source_excerpt"] = item["contract_excerpt"]

        normalized_status = str(item.get("status", "")).lower().replace("_", "-")
        if normalized_status in {"not-applicable", "not applicable", "n/a", "na"}:
            item["status"] = "not-applicable"
            item["severity"] = "info"
            item["target_clause"] = item.get("target_clause") or "Not applicable"
            item["source_excerpt"] = item.get("source_excerpt") or item.get("contract_excerpt") or ""
            return item

        missing = not item.get("contract_excerpt")
        if missing:
            item["target_clause"] = "Missing Protection"
            item["source_page"] = None
            item["source_section"] = ""
            item["source_clause_id"] = ""
            item["source_excerpt"] = ""
            if "missing protection" not in str(item.get("explanation", "")).lower():
                item["explanation"] = f"Missing Protection: {item.get('explanation', '')}".strip()
        return item

    def _split_contract_segments(self, contract_text: str) -> list[str]:
        # Improved regex to catch "Section 8.", "8. Retention", "Article 5" etc.
        segments = re.split(r"\n\s*\n|(?=\n\s*(?:Section|Article|Clause)\s+\d+)|(?=\n\s*\d+\.\s+[A-Z])", contract_text)
        return [segment.strip() for segment in segments if len(segment.strip()) > 20]

    def _detect_document_type(self, contract_text: str) -> str:
        lowered = contract_text.lower()
        dpa_signals = [
            "data processing addendum",
            "data processing agreement",
            "controller",
            "processor",
            "sub-processor",
            "subprocessor",
            "documented instructions",
            "customer personal data",
        ]
        export_signals = [
            "export control",
            "dual-use",
            "dual use",
            "controlled technology",
            "technical data",
            "export license",
            "sanctioned",
        ]
        if sum(1 for signal in dpa_signals if signal in lowered) >= 3:
            return "data_processing_agreement"
        if any(signal in lowered for signal in export_signals):
            return "export_control_agreement"
        return "generic_commercial_contract"

    def _find_semantic_contract_evidence(self, test_name: str, contract_text: str) -> list[str]:
        patterns_by_test = {
            "Technical & Organizational Security Measures": [
                ("technical", "organizational", "security"),
                ("security measures",),
                ("confidentiality", "integrity", "availability"),
                ("protect", "security incident"),
                ("technical and organizational measures",),
                ("appropriate measures", "security"),
                ("toms",),
            ],
            "Data Breach Notification Timeframe": [
                ("72", "security incident"),
                ("seventy-two", "security incident"),
                ("without undue delay", "security incident"),
                ("notify", "security incident"),
                ("notify", "breach"),
            ],
            "Subprocessors Consent & Flow-down": [
                ("sub-processor",),
                ("subprocessor",),
                ("sub-processing",),
                ("written agreement", "sub-processor"),
                ("remain liable", "sub-processor"),
                ("flow", "subprocessor"),
                ("authorisation", "sub-processor"),
                ("authorization", "sub-processor"),
                ("prior", "sub-processor"),
            ],
            "Data Subject Rights - Access/Rectification": [
                ("data subject", "request"),
                ("access", "rectification"),
                ("access", "retrieve"),
                ("data subject", "inquiries"),
                ("correction request",),
                ("support", "data subject"),
                ("assist", "data subject"),
                ("rectify",),
            ],
            "Data Subject Rights - Erasure/Portability": [
                ("delete", "customer personal data"),
                ("erasure",),
                ("portability",),
                ("access", "retrieve", "delete"),
                ("deletion request",),
                ("erase",),
                ("support", "data subject"),
                ("assist", "data subject"),
            ],
            "Data Retention & Deletion": [
                ("delete", "termination"),
                ("deletion", "return"),
                ("retention period",),
                ("retention schedule",),
                ("return or delete",),
                ("erase", "upon request"),
                ("destroy", "completion of services"),
                ("no longer required", "delete"),
            ],
            "Data Processing Agreement (DPA) Requirement": [
                ("controller", "processor"),
                ("documented instructions",),
                ("process", "customer data", "instructions"),
                ("confidentiality", "authorized", "personal data"),
                ("data processing addendum",),
                ("data processing agreement",),
                ("sub-processor", "audit"),
                ("technical", "organizational", "sub-processor"),
            ],
            "Cross-Border Safeguards (e.g. Standard Contractual Clauses)": [
                ("standard contractual clauses",),
                ("sccs",),
                ("international transfer",),
                ("data privacy framework",),
                ("uk addendum",),
                ("swiss", "transfer"),
            ],
            "Legal Basis for Processing": [
                ("lawful", "processing"),
                ("customer", "responsible", "applicable data protection law"),
                ("documented instructions", "comply"),
            ],
            "Consent Management": [
                ("consent",),
            ],
            "Direct Marketing Restrictions": [
                ("direct marketing",),
                ("marketing communication",),
                ("advertising", "opt-out"),
            ],
            "Transparency & Disclosures": [
                ("privacy notice",),
                ("transparent",),
                ("disclos", "personal data"),
            ],
            "DPO Designation": [
                ("data protection officer",),
                ("dpo",),
                ("privacy officer",),
            ],
            "Anonymization/Pseudonymization Standards": [
                ("de-identified",),
                ("pseudonym",),
                ("anonym",),
            ],
            "Children's Data Protections": [
                ("child",),
                ("children",),
                ("minor",),
            ],
        }
        patterns = patterns_by_test.get(test_name, [])
        if not patterns:
            return []
        evidence: list[str] = []
        for segment in self._split_contract_segments(contract_text):
            lowered = segment.lower()
            if any(all(term in lowered for term in pattern) for pattern in patterns):
                evidence.append(segment[:1800])
            if len(evidence) >= 4:
                break
        return evidence

    def _evidence_status_to_review_status(self, applicable: bool, evidence_status: str) -> tuple[str, str]:
        normalized = evidence_status.upper().replace(" ", "_").replace("-", "_")
        if not applicable or normalized == "NOT_APPLICABLE":
            return "not-applicable", "info"
        if normalized == "PRESENT":
            return "pass", "info"
        if normalized == "CONTRADICTED":
            return "partial", "medium"
        if normalized == "PARTIALLY_PRESENT":
            return "partial", "medium"
        return "fail", "high"

    def _confidence_cap(self, evidence_status: str, contract_evidence: list[str], confidence: float) -> float:
        normalized = evidence_status.upper().replace(" ", "_").replace("-", "_")
        if normalized == "CONTRADICTED":
            return min(confidence, 0.20)
        if not contract_evidence:
            return min(confidence, 0.30)
        if normalized == "PARTIALLY_PRESENT":
            return min(confidence, 0.60)
        return min(confidence, 0.95)

    def _semantic_evidence_status_override(self, control: str, evidence: list[str], current_status: str, document_type: str = "") -> str:
        if not evidence:
            return current_status
        joined = "\n".join(evidence).lower()
        normalized = current_status.upper().replace(" ", "_").replace("-", "_")
        if normalized not in {"ABSENT", "PARTIALLY_PRESENT"}:
            return current_status
        contradicted_value = "PRESENT" if normalized == "PARTIALLY_PRESENT" else "CONTRADICTED"
        if control == "Data Processing Agreement (DPA) Requirement" and document_type == "data_processing_agreement":
            dpa_score = sum(
                1
                for term in ["controller", "processor", "instructions", "sub-processor", "subprocessor", "audit", "technical", "organizational", "confidentiality"]
                if term in joined
            )
            if dpa_score >= 3:
                return contradicted_value
        if control == "Technical & Organizational Security Measures":
            if "technical" in joined and "organizational" in joined and "security" in joined:
                return contradicted_value
        if control == "Data Breach Notification Timeframe":
            if ("72" in joined or "seventy-two" in joined) and ("security incident" in joined or "breach" in joined):
                return contradicted_value
            if "notify" in joined and ("security incident" in joined or "breach" in joined):
                return "PARTIALLY_PRESENT"
        if control == "Subprocessors Consent & Flow-down":
            if ("sub-processor" in joined or "subprocessor" in joined) and ("written agreement" in joined or "remain liable" in joined or "same standard" in joined):
                return contradicted_value
        if control == "Cross-Border Safeguards (e.g. Standard Contractual Clauses)":
            if "standard contractual clauses" in joined or "sccs" in joined or "uk addendum" in joined or "data privacy framework" in joined:
                return contradicted_value
        if control in {"Data Retention & Deletion", "Data Subject Rights - Erasure/Portability"}:
            if any(term in joined for term in ["delete", "deletion", "erase", "destroy", "return"]) and any(term in joined for term in ["termination", "retrieve", "customer personal data", "no longer required", "service"]):
                return contradicted_value
        if control == "Data Processing Agreement (DPA) Requirement":
            if "controller" in joined and "processor" in joined and ("documented instructions" in joined or "instructions" in joined):
                return contradicted_value
        if control == "Data Subject Rights - Access/Rectification":
            if ("data subject" in joined and ("request" in joined or "inquiries" in joined or "access" in joined or "assist" in joined)) or "rectification" in joined or "correction request" in joined:
                return contradicted_value
        if control == "DPO Designation":
            if "data protection officer" in joined or "dpo" in joined or "privacy officer" in joined:
                return contradicted_value
        return current_status

    def _assessment_to_finding(self, assessment: dict, coord: dict, rag_context: list[str], document_type: str = "") -> dict:
        contract_evidence = [str(x).strip() for x in assessment.get("contract_evidence", []) if str(x).strip()]
        if not contract_evidence:
            contract_evidence = [
                str(x).strip()
                for x in coord.get("semantic_contract_evidence", [])
                if str(x).strip()
            ]
        law_evidence = [str(x).strip() for x in assessment.get("law_evidence", []) if str(x).strip()]
        applicable = bool(assessment.get("applicable"))
        evidence_status = assessment.get("evidence_status", "ABSENT")
        if evidence_status in {"ABSENT", "PARTIALLY_PRESENT"} and contract_evidence:
            override_status = self._semantic_evidence_status_override(
                assessment.get("control", ""),
                contract_evidence,
                evidence_status,
                document_type=document_type
            )
            if override_status == "CONTRADICTED":
                evidence_status = "PRESENT"
            else:
                evidence_status = override_status
        status, severity = self._evidence_status_to_review_status(applicable, evidence_status)
        
        confidence = float(assessment.get("confidence") or 0.0)
        excerpt = contract_evidence[0] if contract_evidence else ""
        regulatory_basis = assessment.get("regulatory_basis") or (law_evidence[0] if law_evidence else "")
        explanation = (
            f"{assessment.get('finding', '')}\n\n"
            f"Evidence status: {evidence_status}. "
            f"Applicability: {assessment.get('applicability_reason', '')} "
            f"Adequacy: {assessment.get('adequacy_evaluation', '')}"
        ).strip()
        item = {
            "test_name": assessment.get("control", ""),
            "status": status,
            "severity": severity,
            "explanation": explanation,
            "evidence": excerpt,
            "remediation": assessment.get("remediation") if status in {"fail", "partial"} else "No remediation required.",
            "target_clause": assessment.get("target_clause") or coord.get("target_clause", ""),
            "contract_excerpt": excerpt,
            "regulatory_basis": regulatory_basis,
            "deviation_gap": (
                "" if status in {"pass", "not-applicable"}
                else f"Contract evidence is {evidence_status}; regulation requires {regulatory_basis or 'the cited control'}."
            ),
            "source_page": coord.get("source_page"),
            "source_section": coord.get("source_section", ""),
            "source_clause_id": coord.get("source_clause_id", ""),
            "source_excerpt": excerpt,
            "rag_context": rag_context,
            "confidence": confidence,
            
            # vNext fields
            "contract_sections": [assessment.get("target_clause")] if assessment.get("target_clause") else [],
            "contract_evidence_list": contract_evidence,
        }
        return self._normalize_evidence_first_item(item, coord)


    def _verified_to_compliance_finding(self, finding: dict) -> dict:
        evidence = []
        if finding.get("contract_excerpt"):
            evidence.append(finding["contract_excerpt"])
        elif finding.get("evidence"):
            if isinstance(finding["evidence"], list):
                for ev in finding["evidence"]:
                    if ev and str(ev).strip():
                        evidence.append(str(ev).strip())
            else:
                evidence.append(str(finding["evidence"]).strip())
        
        # Parse sections
        sections = []
        if finding.get("contract_sections"):
            sections = [str(s).strip() for s in finding["contract_sections"] if str(s).strip()]
        elif finding.get("target_clause"):
            sections = [str(finding["target_clause"]).strip()]
            
        # Avoid "Section: Not provided" if we have evidence!
        if evidence and (not sections or sections == ["Section: Not provided"]):
            sections = [finding.get("source_section") or "Clause Evidence"]
            
        vnext_status_map = {
            "pass": "PRESENT",
            "partial": "PARTIALLY_PRESENT",
            "fail": "ABSENT",
            "not-applicable": "NOT_APPLICABLE",
            "contradicted": "CONTRADICTED",
            "present": "PRESENT",
            "partially_present": "PARTIALLY_PRESENT",
            "absent": "ABSENT",
            "not_applicable": "NOT_APPLICABLE"
        }
        raw_status = finding.get("status", "not-applicable")
        vnext_status = vnext_status_map.get(str(raw_status).lower().replace("_", "-").replace(" ", "-"), raw_status)
        
        return {
            "requirement": finding.get("test_name", "Compliance control"),
            "status": vnext_status,
            "severity": finding.get("severity", "info"),
            "explanation": finding.get("explanation") or finding.get("verification_notes", ""),
            "evidence": evidence,
            "remediation": finding.get("remediation") or "No remediation required.",
            "target_clause": sections[0] if sections else "",
            "contract_excerpt": evidence[0] if evidence else "",
            "regulatory_basis": finding.get("regulatory_basis") or finding.get("citation_source", ""),
            "deviation_gap": finding.get("deviation_gap", ""),
            "source_page": finding.get("source_page"),
            "source_section": finding.get("source_section", ""),
            "source_clause_id": finding.get("source_clause_id", ""),
            "source_excerpt": evidence[0] if evidence else "",
            "confidence": finding.get("confidence", 0.0),
            
            # vNext fields
            "control": finding.get("test_name", ""),
            "contract_sections": sections,
            "contract_evidence": evidence,
            "law_reference": finding.get("regulatory_basis") or finding.get("citation_source", ""),
        }


    def _build_graph(self):
        workflow = StateGraph(AgentState)
        llm = self.llm

        # Node 1: Jurisdiction Identification
        def jurisdiction_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Jurisdiction Node")
            prompt = (
                "Analyze the following contract text. Identify whether the supported official-regulation review regimes apply: "
                "EU GDPR, Australian Privacy Act, EU Export Control, or Australian Export Control. "
                "Set privacy_triggered true only when the contract itself shows personal-data processing, controller/processor duties, "
                "privacy notices, data subject handling, security for personal information, or cross-border personal-data transfer tied to EU or Australia. "
                "Set export_triggered true only for controlled goods, dual-use items, software/technology transfer, sanctions, export licensing, or controlled technical data tied to EU or Australia. "
                "Do not infer EU/Australia applicability merely because a party is a financial services company or because customers/individuals are mentioned.\n\n"
                f"CONTRACT TEXT:\n{state['contract_text']}"
            )
            structured_llm = llm.with_structured_output(JurisdictionProfileSchema)
            profile = structured_llm.invoke(prompt)
            return {
                "jurisdiction_profile": profile.model_dump(),
                "privacy_triggered": profile.privacy_triggered,
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
            tests = (PRIVACY_TESTS if state.get("privacy_triggered", False) else []) + (EXPORT_TESTS if state.get("export_triggered", False) else [])
            if not tests:
                return {"privacy_mappings": [], "export_mappings": []}
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
        async def privacy_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Privacy Node")
            profile = state["jurisdiction_profile"]
            if not state.get("privacy_triggered", False):
                return {"privacy_findings": []}
                
            all_clauses = self._reconstruct_clauses(state["contract_text"], state["source_context"])
            rag_context_by_test = {m.get("test_name"): m.get("rag_context", []) for m in state.get("privacy_mappings", [])}
            coord_by_test = {m.get("test_name"): m for m in state.get("privacy_mappings", [])}
            
            findings = []
            structured_llm_single = llm.with_structured_output(EvidenceControlAssessment)
            
            for control_name in PRIVACY_TESTS:
                # 1. Check Applicability Gate
                gate_keywords = APPLICABILITY_GATES.get(control_name)
                is_gate_passed = True
                if gate_keywords:
                    contract_lower = state['contract_text'].lower()
                    is_gate_passed = any(kw in contract_lower for kw in gate_keywords)

                if not is_gate_passed:
                    logger.info(f"[LangGraph] Skipping {control_name} - Applicability gate failed.")
                    assessment = {
                        "control": control_name,
                        "applicable": False,
                        "applicability_reason": f"Control is not applicable as no indicators of {control_name} (e.g., {', '.join(gate_keywords[:3])}) were found in the contract.",
                        "contract_evidence": [],
                        "law_evidence": [],
                        "evidence_status": "NOT_APPLICABLE",
                        "adequacy_evaluation": "Not triggered.",
                        "finding": f"Control is not applicable as no indicators of {control_name} (e.g., {', '.join(gate_keywords[:3])}) were found in the contract.",
                        "remediation": "No remediation required.",
                        "target_clause": "Not applicable",
                        "regulatory_basis": "",
                        "confidence": 1.0,
                        "is_relevant_match": False,
                    }
                    coord = coord_by_test.get(control_name, {})
                    findings.append(self._assessment_to_finding(assessment, coord, rag_context_by_test.get(control_name, []), document_type="data_processing_agreement"))
                    continue

                control_queries = EXPANDED_QUERIES_MAP.get(control_name, [control_name])
                ranked = self._hybrid_retrieve_and_rank(control_name, all_clauses, control_queries)
                
                top_5_clauses = ranked[:5]
                top_clause = top_5_clauses[0]["clause"] if top_5_clauses else None
                
                mapping = {
                    "test_name": control_name,
                    "target_clause": top_clause.get("section_number") if top_clause else "",
                    "contract_excerpt": top_clause.get("text") if top_clause else "",
                    "semantic_contract_evidence": [c["clause"]["text"] for c in top_5_clauses],
                    "retrieved_clauses": [
                        {
                            "section": c["clause"]["section_number"] or f"p. {c['clause']['page_number']}",
                            "score": round(c["score"], 2),
                            "excerpt": c["clause"]["text"]
                        }
                        for c in top_5_clauses
                    ],
                    "rag_context": rag_context_by_test.get(control_name, [])
                }
                
                formatted_rag = self._format_mapping_rag_context([mapping])
                
                logger.info(f"[LangGraph] Privacy Node - Evaluating control: {control_name}")
                prompt = (
                    f"You are a forensic legal privacy auditor. The identified privacy jurisdiction profile is: {profile}.\n\n"
                    f"Review the control '{control_name}' following these strict stages:\n"
                    "Stage 1 — Applicability Analysis: Determine whether this regulatory control is applicable. If the contract does not involve the specific subject matter (e.g., no mention of children, marketing, or automated processing), you MUST return evidence_status as NOT_APPLICABLE. Do not use generic 'personal data' clauses to force applicability. Never evaluate adequacy for non-applicable controls.\n"
                    "Stage 5 — Legal Adequacy Evaluation: Evaluate if the contract materially satisfies the legal obligation (e.g., equivalent wording is PRESENT). Do not require identical wording to the regulation.\n"
                    "Stage 6 — Evidence Status: The control must be classified as: PRESENT, PARTIALLY_PRESENT, ABSENT, or NOT_APPLICABLE.\n"
                    "Stage 7 — Mandatory Citation Requirement: You must cite contract evidence. Prohibit the value 'Section: Not provided' if contract evidence was retrieved.\n"
                    "Stage 8 — Confidence Calibration: Keep confidence values calibrated (max 40% for ABSENT, max 70% for PARTIALLY_PRESENT, max 85% for PRESENT, and 90%+ only when applicability is confirmed, evidence retrieved/cited, and adequacy evaluated).\n"
                    "Stage 9 — Relevance Filtering: If the provided CANDIDATE EVIDENCE discusses a different topic (e.g., Data Transfer, Security Measures, or Subprocessors) and does not explicitly mention retention periods or deletion obligations, you MUST set is_relevant_match to False, ignore it, and classify evidence_status as ABSENT. Do not attempt to 'stretch' a storage clause to satisfy a deletion requirement.\n\n"
                    "Strict Node Rules:\n"
                    "1. For every test, you MUST identify the exact clause ID. If multiple clauses mention the topic, you must select the one that most specifically addresses the requirement (e.g., for notification timeframes, prioritize clauses with time units like '72 hours' or 'undue delay' over general security clauses).\n"
                    "2. You MUST explicitly look for 'Parent Article: [Name]' in the official regulatory context to cite the correct regulatory basis.\n\n"
                    f"COORDINATE AND CONTRACT EVIDENCE CANDIDATES:\n{json.dumps(mapping, indent=2)}\n\n"
                    f"OFFICIAL REGULATORY RAG CONTEXT:\n{formatted_rag}\n\n"
                    f"CONTRACT TEXT:\n{state['contract_text']}\n\n"
                    "Return the assessment for this control. law_evidence must cite the official PDF RAG context. contract_evidence must be verbatim contract excerpts where present."
                )
                
                try:
                    assessment = await structured_llm_single.ainvoke(prompt)
                    item = assessment.model_dump()
                except Exception as ex:
                    logger.error(f"Failed to evaluate {control_name} using LLM: {ex}")
                    item = {
                        "control": control_name,
                        "applicable": True,
                        "applicability_reason": "Fallback due to LLM error",
                        "contract_evidence": [mapping["contract_excerpt"]] if mapping["contract_excerpt"] else [],
                        "law_evidence": [],
                        "evidence_status": "ABSENT",
                        "adequacy_evaluation": "LLM error during evaluation",
                        "finding": f"{control_name} is ABSENT (fallback)",
                        "remediation": "Review the control requirements.",
                        "target_clause": mapping["target_clause"],
                        "regulatory_basis": "",
                        "confidence": 0.3,
                        "is_relevant_match": True,
                    }

                # Force status to ABSENT if not relevant match
                if not item.get("is_relevant_match", True):
                    item["evidence_status"] = "ABSENT"
                    item["contract_evidence"] = []
                    item["finding"] = f"{control_name} is ABSENT (no relevant contract evidence found)."
                    item["remediation"] = f"Add a {control_name} clause to the contract."
                
                evidence_status = item.get("evidence_status", "ABSENT")
                
                # Stage 4: Contradiction Detection before emitting ABSENT
                if evidence_status == "ABSENT":
                    control_map_info = RETRIEVAL_MAPS.get(control_name, {})
                    keywords = control_map_info.get("keywords", [])
                    contradiction_clauses = []
                    for c in all_clauses:
                        text_lower = c["text"].lower()
                        for kw in keywords:
                            if " " in kw:
                                if kw.lower() in text_lower:
                                    contradiction_clauses.append(c)
                                    break
                            else:
                                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                                    contradiction_clauses.append(c)
                                    break
                        if len(contradiction_clauses) >= 5:
                            break
                            
                    if contradiction_clauses:
                        logger.info(f"Contradiction found for control {control_name}. Triggering re-review.")
                        item["evidence_status"] = "CONTRADICTED"
                        rereview_prompt = (
                            f"You are a senior legal auditor performing a contradiction audit for control: {control_name}.\n"
                            f"You previously assessed this control as ABSENT, but a forensic search discovered the following relevant clauses in the contract:\n"
                            + "\n\n".join([f"Section {c['section_number']} (p. {c['page_number']}): {c['text']}" for c in contradiction_clauses])
                            + "\n\nUnder our vNext architecture, ABSENT is strictly prohibited when relevant evidence is found. You must reassess the control and classify it as either PRESENT (materially satisfied) or PARTIALLY_PRESENT (partially addressed).\n"
                            "Evaluate the adequacy of this evidence and generate the updated finding details in JSON format."
                        )
                        try:
                            reassessed = await structured_llm_single.ainvoke(rereview_prompt)
                            reassessed_item = reassessed.model_dump()
                            if reassessed_item.get("evidence_status") == "ABSENT":
                                reassessed_item["evidence_status"] = "PARTIALLY_PRESENT"
                            item.update(reassessed_item)
                        except Exception as ex:
                            logger.error(f"Re-review failed for {control_name}: {ex}")
                            item["evidence_status"] = "PARTIALLY_PRESENT"
                            item["contract_evidence"] = [contradiction_clauses[0]["text"]]
                            item["target_clause"] = contradiction_clauses[0]["section_number"] or f"p. {contradiction_clauses[0]['page_number']}"
                            item["adequacy_evaluation"] = "Evidence found in contradiction search: " + contradiction_clauses[0]["text"]
                            
                # Stage 8: Confidence Calibration
                has_ev = bool(item.get("contract_evidence"))
                app_conf = bool(item.get("applicable"))
                ade_eval = bool(item.get("adequacy_evaluation"))
                item["confidence"] = self._calibrate_confidence(
                    item.get("evidence_status", "ABSENT"),
                    has_ev,
                    app_conf,
                    ade_eval,
                    float(item.get("confidence") or 0.0)
                )
                
                # Prohibit "Section: Not provided" if evidence is cited
                if has_ev and (not item.get("target_clause") or item.get("target_clause") == "Section: Not provided"):
                    found_sec = None
                    for c in all_clauses:
                        for ev in item.get("contract_evidence", []):
                            if ev.strip() in c["text"] or c["text"] in ev.strip():
                                found_sec = c["section_number"] or f"p. {c['page_number']}"
                                break
                        if found_sec:
                            break
                    item["target_clause"] = found_sec or "Clause Evidence"
                    
                coord = coord_by_test.get(control_name, {})
                findings.append(self._assessment_to_finding(item, coord, rag_context_by_test.get(control_name, []), document_type="data_processing_agreement"))
                
            return {
                "privacy_findings": findings
            }

        # Node 6: Export Control Compliance Check (Conditional)
        async def export_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Export Node")
            profile = state["jurisdiction_profile"]
            if not state.get("export_triggered", False):
                return {"export_findings": []}
                
            all_clauses = self._reconstruct_clauses(state["contract_text"], state["source_context"])
            rag_context_by_test = {m.get("test_name"): m.get("rag_context", []) for m in state.get("export_mappings", [])}
            coord_by_test = {m.get("test_name"): m for m in state.get("export_mappings", [])}
            
            findings = []
            structured_llm_single = llm.with_structured_output(EvidenceControlAssessment)
            
            for control_name in EXPORT_TESTS:
                control_queries = EXPANDED_QUERIES_MAP.get(control_name, [control_name])
                ranked = self._hybrid_retrieve_and_rank(control_name, all_clauses, control_queries)
                
                top_5_clauses = ranked[:5]
                top_clause = top_5_clauses[0]["clause"] if top_5_clauses else None
                
                mapping = {
                    "test_name": control_name,
                    "target_clause": top_clause.get("section_number") if top_clause else "",
                    "contract_excerpt": top_clause.get("text") if top_clause else "",
                    "semantic_contract_evidence": [c["clause"]["text"] for c in top_5_clauses],
                    "retrieved_clauses": [
                        {
                            "section": c["clause"]["section_number"] or f"p. {c['clause']['page_number']}",
                            "score": round(c["score"], 2),
                            "excerpt": c["clause"]["text"]
                        }
                        for c in top_5_clauses
                    ],
                    "rag_context": rag_context_by_test.get(control_name, [])
                }
                
                formatted_rag = self._format_mapping_rag_context([mapping])
                
                logger.info(f"[LangGraph] Export Node - Evaluating control: {control_name}")
                prompt = (
                    f"You are a forensic legal export-control auditor. The identified export jurisdiction profile is: {profile}.\n\n"
                    f"Review the control '{control_name}' following these strict stages:\n"
                    "Stage 1 — Applicability Analysis: Determine whether this regulatory control is applicable. If not applicable, return evidence_status as NOT_APPLICABLE and stop. Never evaluate adequacy for non-applicable controls.\n"
                    "Stage 5 — Legal Adequacy Evaluation: Evaluate if the contract materially satisfies the legal obligation (e.g., equivalent wording is PRESENT). Do not require identical wording to the regulation.\n"
                    "Stage 6 — Evidence Status: The control must be classified as: PRESENT, PARTIALLY_PRESENT, ABSENT, or NOT_APPLICABLE.\n"
                    "Stage 7 — Mandatory Citation Requirement: You must cite contract evidence. Prohibit the value 'Section: Not provided' if contract evidence was retrieved.\n"
                    "Stage 8 — Confidence Calibration: Keep confidence values calibrated (max 40% for ABSENT, max 70% for PARTIALLY_PRESENT, max 85% for PRESENT, and 90%+ only when applicability is confirmed, evidence retrieved/cited, and adequacy evaluated).\n"
                    "Stage 9 — Relevance Filtering: If the provided CANDIDATE EVIDENCE discusses a different topic (e.g., Data Transfer, Security Measures, or Subprocessors) and does not explicitly mention compliance with export laws, you MUST set is_relevant_match to False, ignore it, and classify evidence_status as ABSENT. Do not attempt to 'stretch' a security clause to satisfy an export check.\n\n"
                    f"COORDINATE AND CONTRACT EVIDENCE CANDIDATES:\n{json.dumps(mapping, indent=2)}\n\n"
                    f"OFFICIAL REGULATORY RAG CONTEXT:\n{formatted_rag}\n\n"
                    f"CONTRACT TEXT:\n{state['contract_text']}\n\n"
                    "Return the assessment for this control. law_evidence must cite the official PDF RAG context. contract_evidence must be verbatim contract excerpts where present."
                )
                
                try:
                    assessment = await structured_llm_single.ainvoke(prompt)
                    item = assessment.model_dump()
                except Exception as ex:
                    logger.error(f"Failed to evaluate export control {control_name} using LLM: {ex}")
                    item = {
                        "control": control_name,
                        "applicable": True,
                        "applicability_reason": "Fallback due to LLM error",
                        "contract_evidence": [mapping["contract_excerpt"]] if mapping["contract_excerpt"] else [],
                        "law_evidence": [],
                        "evidence_status": "ABSENT",
                        "adequacy_evaluation": "LLM error during evaluation",
                        "finding": f"{control_name} is ABSENT (fallback)",
                        "remediation": "Review the control requirements.",
                        "target_clause": mapping["target_clause"],
                        "regulatory_basis": "",
                        "confidence": 0.3,
                        "is_relevant_match": True,
                    }

                # Force status to ABSENT if not relevant match
                if not item.get("is_relevant_match", True):
                    item["evidence_status"] = "ABSENT"
                    item["contract_evidence"] = []
                    item["finding"] = f"{control_name} is ABSENT (no relevant contract evidence found)."
                    item["remediation"] = f"Add a {control_name} clause to the contract."
                
                evidence_status = item.get("evidence_status", "ABSENT")
                
                # Stage 4: Contradiction Detection before emitting ABSENT
                if evidence_status == "ABSENT":
                    control_map_info = RETRIEVAL_MAPS.get(control_name, {})
                    keywords = control_map_info.get("keywords", [])
                    contradiction_clauses = []
                    for c in all_clauses:
                        text_lower = c["text"].lower()
                        for kw in keywords:
                            if " " in kw:
                                if kw.lower() in text_lower:
                                    contradiction_clauses.append(c)
                                    break
                            else:
                                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                                    contradiction_clauses.append(c)
                                    break
                        if len(contradiction_clauses) >= 5:
                            break
                            
                    if contradiction_clauses:
                        logger.info(f"Contradiction found for export control {control_name}. Triggering re-review.")
                        item["evidence_status"] = "CONTRADICTED"
                        rereview_prompt = (
                            f"You are a senior legal auditor performing a contradiction audit for control: {control_name}.\n"
                            f"You previously assessed this control as ABSENT, but a forensic search discovered the following relevant clauses in the contract:\n"
                            + "\n\n".join([f"Section {c['section_number']} (p. {c['page_number']}): {c['text']}" for c in contradiction_clauses])
                            + "\n\nUnder our vNext architecture, ABSENT is strictly prohibited when relevant evidence is found. You must reassess the control and classify it as either PRESENT (materially satisfied) or PARTIALLY_PRESENT (partially addressed).\n"
                            "Evaluate the adequacy of this evidence and generate the updated finding details in JSON format."
                        )
                        try:
                            reassessed = await structured_llm_single.ainvoke(rereview_prompt)
                            reassessed_item = reassessed.model_dump()
                            if reassessed_item.get("evidence_status") == "ABSENT":
                                reassessed_item["evidence_status"] = "PARTIALLY_PRESENT"
                            item.update(reassessed_item)
                        except Exception as ex:
                            logger.error(f"Re-review failed for export {control_name}: {ex}")
                            item["evidence_status"] = "PARTIALLY_PRESENT"
                            item["contract_evidence"] = [contradiction_clauses[0]["text"]]
                            item["target_clause"] = contradiction_clauses[0]["section_number"] or f"p. {contradiction_clauses[0]['page_number']}"
                            item["adequacy_evaluation"] = "Evidence found in contradiction search: " + contradiction_clauses[0]["text"]
                            
                # Stage 8: Confidence Calibration
                has_ev = bool(item.get("contract_evidence"))
                app_conf = bool(item.get("applicable"))
                ade_eval = bool(item.get("adequacy_evaluation"))
                item["confidence"] = self._calibrate_confidence(
                    item.get("evidence_status", "ABSENT"),
                    has_ev,
                    app_conf,
                    ade_eval,
                    float(item.get("confidence") or 0.0)
                )
                
                # Prohibit "Section: Not provided" if evidence is cited
                if has_ev and (not item.get("target_clause") or item.get("target_clause") == "Section: Not provided"):
                    found_sec = None
                    for c in all_clauses:
                        for ev in item.get("contract_evidence", []):
                            if ev.strip() in c["text"] or c["text"] in ev.strip():
                                found_sec = c["section_number"] or f"p. {c['page_number']}"
                                break
                        if found_sec:
                            break
                    item["target_clause"] = found_sec or "Clause Evidence"
                    
                coord = coord_by_test.get(control_name, {})
                findings.append(self._assessment_to_finding(item, coord, rag_context_by_test.get(control_name, []), document_type="export_control_agreement"))
                
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

            def process_mappings(mappings):
                updated = []
                for f in mappings:
                    rag_context = []
                    if vector_store:
                        # Get expanded queries for this test
                        queries = EXPANDED_QUERIES_MAP.get(f["test_name"])
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
                            parent_title = doc.metadata.get("parent_title") or doc.metadata.get("article_number") or ""
                            rag_context.append(
                                f"Parent Article: {parent_title}\n"
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
                v_dict = f.copy()
                v_dict["verification_notes"] = (
                    "Deterministic verification preserved the evidence-derived status. "
                    "Actionable findings require applicability plus ABSENT or PARTIALLY_PRESENT contract evidence."
                )
                v_dict["citation_source"] = f.get("regulatory_basis", "")
                verified.append(v_dict)

            return {
                "verification_results": verified
            }

        # Node 6: Qualitative Decision and Redline proposal
        def decision_node(state: AgentState):
            logger.info("[LangGraph] Transitioning to Decision Node")
            if not state.get("verification_results"):
                profile = state.get("jurisdiction_profile", {})
                rationale = profile.get("rationale") or (
                    "The contract did not contain contract-grounded triggers for the supported EU/Australia privacy or export-control regimes."
                )
                return {
                    "redlines": [],
                    "final_decision": {
                        "summary": (
                            "No GDPR, Australian Privacy Act, EU Export Control, or Australian Export Control findings were issued. "
                            f"{rationale} Disclaimer: This review is for informational purposes only and does not constitute formal legal advice. "
                            "Please consult with qualified legal counsel."
                        ),
                        "clause_analyses": [],
                        "risk_assessments": [],
                        "compliance_findings": [],
                        "negotiation_strategies": [],
                        "missing_protections": [],
                    }
                }
            compliance_findings = [
                self._verified_to_compliance_finding(item)
                for item in state.get("verification_results", [])
            ]
            status_counts: dict[str, int] = {}
            for finding in compliance_findings:
                status = str(finding.get("status", "unknown")).lower()
                status_counts[status] = status_counts.get(status, 0) + 1
            issue_count = status_counts.get("fail", 0) + status_counts.get("partial", 0)
            summary = (
                f"Evidence-grounded privacy/export review completed. Reviewed {len(compliance_findings)} controls: "
                f"{status_counts.get('pass', 0)} pass, {status_counts.get('partial', 0)} partial, "
                f"{status_counts.get('fail', 0)} fail, and {status_counts.get('not-applicable', 0)} not applicable. "
                f"{issue_count} actionable issue(s) require remediation. "
                "Disclaimer: This review is for informational purposes only and does not constitute formal legal advice. "
                "Please consult with qualified legal counsel."
            )
            return {
                "redlines": [],
                "final_decision": {
                    "summary": summary,
                    "clause_analyses": [],
                    "risk_assessments": [],
                    "compliance_findings": compliance_findings,
                    "negotiation_strategies": [],
                    "missing_protections": [],
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

        def choose_first_analysis_node(state: AgentState):
            if state.get("privacy_triggered", False):
                return "privacy_node"
            if state.get("export_triggered", False):
                return "export_node"
            return "verification_node"

        workflow.add_conditional_edges(
            "rag_node",
            choose_first_analysis_node,
            {
                "privacy_node": "privacy_node",
                "export_node": "export_node",
                "verification_node": "verification_node",
            },
        )

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
            "privacy_triggered": False,
            "export_triggered": False
        }
        
        # Run graph sequentially
        final_state = await self.graph.ainvoke(initial_state)
        decision = final_state.get("final_decision", {})
        
        # Map findings to response classes
        clause_analyses = [ClauseAnalysis.model_validate(x) for x in decision.get("clause_analyses", [])]
        compliance_findings = []
        for x in decision.get("compliance_findings", []):
            try:
                compliance_findings.append(ComplianceFinding.model_validate(x))
            except Exception:
                # Fallback if domain is not set
                x["domain"] = "export_control" if "export" in str(x.get("requirement", "")).lower() else "privacy"
                compliance_findings.append(ComplianceFinding.model_validate(x))
                
        missing_protections = [MissingProtection.model_validate(x) for x in decision.get("missing_protections", [])]
        
        # Link findings with sequential issue IDs and build redline suggestions
        from clauseguard.models.openai_legal import RedlineSuggestion, FinalDecision, DecisionOutcome, JurisdictionProfile, JurisdictionFinding, AnalysisSeverity
        
        redline_suggestions = []
        for idx, finding in enumerate(compliance_findings, start=1):
            finding.domain = "export_control" if "export" in str(finding.requirement).lower() or finding.domain == "export_control" else "privacy"
            status_lower = str(finding.status).lower().replace("_", "-")
            if status_lower in ("fail", "partial", "absent", "partially-present", "contradicted"):
                issue_id = f"{'EXP' if finding.domain == 'export_control' else 'PRIV'}-{idx:03d}"
                finding.issue_id = issue_id
                redline_suggestions.append(RedlineSuggestion(
                    issue_id=issue_id,
                    domain="export_control" if finding.domain == "export_control" else "privacy",
                    clause_reference=finding.target_clause or "Not provided",
                    applicable_laws=finding.applicable_laws if finding.applicable_laws else ([finding.regulatory_basis] if finding.regulatory_basis else []),
                    proposed_wording=finding.remediation or "",
                    drafting_instruction=finding.remediation or "Remediate finding."
                ))
            else:
                finding.issue_id = f"{'EXP' if finding.domain == 'export_control' else 'PRIV'}-{idx:03d}"
                
        # Derive final decision
        def is_actionable(f):
            st = str(f.status).upper().replace("_", "-")
            return st not in ("PRESENT", "PASS", "NOT-APPLICABLE", "NOT_APPLICABLE")

        has_critical = any(f.severity == AnalysisSeverity.CRITICAL for f in compliance_findings if is_actionable(f))
        has_high_or_medium = any(f.severity in (AnalysisSeverity.HIGH, AnalysisSeverity.MEDIUM) for f in compliance_findings if is_actionable(f))
        
        if has_critical:
            outcome = DecisionOutcome.FAIL
            rationale = "The contract contains critical compliance findings that fail legal adequacy requirements."
        elif has_high_or_medium:
            outcome = DecisionOutcome.CONDITIONAL_PASS
            rationale = "The contract is approved subject to resolving the highlighted compliance issues."
        else:
            outcome = DecisionOutcome.PASS
            rationale = "The contract is approved with no significant data privacy or export control compliance issues."
            
        # Conditions should only include:
        # - ABSENT controls
        # - PARTIALLY_PRESENT controls above a severity threshold (MEDIUM or higher)
        conditions = []
        for f in compliance_findings:
            st = str(f.status).upper().replace("_", "-")
            if st in ("PRESENT", "PASS", "NOT-APPLICABLE", "NOT_APPLICABLE"):
                continue
            if st in ("ABSENT", "FAIL"):
                conditions.append(f.requirement)
            elif st in ("PARTIALLY-PRESENT", "PARTIALLY_PRESENT", "PARTIAL", "CONTRADICTED"):
                if f.severity in (AnalysisSeverity.CRITICAL, AnalysisSeverity.HIGH, AnalysisSeverity.MEDIUM):
                    conditions.append(f.requirement)

        final_decision = FinalDecision(
            outcome=outcome,
            rationale=rationale,
            conditions=conditions,
            escalation_targets=["HUMAN PRIVACY COUNSEL"] if has_critical else []
        )
        
        # Build JurisdictionProfile
        j_profile_dict = final_state.get("jurisdiction_profile", {})
        privacy_juris_list = []
        if j_profile_dict.get("privacy_jurisdiction") and j_profile_dict.get("privacy_jurisdiction") != "None":
            privacy_juris_list.append(JurisdictionFinding(
                jurisdiction=j_profile_dict.get("privacy_jurisdiction", ""),
                basis=j_profile_dict.get("rationale", ""),
                privacy_laws=["GDPR"] if "EU" in str(j_profile_dict.get("privacy_jurisdiction")) else ["Australian Privacy Act"],
                export_laws=[]
            ))
        export_juris_list = []
        if j_profile_dict.get("export_jurisdiction") and j_profile_dict.get("export_jurisdiction") != "None":
            export_juris_list.append(JurisdictionFinding(
                jurisdiction=j_profile_dict.get("export_jurisdiction", ""),
                basis=j_profile_dict.get("rationale", ""),
                privacy_laws=[],
                export_laws=["EU Export Control"] if "EU" in str(j_profile_dict.get("export_jurisdiction")) else ["Australia Export Control"]
            ))
            
        jurisdiction_profile = JurisdictionProfile(
            privacy_jurisdictions=privacy_juris_list,
            export_control_jurisdictions=export_juris_list,
            export_control_triggered=final_state.get("export_triggered", False),
            trigger_rationale=j_profile_dict.get("rationale", "")
        )
        
        # Build summary
        summary = (
            f"Review of {filename or 'contract'} completed. "
            f"Final decision: {str(outcome.value).upper().replace('_', ' ')}. "
            f"{len(compliance_findings)} compliance findings evaluated."
        )
        
        return ContractReviewOutput(
            summary=summary,
            jurisdiction_profile=jurisdiction_profile,
            compliance_findings=compliance_findings,
            redline_suggestions=redline_suggestions,
            final_decision=final_decision,
            clause_analyses=clause_analyses,
            missing_protections=missing_protections,
            export_control_triggered=final_state.get("export_triggered", False),
            source_filename=filename,
            document_type="contract"
        )

    async def extract_clauses(self, contract_text: str) -> list[dict]:
        """Extract clauses from contract text using LLM."""
        from clauseguard.models.clause import ClauseType
        clause_types = ", ".join(f'"{ct.value}"' for ct in ClauseType)
        prompt = (
            "You are a legal contract analyst. Extract all distinct legal clauses from the following contract text.\n\n"
            "For each clause, return a JSON object with:\n"
            f"- \"clause_type\": one of {clause_types}\n"
            "- \"text\": the full clause text (verbatim from the contract)\n"
            "- \"section_number\": the section number if present (e.g. \"3.1\", \"Section 5\"), or \"\"\n"
            "- \"char_offset_start\": approximate character offset where clause begins\n"
            "- \"char_offset_end\": approximate character offset where clause ends\n"
            "- \"confidence\": your confidence in the classification (0.0 to 1.0)\n\n"
            "Return a JSON array of clause objects. Only return valid JSON, no markdown fences or extra text.\n\n"
            f"CONTRACT TEXT:\n{contract_text[:50000]}"
        )
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content or "[]"
        
        if content.startswith("```"):
            if "\n" in content:
                content = content.split("\n", 1)[1]
            else:
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
        try:
            payload = json.loads(content)
            if isinstance(payload, dict) and "clauses" in payload:
                return payload["clauses"]
            if isinstance(payload, list):
                return payload
            elif isinstance(payload, dict):
                for k, v in payload.items():
                    if isinstance(v, list):
                        return v
            return []
        except Exception as e:
            logger.error("Failed to parse clauses extraction JSON: %s", e)
            return []

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
                temperature=0.0,
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
