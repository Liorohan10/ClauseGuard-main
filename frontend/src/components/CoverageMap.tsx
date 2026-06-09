import { Check, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ALL_CLAUSE_TYPES, CLAUSE_TYPE_LABELS } from '@/lib/constants';
import type { ClauseType } from '@/types/api';
import { cn } from '@/lib/utils';

interface CoverageMapProps {
  coverage: Record<string, boolean>;
  missingRequired: ClauseType[];
}

export function CoverageMap({ coverage, missingRequired }: CoverageMapProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {ALL_CLAUSE_TYPES.filter((t) => t !== 'other').map((t) => {
        const found = coverage[t] ?? false;
        const isMissing = missingRequired.includes(t);

        return (
          <div
            key={t}
            className={cn(
              'flex items-center gap-3 rounded-xl border p-4 transition-colors',
              found
                ? 'border-emerald-200 bg-emerald-50/50'
                : isMissing
                  ? 'border-red-200 bg-red-50/50'
                  : 'border-border bg-card'
            )}
          >
            <div className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
              found
                ? 'bg-emerald-100'
                : isMissing
                  ? 'bg-red-100'
                  : 'bg-muted'
            )}>
              {found ? (
                <Check className="h-4 w-4 text-emerald-600" />
              ) : (
                <X className="h-4 w-4 text-red-500" />
              )}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium leading-tight">{CLAUSE_TYPE_LABELS[t]}</p>
              {isMissing && (
                <Badge variant="destructive" className="mt-1 h-4 px-1.5 text-[9px]">
                  Required
                </Badge>
              )}
              {found && (
                <p className="mt-0.5 text-[11px] text-emerald-600 font-medium">Present</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
