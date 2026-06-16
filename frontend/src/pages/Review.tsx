import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Download,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import type { ComplianceFinding, ContractReviewOutput } from '@/types/api';

type ReviewIssue = ComplianceFinding & { area: 'privacy' | 'export' };

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
            Checking data privacy and export control obligations.
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

  const complianceIssues: ReviewIssue[] = report.compliance_findings
    .filter(isActionableIssue)
    .map((item) => ({ ...item, area: isExportControlFinding(item) ? 'export' : 'privacy' }));
  const privacyIssues = complianceIssues.filter((item) => item.area === 'privacy');
  const exportIssues = complianceIssues.filter((item) => item.area === 'export');
  const nonIssueControls = report.compliance_findings.length - complianceIssues.length;

  const handleExport = async () => {
    if (!id) return;
    setExporting(true);
    try {
      const blob = await api.exportReviewExcel(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.source_filename || id}_compliance_review.xlsx`;
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
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to={id ? `/contracts/${id}` : '/'}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Compliance Review</h1>
          {report.source_filename && <p className="text-sm text-muted-foreground">{report.source_filename}</p>}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link to={id ? `/contracts/${id}/reviews` : '/'}>History</Link>
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting...' : 'Export Excel'}
          </Button>
          <Button variant="ghost" size="icon" asChild>
            <Link to={id ? `/contracts/${id}/review` : '/'}>
              <RefreshCw className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Executive Summary
          </h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">
            {report.summary || 'No summary available.'}
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Data Privacy Issues"
          count={privacyIssues.length}
          icon={AlertCircle}
          colorClass="border-l-red-500 bg-red-50/50"
          iconColor="text-red-500"
          countColor="text-red-600"
        />
        <MetricCard
          label="Export Control Issues"
          count={exportIssues.length}
          icon={AlertTriangle}
          colorClass="border-l-amber-500 bg-amber-50/50"
          iconColor="text-amber-500"
          countColor="text-amber-600"
        />
        <MetricCard
          label="Passed / N/A"
          count={Math.max(nonIssueControls, 0)}
          icon={ShieldCheck}
          colorClass="border-l-blue-500 bg-blue-50/50"
          iconColor="text-blue-500"
          countColor="text-blue-600"
        />
        <MetricCard
          label="Reviewed Controls"
          count={report.compliance_findings.length}
          icon={ShieldCheck}
          colorClass="border-l-emerald-500 bg-emerald-50/50"
          iconColor="text-emerald-500"
          countColor="text-emerald-600"
        />
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Document Profile
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <ProfileItem label="Document Type" value={report.document_type} />
            <ProfileItem label="Source File" value={report.source_filename || 'Unknown'} />
            <ProfileItem label="Data Privacy Issues" value={String(privacyIssues.length)} />
            <ProfileItem label="Export Control Issues" value={String(exportIssues.length)} />
          </div>
        </CardContent>
      </Card>

      <IssueSection
        title="Data Privacy Issues"
        items={privacyIssues}
        emptyMessage="No data privacy issues returned."
      />

      <IssueSection
        title="Export Control Issues"
        items={exportIssues}
        emptyMessage="No export control issues returned."
      />
    </div>
  );
}

function isActionableIssue(item: ComplianceFinding) {
  const status = item.status.toLowerCase().replace('_', '-');
  return status === 'fail' || status === 'partial' || status === 'absent' || status === 'partially-present' || status === 'contradicted';
}

function isExportControlFinding(item: ComplianceFinding) {
  const haystack = `${item.requirement} ${item.explanation} ${item.regulatory_basis ?? ''}`.toLowerCase();
  return [
    'export',
    'dual-use',
    'dual use',
    'sanction',
    'restricted part',
    'denied part',
    'end-use',
    'end user',
    'license',
    'technology control',
    'technical data',
    'wmd',
  ].some((term) => haystack.includes(term));
}

function citationLabel(page?: number | null, section?: string, clauseId?: string, excerpt?: string) {
  const parts = [page ? `p. ${page}` : '', section ? `sec. ${section}` : '', clauseId ? `clause ${clauseId}` : ''].filter(Boolean);
  const base = parts.join(' / ');
  if (!excerpt) return base;
  return base ? `${base} / ${excerpt}` : excerpt;
}

function MetricCard({
  label,
  count,
  icon: Icon,
  colorClass,
  iconColor,
  countColor,
}: {
  label: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  colorClass: string;
  iconColor: string;
  countColor: string;
}) {
  return (
    <Card className={`border-l-4 ${colorClass}`}>
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

function ProfileItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
    </div>
  );
}

function IssueSection({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: ReviewIssue[];
  emptyMessage: string;
}) {
  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">{title}</h2>
      {items.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-muted-foreground">{emptyMessage}</CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((item, index) => (
            <IssueItem key={`${item.requirement}-${index}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function IssueItem({ item }: { item: ReviewIssue }) {
  const citation = citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt);
  const clauseLabel = item.target_clause || item.source_section || 'Clause not identified';

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold">{item.requirement}</h3>
            <p className="text-sm text-muted-foreground">
              {item.status} / {item.severity}
            </p>
          </div>
          {item.regulatory_basis && (
            <Badge variant="secondary" className="max-w-full whitespace-normal text-left">
              {item.regulatory_basis}
            </Badge>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border bg-muted/20 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Identified Clause</p>
            <p className="mt-1 text-sm font-medium">{clauseLabel}</p>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Section</p>
            <p className="mt-1 text-sm font-medium">{item.source_section || 'Not provided'}</p>
          </div>
        </div>

        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Issue Reasoning</p>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground">{item.explanation}</p>
        </div>

        {item.contract_excerpt && (
          <blockquote className="rounded-lg border-l-4 border-muted-foreground/20 bg-muted/30 py-3 pl-4 pr-3 text-sm leading-relaxed text-muted-foreground">
            {item.contract_excerpt}
          </blockquote>
        )}

        {item.deviation_gap && (
          <p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">{item.deviation_gap}</p>
        )}

        {citation && <p className="text-xs text-muted-foreground">Source: {citation}</p>}

        {item.remediation && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-700">Remediation</p>
            <p className="mt-1.5 text-sm leading-relaxed text-emerald-900">{item.remediation}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
