import { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ClipboardCheck, FileText, ArrowLeft, ArrowRight, ChevronDown, ChevronUp, Download, Trash2, History } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/lib/api';
import { CLAUSE_TYPE_LABELS, CLAUSE_TYPE_COLORS } from '@/lib/constants';
import type { ContractMetadata, ExtractedClause, ClauseType } from '@/types/api';

export function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<ContractMetadata | null>(null);
  const [clauses, setClauses] = useState<ExtractedClause[]>([]);
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([api.getContract(id), api.getContractClauses(id)])
      .then(([c, cls]) => {
        setContract(c);
        setClauses(cls);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading contract...
        </div>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        {error || 'Contract not found'}
      </div>
    );
  }

  const byType = clauses.reduce<Record<ClauseType, ExtractedClause[]>>(
    (acc, c) => {
      (acc[c.clause_type] ??= []).push(c);
      return acc;
    },
    {} as Record<ClauseType, ExtractedClause[]>
  );
  const types = Object.keys(byType) as ClauseType[];

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await api.exportReviewExcel(contract.contract_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${contract.filename}_compliance_review.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    const confirmed = window.confirm('Delete this contract and all related clauses and reviews? This cannot be undone.');
    if (!confirmed) return;
    setDeleting(true);
    try {
      await api.deleteContract(id);
      navigate('/');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Back link + header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" asChild className="mt-1 shrink-0">
            <Link to="/"><ArrowLeft className="h-4 w-4" /></Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <FileText className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold tracking-tight">{contract.filename}</h1>
            </div>
            <p className="mt-1 text-sm text-muted-foreground ml-9">
              Uploaded {new Date(contract.upload_timestamp).toLocaleDateString('en-US', {
                month: 'long', day: 'numeric', year: 'numeric'
              })}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link to={`/contracts/${contract.contract_id}/reviews`}>
              <History className="mr-2 h-4 w-4" />
              History
            </Link>
          </Button>
          <Button variant="outline" onClick={handleExport} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting...' : 'Export Excel'}
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
            <Trash2 className="mr-2 h-4 w-4" />
            {deleting ? 'Deleting...' : 'Delete'}
          </Button>
          <Button asChild>
            <Link to={`/contracts/${contract.contract_id}/review`}>
              <ClipboardCheck className="mr-2 h-4 w-4" />
              Run Review
              <ArrowRight className="ml-1 h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats bar */}
      <Card>
        <CardContent className="p-0">
          <div className="grid grid-cols-2 divide-x sm:grid-cols-4">
            <MetricCell label="Pages" value={String(contract.num_pages)} />
            <MetricCell label="Clauses" value={String(contract.num_clauses)} />
            <MetricCell label="Characters" value={contract.text_length.toLocaleString()} />
            <div className="p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Types</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {contract.clause_types_found.map((t) => (
                  <Badge key={t} variant="secondary" className={`text-[10px] ${CLAUSE_TYPE_COLORS[t]}`}>
                    {CLAUSE_TYPE_LABELS[t]}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Clause tabs */}
      {types.length > 0 ? (
        <div>
          <h2 className="mb-4 text-lg font-semibold">Extracted Clauses</h2>
          <Tabs defaultValue={types[0]}>
            <TabsList className="mb-4 flex-wrap h-auto gap-1 bg-transparent p-0">
              {types.map((t) => (
                <TabsTrigger
                  key={t}
                  value={t}
                  className="rounded-full border border-border bg-card data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:border-primary"
                >
                  {CLAUSE_TYPE_LABELS[t]}
                  <span className="ml-1.5 text-xs opacity-70">({byType[t].length})</span>
                </TabsTrigger>
              ))}
            </TabsList>

            {types.map((t) => (
              <TabsContent key={t} value={t} className="space-y-3">
                {byType[t].map((clause) => (
                  <ClauseCard key={clause.clause_id} clause={clause} />
                ))}
              </TabsContent>
            ))}
          </Tabs>
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center text-muted-foreground">
            No clauses extracted for this contract.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}

function ClauseCard({ clause }: { clause: ExtractedClause }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = clause.text.length > 300;
  const confidence = Math.round(clause.confidence * 100);

  return (
    <Card className="transition-shadow hover:shadow-sm">
      <CardContent className="p-5 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className={CLAUSE_TYPE_COLORS[clause.clause_type]}>
              {CLAUSE_TYPE_LABELS[clause.clause_type]}
            </Badge>
            {clause.section_number && (
              <span className="text-xs text-muted-foreground">
                Sec. {clause.section_number}
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              p.{clause.page_number}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className="tabular-nums font-medium">{confidence}%</span>
          </div>
        </div>

        <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground/90">
          {isLong && !expanded ? clause.text.slice(0, 300) + '...' : clause.text}
        </p>

        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </CardContent>
    </Card>
  );
}
