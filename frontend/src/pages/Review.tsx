import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  AlertCircle,
  ShieldCheck,
  ShieldX,
  ShieldAlert,
  Globe,
  Scale,
  FileEdit,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  TriangleAlert,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';
import { RiskGauge } from '@/components/RiskGauge';
import {
  DECISION_OUTCOME_STYLES,
  SEVERITY_COLORS,
  DOMAIN_STYLES,
  getLawBadgeColor,
} from '@/lib/constants';
import type {
  ContractReviewOutput,
  ComplianceFinding,
  RedlineSuggestion,
  ClauseAnalysis,
  JurisdictionFinding,
  DecisionOutcome,
  Severity,
  Domain,
} from '@/types/api';

// ─────────────────────────────────────────────────────────────────────────────
// Page component
// ─────────────────────────────────────────────────────────────────────────────

export function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const reviewId = searchParams.get('reviewId');
  const [report, setReport] = useState<ContractReviewOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!id) return;
    const loader = reviewId ? api.getReviewById(id, reviewId) : api.getLatestReview(id);
    loader
      .catch(() => (reviewId ? api.getLatestReview(id) : api.reviewContract(id)))
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, reviewId]);

  if (loading) {
    return (
      <div className="flex h-80 flex-col items-center justify-center gap-4">
        <div className="relative">
          <div className="h-16 w-16 rounded-full border-4 border-muted" />
          <div className="absolute inset-0 h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
        <div className="text-center">
          <p className="font-semibold">Running Compliance Review</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Analyzing clauses against Data Privacy & Export Control requirements…
          </p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>
        <p className="text-sm text-muted-foreground">{error || 'Failed to load report'}</p>
        <Button variant="outline" asChild>
          <Link to={id ? `/contracts/${id}` : '/'}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Link>
        </Button>
      </div>
    );
  }

  // Split findings by domain
  const privacyFindings = report.compliance_findings.filter(
    (f) => f.domain === 'privacy' || f.domain === 'general'
  );
  const exportFindings = report.compliance_findings.filter(
    (f) => f.domain === 'export_control'
  );
  const escalations = report.compliance_findings.filter((f) => f.escalate);

  const criticalCount = report.compliance_findings.filter(
    (f) => f.severity === 'critical'
  ).length;
  const highPrivacyCount = privacyFindings.filter((f) => f.severity === 'high').length;

  const decision = report.final_decision;
  const decisionStyle = decision
    ? DECISION_OUTCOME_STYLES[decision.outcome as DecisionOutcome] ??
      DECISION_OUTCOME_STYLES.escalate
    : DECISION_OUTCOME_STYLES.escalate;

  const handleExport = async () => {
    if (!id) return;
    setExporting(true);
    try {
      const blob = await api.exportReviewExcel(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.source_filename || id}_privacy_export_review.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to={id ? `/contracts/${id}` : '/'}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Data Privacy &amp; Export Control Review
          </h1>
          {report.source_filename && (
            <p className="text-sm text-muted-foreground">{report.source_filename}</p>
          )}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link to={id ? `/contracts/${id}/reviews` : '/'}>History</Link>
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting…' : 'Export Excel'}
          </Button>
          <Button variant="ghost" size="icon" asChild>
            <Link to={id ? `/contracts/${id}/review` : '/'}>
              <RefreshCw className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      {/* ── Spec §1: Executive Result + Score ────────────────────────── */}
      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <Card className="flex items-center justify-center">
          <CardContent className="p-8">
            <RiskGauge score={report.contract_safety_score} />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 space-y-4">
            {/* Final decision badge */}
            {decision && (
              <div
                className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-bold text-sm
                  ${decisionStyle.bg} ${decisionStyle.text} ${decisionStyle.border}`}
              >
                <DecisionIcon outcome={decision.outcome as DecisionOutcome} />
                {decisionStyle.label}
              </div>
            )}
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Executive Summary
              </h2>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">
                {report.summary || 'No summary available.'}
              </p>
            </div>
            {/* Decision rationale */}
            {decision?.rationale && (
              <p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">
                {decision.rationale}
              </p>
            )}
            <p className="text-xs text-muted-foreground italic">
              This review is not legal advice and does not constitute regulatory certification.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* ── Severity counter cards ────────────────────────────────────── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          id="stat-critical"
          label="Critical Findings"
          count={criticalCount}
          icon={ShieldX}
          colorClass="border-l-4 border-l-red-800 bg-red-50/60 dark:bg-red-950/20"
          iconColor="text-red-800"
          countColor="text-red-800"
        />
        <StatCard
          id="stat-high-privacy"
          label="High Privacy Issues"
          count={highPrivacyCount}
          icon={ShieldAlert}
          colorClass="border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-950/10"
          iconColor="text-red-500"
          countColor="text-red-600"
        />
        <StatCard
          id="stat-export"
          label="Export Control Issues"
          count={exportFindings.filter((f) => f.status !== 'pass').length}
          icon={AlertCircle}
          colorClass="border-l-4 border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/10"
          iconColor="text-amber-500"
          countColor="text-amber-600"
        />
        <StatCard
          id="stat-escalations"
          label="Escalations Required"
          count={escalations.length}
          icon={TriangleAlert}
          colorClass="border-l-4 border-l-orange-500 bg-orange-50/50 dark:bg-orange-950/10"
          iconColor="text-orange-500"
          countColor="text-orange-600"
        />
      </div>

      {/* ── Spec §2: Applicable Jurisdictions ────────────────────────── */}
      {report.jurisdiction_profile && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="h-5 w-5 text-primary" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Applicable Jurisdictions Identified
              </h2>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {/* Privacy jurisdictions */}
              <div>
                <h3 className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide mb-2">
                  Data Privacy
                </h3>
                {report.jurisdiction_profile.privacy_jurisdictions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">None identified on current facts.</p>
                ) : (
                  <div className="space-y-2">
                    {report.jurisdiction_profile.privacy_jurisdictions.map((j, i) => (
                      <JurisdictionCard key={i} item={j} domain="privacy" />
                    ))}
                  </div>
                )}
              </div>
              {/* Export control jurisdictions */}
              <div>
                <h3 className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wide mb-2">
                  Export Control
                </h3>
                {!report.export_control_triggered ? (
                  <div className="rounded-lg border border-green-200 bg-green-50/60 dark:bg-green-950/10 p-3">
                    <p className="text-sm text-green-800 dark:text-green-400">
                      <ShieldCheck className="inline h-4 w-4 mr-1" />
                      No export-control trigger identified on current facts. Export control review was not performed.
                    </p>
                  </div>
                ) : report.jurisdiction_profile.export_control_jurisdictions.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Export control triggered — see findings.</p>
                ) : (
                  <div className="space-y-2">
                    {report.jurisdiction_profile.export_control_jurisdictions.map((j, i) => (
                      <JurisdictionCard key={i} item={j} domain="export_control" />
                    ))}
                  </div>
                )}
                {report.jurisdiction_profile.trigger_rationale && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {report.jurisdiction_profile.trigger_rationale}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Spec §§3-5: Main tabbed content ──────────────────────────── */}
      <Tabs defaultValue="privacy" id="review-tabs">
        <TabsList className="mb-4 flex-wrap h-auto gap-1 bg-transparent p-0">
          <TabsTrigger
            value="privacy"
            className="rounded-full border border-border bg-card data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=active]:border-blue-600"
          >
            Data Privacy
            <span className="ml-1.5 text-xs opacity-75">({privacyFindings.filter(f => f.status !== 'pass').length})</span>
          </TabsTrigger>
          <TabsTrigger
            value="export"
            className="rounded-full border border-border bg-card data-[state=active]:bg-amber-600 data-[state=active]:text-white data-[state=active]:border-amber-600"
          >
            Export Control
            <span className="ml-1.5 text-xs opacity-75">({exportFindings.filter(f => f.status !== 'pass').length})</span>
          </TabsTrigger>
          <TabsTrigger
            value="redlines"
            className="rounded-full border border-border bg-card data-[state=active]:bg-emerald-600 data-[state=active]:text-white data-[state=active]:border-emerald-600"
          >
            Proposed Redlines
            <span className="ml-1.5 text-xs opacity-75">({report.redline_suggestions.length})</span>
          </TabsTrigger>
          <TabsTrigger
            value="clauses"
            className="rounded-full border border-border bg-card data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:border-primary"
          >
            Clause Analysis
            <span className="ml-1.5 text-xs opacity-75">({report.clause_analyses.length})</span>
          </TabsTrigger>
        </TabsList>

        {/* ── Tab: Data Privacy (spec §3) ────────────────────────────── */}
        <TabsContent value="privacy" className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Privacy compliance findings across all identified jurisdictions.
          </p>
          {privacyFindings.filter(f => f.status !== 'pass' && f.status !== 'not-applicable').length === 0 ? (
            <EmptyState message="No data privacy issues identified on current facts." />
          ) : (
            privacyFindings
              .filter(f => f.status !== 'pass' && f.status !== 'not-applicable')
              .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
              .map((item, i) => (
                <FindingCard key={i} finding={item} />
              ))
          )}
        </TabsContent>

        {/* ── Tab: Export Control (spec §4) ──────────────────────────── */}
        <TabsContent value="export" className="space-y-4">
          {!report.export_control_triggered ? (
            <Card className="border-green-200">
              <CardContent className="p-6 flex items-start gap-3">
                <ShieldCheck className="h-5 w-5 text-green-600 mt-0.5 shrink-0" />
                <div>
                  <h3 className="font-semibold text-green-800 dark:text-green-400">
                    No Export-Control Trigger Identified
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    The contract does not contain references to controlled items, technology,
                    encryption, EAR/OFAC/sanctions, or other export-control triggers.
                    Export control review was not performed on current facts.
                  </p>
                  <p className="text-xs text-muted-foreground mt-2 italic">
                    Note: Sanctions screening should still be considered for any international counterparty.
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : exportFindings.filter(f => f.status !== 'pass' && f.status !== 'not-applicable').length === 0 ? (
            <EmptyState message="No export control issues identified on current facts." />
          ) : (
            exportFindings
              .filter(f => f.status !== 'pass' && f.status !== 'not-applicable')
              .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
              .map((item, i) => (
                <FindingCard key={i} finding={item} />
              ))
          )}
        </TabsContent>

        {/* ── Tab: Proposed Redlines (spec §5) ───────────────────────── */}
        <TabsContent value="redlines" className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Exact redline wording or structured drafting instructions for unresolved findings.
          </p>
          {report.redline_suggestions.length === 0 ? (
            <EmptyState message="No redlines proposed." />
          ) : (
            report.redline_suggestions.map((item, i) => (
              <RedlineCard key={i} item={item} />
            ))
          )}
        </TabsContent>

        {/* ── Tab: Clause Analysis ───────────────────────────────────── */}
        <TabsContent value="clauses" className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Clause-level analysis for privacy and export-control clauses identified in the contract.
          </p>
          {report.clause_analyses.length === 0 ? (
            <EmptyState message="No clause analyses returned." />
          ) : (
            report.clause_analyses.map((item, i) => (
              <ClauseCard key={i} item={item} />
            ))
          )}
        </TabsContent>
      </Tabs>

      {/* ── Spec §6: Final Decision ───────────────────────────────────── */}
      {decision && (
        <Card className={`border-l-4 ${decisionStyle.border}`}>
          <CardContent className="p-6 space-y-3">
            <div className="flex items-center gap-2">
              <Scale className="h-5 w-5" />
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Final Decision
              </h2>
            </div>
            <div
              className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2 font-bold text-sm
                ${decisionStyle.bg} ${decisionStyle.text} ${decisionStyle.border}`}
            >
              <DecisionIcon outcome={decision.outcome as DecisionOutcome} />
              {decisionStyle.label}
            </div>
            <p className="text-sm leading-relaxed">{decision.rationale}</p>
            {decision.conditions.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Conditions to Resolve
                </p>
                <ul className="space-y-1">
                  {decision.conditions.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="text-yellow-500 mt-0.5">•</span>
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {decision.escalation_targets.length > 0 && (
              <div className="rounded-lg border border-orange-200 bg-orange-50/60 dark:bg-orange-950/10 p-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-400 mb-1">
                  Escalate To
                </p>
                <div className="flex flex-wrap gap-2">
                  {decision.escalation_targets.map((t, i) => (
                    <Badge key={i} className="bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function DecisionIcon({ outcome }: { outcome: DecisionOutcome }) {
  if (outcome === 'pass') return <ShieldCheck className="h-4 w-4" />;
  if (outcome === 'conditional_pass') return <ShieldAlert className="h-4 w-4" />;
  if (outcome === 'fail') return <ShieldX className="h-4 w-4" />;
  return <TriangleAlert className="h-4 w-4" />;
}

function JurisdictionCard({ item, domain }: { item: JurisdictionFinding; domain: Domain }) {
  const [open, setOpen] = useState(false);
  const laws = domain === 'privacy' ? item.privacy_laws : item.export_laws;

  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium">{item.jurisdiction}</p>
        {laws.length > 0 && (
          <button
            onClick={() => setOpen(!open)}
            className="text-xs text-muted-foreground hover:text-foreground"
            aria-label="Toggle laws"
          >
            {open ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{item.basis}</p>
      {open && laws.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {laws.map((law, i) => (
            <span
              key={i}
              className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${getLawBadgeColor(law)}`}
            >
              {law}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: ComplianceFinding }) {
  const [expanded, setExpanded] = useState(false);
  const sevColor = SEVERITY_COLORS[finding.severity as Severity] ?? SEVERITY_COLORS.info;
  const domainStyle = DOMAIN_STYLES[finding.domain as Domain] ?? DOMAIN_STYLES.general;

  return (
    <Card className={finding.escalate ? 'border-orange-400 dark:border-orange-500' : ''}>
      <CardContent className="p-5 space-y-3">
        {/* Header row */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              {finding.issue_id && (
                <span className="text-xs font-mono font-semibold text-muted-foreground">
                  {finding.issue_id}
                </span>
              )}
              <Badge className={sevColor}>{finding.severity.toUpperCase()}</Badge>
              <span className={`text-xs font-semibold ${domainStyle.color}`}>
                {domainStyle.label}
              </span>
              {finding.escalate && (
                <Badge className="bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400">
                  ⚠ ESCALATE: {finding.escalation_target}
                </Badge>
              )}
            </div>
            <h3 className="font-semibold">{finding.requirement}</h3>
          </div>
          <Badge variant="outline">{finding.status.toUpperCase()}</Badge>
        </div>

        {/* Explanation */}
        <p className="text-sm leading-relaxed text-foreground">{finding.explanation}</p>

        {/* Citation */}
        {citationLabel(finding.source_page, finding.source_section, finding.source_clause_id, finding.source_excerpt) && (
          <p className="text-xs text-muted-foreground">
            Source:{' '}
            {citationLabel(finding.source_page, finding.source_section, finding.source_clause_id, finding.source_excerpt)}
          </p>
        )}

        {/* Applicable laws */}
        {finding.applicable_laws.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {finding.applicable_laws.map((law, i) => (
              <span
                key={i}
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${getLawBadgeColor(law)}`}
              >
                {law}
              </span>
            ))}
          </div>
        )}

        {/* Jurisdictions */}
        {finding.jurisdictions.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Jurisdictions: {finding.jurisdictions.join(', ')}
          </p>
        )}

        {/* Expandable: remediation + fallback + evidence */}
        {(finding.remediation || finding.fallback_position || finding.evidence.length > 0) && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? 'Hide' : 'Show'} Remediation &amp; Evidence
            </button>
            {expanded && (
              <div className="mt-2 space-y-2">
                {finding.remediation && (
                  <div className="rounded-lg bg-blue-50/60 dark:bg-blue-950/20 p-3">
                    <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wide mb-1">
                      Recommended Redline / Remediation
                    </p>
                    <p className="text-sm text-foreground">{finding.remediation}</p>
                  </div>
                )}
                {finding.fallback_position && (
                  <div className="rounded-lg bg-yellow-50/60 dark:bg-yellow-950/20 p-3">
                    <p className="text-xs font-semibold text-yellow-700 dark:text-yellow-400 uppercase tracking-wide mb-1">
                      Fallback Position
                    </p>
                    <p className="text-sm text-foreground">{finding.fallback_position}</p>
                  </div>
                )}
                {finding.evidence.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                      Evidence
                    </p>
                    <div className="space-y-1">
                      {finding.evidence.map((ev, i) => (
                        <p key={i} className="rounded bg-muted/40 px-2 py-1 text-xs font-mono text-foreground">
                          {ev}
                        </p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RedlineCard({ item }: { item: RedlineSuggestion }) {
  const domainStyle = DOMAIN_STYLES[item.domain] ?? DOMAIN_STYLES.general;

  return (
    <Card>
      <CardContent className="p-5 space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <FileEdit className="h-4 w-4 text-emerald-600" />
          {item.issue_id && (
            <span className="text-xs font-mono font-semibold text-muted-foreground">
              → {item.issue_id}
            </span>
          )}
          <span className={`text-xs font-semibold ${domainStyle.color}`}>
            {domainStyle.label}
          </span>
        </div>
        <h3 className="font-semibold">{item.clause_reference}</h3>

        {item.applicable_laws.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.applicable_laws.map((law, i) => (
              <span
                key={i}
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${getLawBadgeColor(law)}`}
              >
                {law}
              </span>
            ))}
          </div>
        )}

        {item.proposed_wording && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 dark:bg-emerald-950/20 p-3">
            <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-1">
              Proposed Wording
            </p>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{item.proposed_wording}</p>
          </div>
        )}

        {item.drafting_instruction && (
          <div className="rounded-lg bg-muted/40 p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
              Drafting Instruction
            </p>
            <p className="text-sm text-foreground">{item.drafting_instruction}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ClauseCard({ item }: { item: ClauseAnalysis }) {
  const [expanded, setExpanded] = useState(false);
  const domainStyle = DOMAIN_STYLES[item.domain as Domain] ?? DOMAIN_STYLES.general;
  const riskColors: Record<string, string> = {
    critical: 'bg-red-900 text-white',
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-700',
  };
  const riskColor = riskColors[item.risk_level] ?? riskColors.info;

  return (
    <Card>
      <CardContent className="p-5 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={riskColor}>{item.risk_level.toUpperCase()}</Badge>
          <span className={`text-xs font-semibold ${domainStyle.color}`}>{domainStyle.label}</span>
          <span className="text-xs text-muted-foreground">{item.clause_type}</span>
        </div>
        <h3 className="font-semibold">{item.clause_name}</h3>
        <p className="text-sm text-foreground leading-relaxed">{item.summary}</p>

        {item.applicable_laws.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.applicable_laws.map((law, i) => (
              <span
                key={i}
                className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${getLawBadgeColor(law)}`}
              >
                {law}
              </span>
            ))}
          </div>
        )}

        {citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt) && (
          <p className="text-xs text-muted-foreground">
            Source: {citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
          </p>
        )}

        {(item.impact || item.recommendations.length > 0) && (
          <div>
            <button
              onClick={() => setExpanded(!expanded)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? 'Hide' : 'Show'} Impact &amp; Recommendations
            </button>
            {expanded && (
              <div className="mt-2 space-y-2">
                {item.impact && (
                  <p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">
                    {item.impact}
                  </p>
                )}
                {item.recommendations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {item.recommendations.map((rec, i) => (
                      <Badge key={i} variant="secondary" className="max-w-full whitespace-normal text-left">
                        {rec}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatCard({
  id,
  label,
  count,
  icon: Icon,
  colorClass,
  iconColor,
  countColor,
}: {
  id: string;
  label: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
  iconColor: string;
  countColor: string;
}) {
  return (
    <Card id={id} className={colorClass}>
      <CardContent className="flex items-center justify-between p-5">
        <div className="flex items-center gap-3">
          <Icon className={`h-5 w-5 ${iconColor}`} />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <span className={`text-3xl font-bold ${countColor}`}>{count}</span>
      </CardContent>
    </Card>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <Card className="border-dashed">
      <CardContent className="py-12 text-center text-muted-foreground">{message}</CardContent>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Utility helpers
// ─────────────────────────────────────────────────────────────────────────────

function citationLabel(page?: number | null, section?: string, clauseId?: string, excerpt?: string) {
  const parts = [
    page ? `p. ${page}` : '',
    section ? `sec. ${section}` : '',
    clauseId ? `clause ${clauseId}` : '',
  ].filter(Boolean);
  const base = parts.join(' · ');
  if (!excerpt) return base;
  const short = excerpt.length > 80 ? excerpt.slice(0, 80) + '…' : excerpt;
  return base ? `${base} · "${short}"` : `"${short}"`;
}

function severityRank(s: string): number {
  return { critical: 5, high: 4, medium: 3, low: 2, info: 1 }[s.toLowerCase()] ?? 0;
}
