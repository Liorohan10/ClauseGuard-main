import type { ClauseType, Severity } from '@/types/api';

export const CLAUSE_TYPE_LABELS: Record<ClauseType, string> = {
  indemnity: 'Indemnity',
  liability_cap: 'Liability Cap',
  termination: 'Termination',
  confidentiality: 'Confidentiality',
  ip_assignment: 'IP Assignment',
  governing_law: 'Governing Law',
  data_protection: 'Data Protection',
  force_majeure: 'Force Majeure',
  other: 'Other',
};

export const CLAUSE_TYPE_COLORS: Record<ClauseType, string> = {
  indemnity: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  liability_cap: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  termination: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  confidentiality: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  ip_assignment: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  governing_law: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  data_protection: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  force_majeure: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400',
  other: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  info: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
};

export const SEVERITY_CARD_COLORS: Record<string, string> = {
  high: 'border-red-500 bg-red-50 dark:bg-red-950/20',
  medium: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20',
  low: 'border-blue-500 bg-blue-50 dark:bg-blue-950/20',
};

export const ALL_CLAUSE_TYPES: ClauseType[] = [
  'indemnity',
  'liability_cap',
  'termination',
  'confidentiality',
  'ip_assignment',
  'governing_law',
  'data_protection',
  'force_majeure',
  'other',
];

export function riskScoreColor(score: number): string {
  const normalized = score > 10 ? score / 10 : score;
  if (normalized <= 3) return '#22c55e';
  if (normalized <= 5) return '#eab308';
  if (normalized <= 7) return '#f97316';
  return '#ef4444';
}

export function riskScoreLabel(score: number): string {
  const normalized = score > 10 ? score / 10 : score;
  if (normalized <= 3) return 'Low Risk';
  if (normalized <= 5) return 'Medium Risk';
  if (normalized <= 7) return 'High Risk';
  return 'Critical Risk';
}
