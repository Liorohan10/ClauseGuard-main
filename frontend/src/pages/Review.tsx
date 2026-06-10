import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowLeft,
  AlertCircle,
  Sparkles,
  MessageSquareQuote,
  Download,
  RefreshCw,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { RiskGauge } from '@/components/RiskGauge';
import type { ContractReviewOutput, Severity } from '@/types/api';

type RecommendationCard = {
  title: string;
  subtitle?: string;
  body: string;
  recommendation: string;
  citation?: string;
};

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
            Analyzing clauses against templates... This may take a moment.
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

  const severityCounts = report.risk_assessments.reduce<Record<Severity, number>>(
    (acc, item) => {
      acc[item.severity] += 1;
      return acc;
    },
    { high: 0, medium: 0, low: 0, info: 0 }
  );

  const recommendationItems: RecommendationCard[] = [
    ...report.compliance_findings.map((item) => ({
      title: item.requirement,
      subtitle: `Compliance · ${item.severity}`,
      body: item.explanation,
      recommendation: item.remediation,
      citation: citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt),
    })),
    ...report.risk_assessments.map((item) => ({
      title: item.risk_area,
      subtitle: `Risk · ${item.severity}`,
      body: item.issue,
      recommendation: item.mitigation,
      citation: citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt),
    })),
    ...report.missing_protections.map((item) => ({
      title: item.protection,
      subtitle: 'Missing protection',
      body: item.why_missing,
      recommendation: item.suggested_clause || item.mitigation,
      citation: citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt),
    })),
    ...report.negotiation_strategies.map((item) => ({
      title: item.objective,
      subtitle: `Negotiation · ${item.priority}`,
      body: item.rationale,
      recommendation: item.proposed_language,
      citation: citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt),
    })),
  ];

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

      <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
        <Card className="flex items-center justify-center">
          <CardContent className="p-8">
            <RiskGauge score={report.contract_safety_score} />
          </CardContent>
        </Card>
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
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SeverityCard
          label="High Risks"
          count={severityCounts.high}
          icon={AlertCircle}
          colorClass="border-l-red-500 bg-red-50/50"
          iconColor="text-red-500"
          countColor="text-red-600"
        />
        <SeverityCard
          label="Medium Risks"
          count={severityCounts.medium}
          icon={AlertTriangle}
          colorClass="border-l-red-500 bg-red-50/50"
          iconColor="text-amber-500"
          countColor="text-amber-600"
        />
        <SeverityCard
          label="Clause Analyses"
          count={report.clause_analyses.length}
          icon={MessageSquareQuote}
          colorClass="border-l-blue-500 bg-blue-50/50"
          iconColor="text-blue-500"
          countColor="text-blue-600"
        />
        <SeverityCard
          label="Missing Protections"
          count={report.missing_protections.length}
          icon={Sparkles}
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
            <ProfileItem label="Risk Items" value={String(report.risk_assessments.length)} />
            <ProfileItem label="Compliance Items" value={String(report.compliance_findings.length)} />
          </div>
        </CardContent>
      </Card>

      <SectionList
        title="Recommended Changes"
        items={recommendationItems}
        emptyMessage="No recommendations returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.title}
            subtitle={item.subtitle}
            body={item.body}
            note={item.recommendation}
            citation={item.citation}
          />
        )}
      />

      <SectionList
        title="Clause Analyses"
        items={report.clause_analyses}
        emptyMessage="No clause analyses returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.clause_name}
            subtitle={`${item.clause_type} · ${item.risk_level}`}
            body={item.summary}
            note={item.impact}
            citation={citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
            actions={item.recommendations}
          />
        )}
      />

      <SectionList
        title="Risk Assessments"
        items={report.risk_assessments}
        emptyMessage="No risk assessments returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.risk_area}
            subtitle={item.severity}
            body={item.issue}
            note={item.mitigation}
            citation={citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
          />
        )}
      />

      <SectionList
        title="Compliance Findings"
        items={report.compliance_findings}
        emptyMessage="No compliance findings returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.requirement}
            subtitle={`${item.status} · ${item.severity}`}
            body={item.explanation}
            note={item.remediation}
            citation={citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
            actions={item.evidence}
          />
        )}
      />

      <SectionList
        title="Negotiation Strategies"
        items={report.negotiation_strategies}
        emptyMessage="No negotiation strategies returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.objective}
            subtitle={item.priority}
            body={item.rationale}
            note={item.proposed_language}
            citation={citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
          />
        )}
      />

      <SectionList
        title="Missing Protections"
        items={report.missing_protections}
        emptyMessage="No missing protections returned."
        renderItem={(item) => (
          <SimpleItem
            title={item.protection}
            subtitle={item.confidence > 0 ? `${Math.round(item.confidence * 100)}% confidence` : ''}
            body={item.why_missing}
            note={item.mitigation}
            citation={citationLabel(item.source_page, item.source_section, item.source_clause_id, item.source_excerpt)}
            actions={[item.suggested_clause].filter(Boolean)}
          />
        )}
      />
    </div>
  );
}

function citationLabel(page?: number | null, section?: string, clauseId?: string, excerpt?: string) {
  const parts = [page ? `p. ${page}` : '', section ? `sec. ${section}` : '', clauseId ? `clause ${clauseId}` : ''].filter(Boolean);
  const base = parts.join(' · ');
  if (!excerpt) return base;
  return base ? `${base} · ${excerpt}` : excerpt;
}

function SeverityCard({
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

function SectionList<T>({
  title,
  items,
  emptyMessage,
  renderItem,
}: {
  title: string;
  items: T[];
  emptyMessage: string;
  renderItem: (item: T) => React.ReactNode;
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
            <div key={index}>{renderItem(item)}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function SimpleItem({
  title,
  subtitle,
  body,
  note,
  actions,
  citation,
}: {
  title: string;
  subtitle?: string;
  body: string;
  note?: string;
  actions?: string[];
  citation?: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold">{title}</h3>
            {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        <p className="text-sm leading-relaxed text-foreground">{body}</p>
        {citation && <p className="text-xs text-muted-foreground">Source: {citation}</p>}
        {note && <p className="rounded-lg bg-muted/40 p-3 text-sm text-muted-foreground">{note}</p>}
        {actions && actions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {actions.map((action, index) => (
              <Badge key={index} variant="secondary" className="max-w-full whitespace-normal text-left">
                {action}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
