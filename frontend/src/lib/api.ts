import type {
  ContractMetadata,
  ContractUploadResponse,
  ContractReviewOutput,
  ExtractedClause,
  ReviewSummary,
  SearchRequest,
  SearchResponse,
} from '@/types/api';

const BASE = '/api/v1';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>('/health'),

  listContracts: () => request<ContractMetadata[]>('/contracts/'),

  getContract: (id: string) => request<ContractMetadata>(`/contracts/${id}`),

  getContractClauses: (id: string) =>
    request<ExtractedClause[]>(`/contracts/${id}/clauses`),

  uploadContract: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<ContractUploadResponse>('/contracts/upload', {
      method: 'POST',
      body: form,
    });
  },

  search: (body: SearchRequest) =>
    request<SearchResponse>('/search/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  reviewContract: (id: string) =>
    request<ContractReviewOutput>(`/review/${id}`, { method: 'POST' }),

  getLatestReview: (id: string) =>
    request<ContractReviewOutput>(`/review/${id}/latest`),

  getReviewHistory: (id: string) =>
    request<ReviewSummary[]>(`/review/${id}/history`),

  getReviewById: (contractId: string, reviewId: string) =>
    request<ContractReviewOutput>(`/review/${contractId}/${reviewId}`),

  exportReviewExcel: async (id: string) => {
    const res = await fetch(`${BASE}/review/${id}/export.xlsx`);
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`${res.status}: ${body}`);
    }
    return res.blob();
  },

  deleteContract: async (id: string) =>
    request<{ status: string; contract_id: string }>(`/contracts/${id}`, {
      method: 'DELETE',
    }),
};
