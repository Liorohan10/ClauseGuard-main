import { useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, AlertCircle, Eye, ClipboardCheck, ArrowRight } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DropZone } from '@/components/DropZone';
import { api } from '@/lib/api';
import { CLAUSE_TYPE_LABELS, CLAUSE_TYPE_COLORS } from '@/lib/constants';
import type { ContractUploadResponse } from '@/types/api';

export function UploadPage() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [result, setResult] = useState<ContractUploadResponse | null>(null);
  const [error, setError] = useState('');

  const handleFile = async (file: File) => {
    setStatus('loading');
    setError('');
    try {
      const res = await api.uploadContract(file);
      setResult(res);
      setStatus('success');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
      setStatus('error');
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Contract</h1>
        <p className="mt-1 text-muted-foreground">
          Upload a PDF or text file for AI-powered clause extraction and analysis.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <DropZone onFile={handleFile} disabled={status === 'loading'} loading={status === 'loading'} />
        </CardContent>
      </Card>

      {status === 'error' && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-start gap-3 p-5">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" />
            <div>
              <p className="font-medium text-destructive">Upload failed</p>
              <p className="mt-1 text-sm text-muted-foreground">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {status === 'success' && result && (
        <Card className="border-emerald-200 bg-emerald-50/50">
          <CardContent className="p-6 space-y-5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="font-semibold text-emerald-900">{result.message}</p>
                <p className="text-sm text-emerald-700">{result.filename}</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-6 rounded-lg bg-white p-4 shadow-sm">
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Clauses Found</p>
                <p className="mt-1 text-2xl font-bold">{result.num_clauses}</p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Clause Types</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {result.clause_types_found.map((t) => (
                    <Badge key={t} variant="secondary" className={`text-[10px] ${CLAUSE_TYPE_COLORS[t]}`}>
                      {CLAUSE_TYPE_LABELS[t]}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <Button asChild>
                <Link to={`/contracts/${result.contract_id}`}>
                  <Eye className="mr-2 h-4 w-4" />
                  View Contract
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link to={`/contracts/${result.contract_id}/review`}>
                  <ClipboardCheck className="mr-2 h-4 w-4" />
                  Run Review
                  <ArrowRight className="ml-1 h-3.5 w-3.5" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
