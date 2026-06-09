import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  List,
  Tags,
  BookOpen,
  Eye,
  ClipboardCheck,
  Upload,
  ArrowRight,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '@/lib/api';
import { CLAUSE_TYPE_LABELS, CLAUSE_TYPE_COLORS } from '@/lib/constants';
import type { ContractMetadata } from '@/types/api';

export function Dashboard() {
  const [contracts, setContracts] = useState<ContractMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .listContracts()
      .then(setContracts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalClauses = contracts.reduce((s, c) => s + c.num_clauses, 0);
  const totalPages = contracts.reduce((s, c) => s + c.num_pages, 0);
  const uniqueTypes = new Set(contracts.flatMap((c) => c.clause_types_found));
  const reviewedContracts = contracts.filter((c) => c.latest_review_id).length;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading contracts...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center text-destructive">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-muted-foreground">
          Overview of your contract portfolio and clause analysis.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard icon={FileText} label="Contracts" value={contracts.length} color="bg-blue-500/10 text-blue-600" />
        <StatCard icon={List} label="Clauses Extracted" value={totalClauses} color="bg-emerald-500/10 text-emerald-600" />
        <StatCard icon={Tags} label="Clause Types" value={uniqueTypes.size} color="bg-violet-500/10 text-violet-600" />
        <StatCard icon={BookOpen} label="Pages Analyzed" value={totalPages} color="bg-amber-500/10 text-amber-600" />
        <StatCard icon={ClipboardCheck} label="Reviewed" value={reviewedContracts} color="bg-cyan-500/10 text-cyan-600" />
      </div>

      {/* Contracts table or empty state */}
      {contracts.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <div className="rounded-full bg-muted p-4">
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold">No contracts yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload your first contract to get started with clause extraction and compliance review.
              </p>
            </div>
            <Button asChild size="lg">
              <Link to="/upload">
                <Upload className="mr-2 h-4 w-4" />
                Upload Contract
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="flex items-center justify-between border-b px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold">Contracts</h2>
              <p className="text-sm text-muted-foreground">
                {contracts.length} contract{contracts.length !== 1 ? 's' : ''} uploaded
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link to="/upload">
                <Upload className="mr-2 h-3.5 w-3.5" />
                Upload New
              </Link>
            </Button>
          </div>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="pl-6">Filename</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-center">Pages</TableHead>
                  <TableHead className="text-center">Clauses</TableHead>
                  <TableHead className="text-center">Review</TableHead>
                  <TableHead>Types</TableHead>
                  <TableHead className="pr-6 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contracts.map((c) => (
                  <TableRow key={c.contract_id}>
                    <TableCell className="pl-6">
                      <Link
                        to={`/contracts/${c.contract_id}`}
                        className="inline-flex items-center gap-2 font-medium text-foreground hover:text-primary transition-colors"
                      >
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        {c.filename}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(c.upload_timestamp).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </TableCell>
                    <TableCell className="text-center text-sm">{c.num_pages}</TableCell>
                    <TableCell className="text-center">
                      <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-primary/10 px-2 text-xs font-semibold text-primary">
                        {c.num_clauses}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      {c.latest_review_id ? (
                        <div className="flex flex-col items-center gap-1">
                          <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-700">
                            Reviewed
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {c.latest_review_score ?? 0}% score
                          </span>
                          {c.latest_review_finding_count ? (
                            <span className="text-[11px] text-muted-foreground">
                              {c.latest_review_finding_count} findings
                            </span>
                          ) : null}
                        </div>
                      ) : (
                        <Badge variant="outline">Not reviewed</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {c.clause_types_found.slice(0, 4).map((t) => (
                          <Badge
                            key={t}
                            variant="secondary"
                            className={`text-[10px] px-1.5 py-0 ${CLAUSE_TYPE_COLORS[t]}`}
                          >
                            {CLAUSE_TYPE_LABELS[t]}
                          </Badge>
                        ))}
                        {c.clause_types_found.length > 4 && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                            +{c.clause_types_found.length - 4}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="pr-6 text-right">
                      <div className="flex justify-end gap-1.5">
                        <Button variant="ghost" size="sm" asChild className="h-8 px-2.5">
                          <Link to={`/contracts/${c.contract_id}`}>
                            <Eye className="mr-1.5 h-3.5 w-3.5" />
                            View
                          </Link>
                        </Button>
                        <Button variant="default" size="sm" asChild className="h-8 px-2.5">
                          <Link to={`/contracts/${c.contract_id}/review`}>
                            <ClipboardCheck className="mr-1.5 h-3.5 w-3.5" />
                            Review
                            <ArrowRight className="ml-1 h-3 w-3" />
                          </Link>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="flex items-center gap-4 p-6">
        <div className={`rounded-xl p-3 ${color}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="text-3xl font-bold tracking-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
