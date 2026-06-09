import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from clauseguard.models.clause import ClauseType
from clauseguard.models.report import Finding, RiskReport, Severity
from clauseguard.services.claude_service import ClaudeService
from clauseguard.services.elasticsearch_service import ElasticsearchService
from clauseguard.templates.defaults import DEFAULT_TEMPLATES

logger = logging.getLogger(__name__)


class ReviewAgent:
    """Compare contract clauses against templates and produce a risk report."""

    def __init__(
        self,
        claude_service: ClaudeService,
        es_service: ElasticsearchService,
    ):
        self.claude = claude_service
        self.es = es_service
        self._executor = ThreadPoolExecutor(max_workers=2)

    async def review(self, contract_id: str) -> RiskReport:
        """Run full compliance review for a contract."""
        # 1. Fetch contract metadata
        contract = await self.es.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # 2. Fetch all clauses
        clauses = await self.es.get_clauses_by_contract(contract_id)
        if not clauses:
            raise ValueError(f"No clauses found for contract {contract_id}")

        # 3. Group clauses by type
        clauses_by_type: dict[str, list[dict]] = {}
        for clause in clauses:
            ct = clause.get("clause_type", "other")
            clauses_by_type.setdefault(ct, []).append(clause)

        # 4. Compare each clause against its template (parallelized)
        findings: list[Finding] = []
        compare_tasks = []
        for clause_type_str, clause_list in clauses_by_type.items():
            try:
                clause_type = ClauseType(clause_type_str)
            except ValueError:
                continue

            template = DEFAULT_TEMPLATES.get(clause_type)
            if not template:
                continue

            for clause in clause_list:
                compare_tasks.append(
                    self._compare_clause(clause, clause_type, template)
                )

        if compare_tasks:
            results = await asyncio.gather(*compare_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Finding):
                    findings.append(result)
                elif isinstance(result, Exception):
                    logger.error("Comparison failed: %s", result)

        # 5. Detect missing required clauses
        coverage: dict[str, bool] = {}
        missing_required: list[ClauseType] = []
        for ct, template in DEFAULT_TEMPLATES.items():
            found = ct.value in clauses_by_type
            coverage[ct.value] = found
            if template.required and not found:
                missing_required.append(ct)
                findings.append(
                    Finding(
                        clause_type=ct,
                        severity=Severity.HIGH,
                        clause_text="",
                        template_text=template.template_text,
                        deviation=f"Required clause '{template.name}' is missing from contract",
                        risk=f"Contract lacks required {template.name} protections",
                        recommendation=f"Add a {template.name} clause based on company template",
                        confidence=1.0,
                    )
                )

        # 6. Generate summary via Claude
        findings_dicts = [f.model_dump() for f in findings]
        missing_names = [ct.value for ct in missing_required]

        loop = asyncio.get_event_loop()
        summary_result = await loop.run_in_executor(
            self._executor,
            self.claude.generate_report_summary,
            findings_dicts,
            missing_names,
        )

        # 7. Assemble report
        num_high = sum(1 for f in findings if f.severity == Severity.HIGH)
        num_medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        num_low = sum(1 for f in findings if f.severity == Severity.LOW)

        return RiskReport(
            contract_id=contract_id,
            contract_filename=contract.get("filename", ""),
            overall_risk_score=summary_result.get("overall_risk_score", 5.0),
            summary=summary_result.get("summary", ""),
            findings=findings,
            coverage=coverage,
            missing_required_clauses=missing_required,
            num_high=num_high,
            num_medium=num_medium,
            num_low=num_low,
        )

    async def _compare_clause(
        self, clause: dict, clause_type: ClauseType, template
    ) -> Finding:
        """Compare a single clause to its template using Claude (run in thread)."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self.claude.compare_clause_to_template,
            clause["text"],
            clause_type.value,
            template.template_text,
            template.key_requirements,
        )

        try:
            severity = Severity(result.get("severity", "medium"))
        except ValueError:
            severity = Severity.MEDIUM

        return Finding(
            clause_type=clause_type,
            severity=severity,
            clause_text=clause["text"],
            template_text=template.template_text,
            deviation=result.get("deviation", ""),
            risk=result.get("risk", ""),
            recommendation=result.get("recommendation", ""),
            confidence=min(max(result.get("confidence", 0.5), 0.0), 1.0),
        )
