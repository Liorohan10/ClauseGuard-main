import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Clock3, Eye } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import type { ContractMetadata, ReviewSummary } from '@/types/api';

export function ReviewHistoryPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<ContractMetadata | null>(null);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([api.getContract(id), api.getReviewHistory(id)])
      .then(([contractData, reviewList]) => {
        setContract(contractData);
        setReviews(reviewList);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="flex items-center gap-3 text-muted-foreground">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading review history...
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

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to={id ? `/contracts/${id}` : '/'}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Review History</h1>
          <p className="text-sm text-muted-foreground">{contract.filename}</p>
        </div>
      </div>

      <Card>
        <CardContent className="flex items-center justify-between gap-4 p-5">
          <div>
            <h2 className="text-lg font-semibold">Saved Reviews</h2>
            <p className="text-sm text-muted-foreground">
              Open any saved review to see the full report and citations.
            </p>
          </div>
          <Badge variant="secondary" className="text-sm">
            {reviews.length} saved
          </Badge>
        </CardContent>
      </Card>

      {reviews.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-16 text-center text-muted-foreground">
            No saved reviews yet. Run a review first to create history.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {reviews.map((review) => (
            <Card key={review.review_id}>
              <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-700">
                      {review.contract_safety_score}% safety
                    </Badge>
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock3 className="h-3.5 w-3.5" />
                      {new Date(review.reviewed_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm leading-relaxed text-foreground">{review.summary}</p>
                  <p className="text-xs text-muted-foreground">{review.findings_count} findings</p>
                </div>
                <Button asChild>
                  <Link to={`/contracts/${contract.contract_id}/review?reviewId=${review.review_id}`}>
                    <Eye className="mr-2 h-4 w-4" />
                    View details
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}