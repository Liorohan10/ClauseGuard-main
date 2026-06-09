import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Loader2, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/lib/api';
import {
  ALL_CLAUSE_TYPES,
  CLAUSE_TYPE_LABELS,
  CLAUSE_TYPE_COLORS,
} from '@/lib/constants';
import type { ClauseType, SearchHit } from '@/types/api';
import { cn } from '@/lib/utils';

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<ClauseType[]>([]);
  const [topK, setTopK] = useState(10);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [totalHits, setTotalHits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.search({
        query: query.trim(),
        clause_types: selectedTypes.length > 0 ? selectedTypes : null,
        top_k: topK,
      });
      setHits(res.hits);
      setTotalHits(res.total_hits);
      setSearched(true);
    } catch {
      setHits([]);
      setTotalHits(0);
    } finally {
      setLoading(false);
    }
  };

  const toggleType = (t: ClauseType) => {
    setSelectedTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Search Clauses</h1>
        <p className="mt-1 text-muted-foreground">
          Hybrid semantic + keyword search across all extracted clauses.
        </p>
      </div>

      {/* Search bar */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search for clauses (e.g. indemnity, limitation of liability)..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doSearch()}
                className="pl-9"
              />
            </div>
            <Button onClick={doSearch} disabled={loading || !query.trim()}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Search
            </Button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Filter:</span>
            {ALL_CLAUSE_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => toggleType(t)}
                className={cn(
                  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-all',
                  selectedTypes.includes(t)
                    ? `${CLAUSE_TYPE_COLORS[t]} border-transparent`
                    : selectedTypes.length > 0
                      ? 'border-border text-muted-foreground/50 hover:text-muted-foreground'
                      : 'border-border text-muted-foreground hover:border-primary/30 hover:text-foreground'
                )}
              >
                {CLAUSE_TYPE_LABELS[t]}
              </button>
            ))}

            <div className="ml-auto">
              <Select value={String(topK)} onValueChange={(v) => setTopK(Number(v))}>
                <SelectTrigger className="h-8 w-24 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[5, 10, 20, 50].map((n) => (
                    <SelectItem key={n} value={String(n)}>Top {n}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {searched && !loading && (
        <p className="text-sm text-muted-foreground">
          Found <span className="font-semibold text-foreground">{totalHits}</span> result{totalHits !== 1 ? 's' : ''}
        </p>
      )}

      <div className="space-y-3">
        {hits.map((hit, i) => (
          <Card key={hit.clause_id} className="transition-shadow hover:shadow-sm">
            <CardContent className="p-5 space-y-3">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground">
                  {i + 1}
                </span>
                <Badge variant="secondary" className={CLAUSE_TYPE_COLORS[hit.clause_type]}>
                  {CLAUSE_TYPE_LABELS[hit.clause_type]}
                </Badge>
                <span className="text-[11px] tabular-nums text-muted-foreground">
                  Score: {hit.score.toFixed(3)}
                </span>
                <Link
                  to={`/contracts/${hit.contract_id}`}
                  className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                >
                  View Contract
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
              {(hit.section_number || hit.page_number) && (
                <p className="text-xs text-muted-foreground">
                  {hit.section_number && `Section ${hit.section_number}`}
                  {hit.section_number && hit.page_number ? ' · ' : ''}
                  {hit.page_number ? `Page ${hit.page_number}` : ''}
                </p>
              )}
              {hit.highlights.length > 0 ? (
                <div className="space-y-1">
                  {hit.highlights.map((h, j) => (
                    <p
                      key={j}
                      className="text-sm leading-relaxed [&>em]:font-semibold [&>em]:not-italic [&>em]:text-primary"
                      dangerouslySetInnerHTML={{ __html: h }}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
                  {hit.text.length > 400 ? hit.text.slice(0, 400) + '...' : hit.text}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {searched && !loading && hits.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No results found for "{query}".</p>
            <p className="mt-1 text-sm text-muted-foreground">Try different keywords or remove filters.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
