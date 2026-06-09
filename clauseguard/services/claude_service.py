import json
import logging
import time

import openai

from clauseguard.config import settings
from clauseguard.models.clause import ClauseType

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


def _call_with_retry(client: openai.OpenAI, model: str, max_tokens: int, messages: list) -> str:
    """Call LLM API with exponential backoff retry on overloaded errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
            )
            return response.choices[0].message.content.strip()
        except openai.APIStatusError as e:
            if e.status_code in (429, 529) and attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("API overloaded, retrying in %.1fs (attempt %d/%d)", delay, attempt + 1, MAX_RETRIES)
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Unreachable")


def _strip_markdown_fences(raw: str) -> str:
    """Strip markdown code fences from LLM response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    return raw


EXTRACT_CLAUSES_PROMPT = """\
You are a legal contract analyst. Extract all distinct legal clauses from the following contract text.

For each clause, return a JSON object with:
- "clause_type": one of {clause_types}
- "text": the full clause text (verbatim from the contract)
- "section_number": the section number if present (e.g. "3.1", "Section 5"), or ""
- "char_offset_start": approximate character offset where clause begins
- "char_offset_end": approximate character offset where clause ends
- "confidence": your confidence in the classification (0.0 to 1.0)

Return a JSON array of clause objects. Only return valid JSON, no markdown fences or extra text.

CONTRACT TEXT:
{contract_text}
"""

COMPARE_CLAUSE_PROMPT = """\
You are a legal compliance reviewer. Compare the following contract clause against the company-approved template.

CONTRACT CLAUSE ({clause_type}):
{clause_text}

COMPANY TEMPLATE:
{template_text}

KEY REQUIREMENTS:
{requirements}

Analyze the clause and return a JSON object with:
- "severity": "high", "medium", "low", or "info"
- "deviation": a clear description of how the clause deviates from the template
- "risk": the potential risk or exposure from this deviation
- "recommendation": specific suggested action or language change
- "confidence": your confidence in this assessment (0.0 to 1.0)

If the clause is fully compliant, set severity to "info" and deviation to "Clause is compliant with template."

Return only valid JSON, no markdown fences or extra text.
"""

SUMMARY_PROMPT = """\
You are a legal risk analyst. Based on the following findings from a contract review, write a concise executive summary (2-4 sentences) and assign an overall risk score from 0.0 (no risk) to 10.0 (critical risk).

FINDINGS:
{findings_json}

MISSING REQUIRED CLAUSES: {missing}

Return a JSON object with:
- "summary": the executive summary text
- "overall_risk_score": a float from 0.0 to 10.0

Return only valid JSON.
"""


class ClaudeService:
    """Wrapper around OpenAI-compatible API for clause extraction and review."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.client = openai.OpenAI(
            api_key=api_key or settings.llm_api_key,
            base_url=base_url or settings.llm_base_url,
        )
        self.model = model or settings.llm_model

    def extract_clauses(self, contract_text: str) -> list[dict]:
        """Extract clauses from contract text using LLM."""
        clause_types = ", ".join(f'"{ct.value}"' for ct in ClauseType)
        prompt = EXTRACT_CLAUSES_PROMPT.format(
            clause_types=clause_types, contract_text=contract_text[:50000]
        )

        raw = _call_with_retry(
            self.client, self.model, 4096,
            [{"role": "user", "content": prompt}],
        )
        raw = _strip_markdown_fences(raw)

        try:
            clauses = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM extraction response: %s", raw[:500])
            return []

        if not isinstance(clauses, list):
            logger.error("Expected list from LLM, got %s", type(clauses))
            return []

        return clauses

    def compare_clause_to_template(
        self,
        clause_text: str,
        clause_type: str,
        template_text: str,
        requirements: list[str],
    ) -> dict:
        """Compare a single clause against a template using LLM."""
        prompt = COMPARE_CLAUSE_PROMPT.format(
            clause_type=clause_type,
            clause_text=clause_text,
            template_text=template_text,
            requirements="\n".join(f"- {r}" for r in requirements),
        )

        raw = _call_with_retry(
            self.client, self.model, 2048,
            [{"role": "user", "content": prompt}],
        )
        raw = _strip_markdown_fences(raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM comparison response: %s", raw[:500])
            return {
                "severity": "medium",
                "deviation": "Unable to parse AI response",
                "risk": "Review manually",
                "recommendation": "Manual review required",
                "confidence": 0.0,
            }

    def generate_report_summary(
        self, findings: list[dict], missing_clauses: list[str]
    ) -> dict:
        """Generate executive summary and risk score from findings."""
        prompt = SUMMARY_PROMPT.format(
            findings_json=json.dumps(findings, indent=2)[:10000],
            missing=", ".join(missing_clauses) if missing_clauses else "None",
        )

        raw = _call_with_retry(
            self.client, self.model, 1024,
            [{"role": "user", "content": prompt}],
        )
        raw = _strip_markdown_fences(raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse LLM summary response: %s", raw[:500])
            return {
                "summary": "Unable to generate summary. Please review findings manually.",
                "overall_risk_score": 5.0,
            }
