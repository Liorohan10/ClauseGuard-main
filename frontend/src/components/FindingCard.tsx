import { useState } from 'react';
import { ChevronDown, ChevronUp, AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CLAUSE_TYPE_LABELS, CLAUSE_TYPE_COLORS, SEVERITY_COLORS } from '@/lib/constants';
import type { Finding, Severity } from '@/types/api';

const SEVERITY_ICONS: Record<Severity, React.ComponentType<{ className?: string }>> = {
  high: AlertCircle,
  medium: AlertTriangle,
  low: Info,
  info: Info,
};

export function FindingCard({ finding }: { finding: Finding }) {
  const [showTemplate, setShowTemplate] = useState(false);
  const SeverityIcon = SEVERITY_ICONS[finding.severity];

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0">
        {/* Header stripe */}
        <div className="flex items-center gap-2.5 border-b bg-muted/30 px-5 py-3">
          <SeverityIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
          <Badge variant="secondary" className={SEVERITY_COLORS[finding.severity]}>
            {finding.severity.toUpperCase()}
          </Badge>
          <Badge variant="secondary" className={CLAUSE_TYPE_COLORS[finding.clause_type]}>
            {CLAUSE_TYPE_LABELS[finding.clause_type]}
          </Badge>
          {finding.confidence > 0 && (
            <span className="ml-auto text-[11px] tabular-nums text-muted-foreground">
              {Math.round(finding.confidence * 100)}% confidence
            </span>
          )}
        </div>

        <div className="space-y-4 p-5">
          {/* Deviation & Risk side by side on larger screens */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Deviation
              </p>
              <p className="mt-1.5 text-sm leading-relaxed">{finding.deviation}</p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
                Risk Exposure
              </p>
              <p className="mt-1.5 text-sm leading-relaxed">{finding.risk}</p>
            </div>
          </div>

          {/* Clause text */}
          <blockquote className="rounded-lg border-l-4 border-muted-foreground/20 bg-muted/30 py-3 pl-4 pr-3 text-sm italic text-muted-foreground leading-relaxed">
            {finding.clause_text}
          </blockquote>

          {/* Template reference */}
          {finding.template_text && (
            <div>
              <button
                onClick={() => setShowTemplate(!showTemplate)}
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                {showTemplate ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                Template Reference
              </button>
              {showTemplate && (
                <div className="mt-2 rounded-lg bg-muted/50 p-4 text-sm leading-relaxed">
                  {finding.template_text}
                </div>
              )}
            </div>
          )}

          {/* Recommendation */}
          <div className="rounded-lg border border-emerald-200 bg-gradient-to-r from-emerald-50 to-emerald-50/50 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-emerald-700">
              Recommendation
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-emerald-900">
              {finding.recommendation}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
