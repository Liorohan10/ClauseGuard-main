import type { ClauseType, Severity, DecisionOutcome, Domain } from '@/types/api';

export const CLAUSE_TYPE_LABELS: Record<ClauseType, string> = {
  // General
  indemnity: 'Indemnity',
  liability_cap: 'Liability Cap',
  termination: 'Termination',
  confidentiality: 'Confidentiality',
  ip_assignment: 'IP Assignment',
  governing_law: 'Governing Law',
  data_protection: 'Data Protection',
  force_majeure: 'Force Majeure',
  other: 'Other',
  // Specialized
  export_control: 'Export Control',
  sanctions: 'Sanctions',
  data_transfer: 'Cross-Border Transfer',
  subprocessor: 'Subprocessor',
  breach_notification: 'Breach Notification',
  data_subject_rights: 'Data Subject Rights',
};

export const CLAUSE_TYPE_COLORS: Record<ClauseType, string> = {
  // General
  indemnity: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  liability_cap: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  termination: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  confidentiality: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  ip_assignment: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  governing_law: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  data_protection: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  force_majeure: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-400',
  other: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  // Specialized
  export_control: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  sanctions: 'bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400',
  data_transfer: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400',
  subprocessor: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-400',
  breach_notification: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  data_subject_rights: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
};

export const SEVERITY_COLORS: Record<Severity, string> = {
  critical: 'bg-red-900 text-white dark:bg-red-800',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  info: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
};

export const SEVERITY_CARD_COLORS: Record<string, string> = {
  critical: 'border-red-900 bg-red-50 dark:bg-red-950/20',
  high: 'border-red-500 bg-red-50 dark:bg-red-950/20',
  medium: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20',
  low: 'border-blue-500 bg-blue-50 dark:bg-blue-950/20',
};

// Decision outcome styles (spec section 6)
export const DECISION_OUTCOME_STYLES: Record<DecisionOutcome, { label: string; bg: string; text: string; border: string }> = {
  pass: {
    label: 'PASS',
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-800 dark:text-green-400',
    border: 'border-green-500',
  },
  conditional_pass: {
    label: 'CONDITIONAL PASS',
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-800 dark:text-yellow-400',
    border: 'border-yellow-500',
  },
  fail: {
    label: 'FAIL',
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-800 dark:text-red-400',
    border: 'border-red-600',
  },
  escalate: {
    label: 'ESCALATE',
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-800 dark:text-orange-400',
    border: 'border-orange-500',
  },
};

// Law badge colours — colour-coded per law family
export const LAW_BADGE_COLORS: Record<string, string> = {
  // EU / UK
  GDPR: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  'UK GDPR': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  'DPA 2018': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
  IDTA: 'bg-indigo-100 text-indigo-800',
  // India
  DPDPA: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  DPDP: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  // US Privacy
  CCPA: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  CPRA: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  HIPAA: 'bg-rose-100 text-rose-800',
  GLBA: 'bg-rose-100 text-rose-800',
  COPPA: 'bg-rose-100 text-rose-800',
  FERPA: 'bg-rose-100 text-rose-800',
  // US Export
  EAR: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  OFAC: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  ITAR: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  // APAC
  PDPA: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
  PIPA: 'bg-teal-100 text-teal-800',
  APPI: 'bg-cyan-100 text-cyan-800',
  PIPL: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-400',
  POPIA: 'bg-green-100 text-green-800',
  LGPD: 'bg-emerald-100 text-emerald-800',
  PDPL: 'bg-sky-100 text-sky-800',
  // Default
  default: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

export const DOMAIN_STYLES: Record<Domain | 'general', { label: string; color: string; border: string }> = {
  privacy: {
    label: 'Data Privacy',
    color: 'text-blue-700 dark:text-blue-400',
    border: 'border-blue-400',
  },
  export_control: {
    label: 'Export Control',
    color: 'text-amber-700 dark:text-amber-400',
    border: 'border-amber-400',
  },
  general: {
    label: 'General',
    color: 'text-gray-700 dark:text-gray-400',
    border: 'border-gray-400',
  },
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
  'export_control',
  'sanctions',
  'data_transfer',
  'subprocessor',
  'breach_notification',
  'data_subject_rights',
];

export function riskScoreColor(score: number): string {
  const safety = score > 10 ? score : score * 10;
  if (safety >= 80) return '#22c55e';
  if (safety >= 60) return '#eab308';
  if (safety >= 40) return '#f97316';
  return '#ef4444';
}

export function riskScoreLabel(score: number): string {
  const safety = score > 10 ? score : score * 10;
  if (safety >= 80) return 'Low Risk';
  if (safety >= 60) return 'Medium Risk';
  if (safety >= 40) return 'High Risk';
  return 'Critical Risk';
}

/** Return law badge color class for a given law string */
export function getLawBadgeColor(law: string): string {
  // Check for known prefixes/exact matches
  for (const [key, cls] of Object.entries(LAW_BADGE_COLORS)) {
    if (key === 'default') continue;
    if (law.toUpperCase().startsWith(key.toUpperCase())) return cls;
  }
  return LAW_BADGE_COLORS.default;
}
