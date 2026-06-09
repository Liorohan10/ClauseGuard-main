export type ClauseType =
  | 'indemnity'
  | 'liability_cap'
  | 'termination'
  | 'confidentiality'
  | 'ip_assignment'
  | 'governing_law'
  | 'data_protection'
  | 'force_majeure'
  | 'other';

export type Severity = 'high' | 'medium' | 'low' | 'info';

export interface ExtractedClause {
  clause_id: string;
  contract_id: string;
  clause_type: ClauseType;
  text: string;
  section_number: string;
  page_number: number;
  char_offset_start: number;
  char_offset_end: number;
  confidence: number;
}

export interface ContractMetadata {
  contract_id: string;
  filename: string;
  upload_timestamp: string;
  num_pages: number;
  num_clauses: number;
  clause_types_found: ClauseType[];
  text_length: number;
  latest_reviewed_at?: string | null;
  latest_review_score?: number | null;
  latest_review_summary?: string;
  latest_review_id?: string | null;
  latest_review_finding_count?: number;
}

export interface ReviewSummary {
  review_id: string;
  reviewed_at: string;
  contract_filename: string;
  contract_safety_score: number;
  summary: string;
  findings_count: number;
}

export interface ContractUploadResponse {
  contract_id: string;
  filename: string;
  num_clauses: number;
  clause_types_found: ClauseType[];
  message: string;
}

export interface SearchRequest {
  query: string;
  clause_types?: ClauseType[] | null;
  contract_ids?: string[] | null;
  top_k?: number;
}

export interface SearchHit {
  clause_id: string;
  contract_id: string;
  clause_type: ClauseType;
  text: string;
  score: number;
  section_number: string;
  page_number: number;
  highlights: string[];
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  hits: SearchHit[];
}

export interface Finding {
  clause_type: ClauseType;
  severity: Severity;
  clause_text: string;
  template_text: string;
  deviation: string;
  risk: string;
  recommendation: string;
  confidence: number;
}

export interface RiskReport {
  contract_id: string;
  contract_filename: string;
  overall_risk_score: number;
  summary: string;
  findings: Finding[];
  coverage: Record<string, boolean>;
  missing_required_clauses: ClauseType[];
  num_high: number;
  num_medium: number;
  num_low: number;
}

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface ClauseAnalysis {
  clause_text: string;
  clause_name: string;
  clause_type: string;
  summary: string;
  risk_level: RiskLevel;
  impact: string;
  recommendations: string[];
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

export interface RiskAssessment {
  risk_area: string;
  severity: Severity;
  issue: string;
  rationale: string;
  mitigation: string;
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

export interface ComplianceFinding {
  requirement: string;
  status: string;
  severity: Severity;
  explanation: string;
  evidence: string[];
  remediation: string;
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

export interface NegotiationStrategy {
  objective: string;
  leverage: string;
  proposed_language: string;
  rationale: string;
  priority: Severity;
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

export interface MissingProtection {
  protection: string;
  why_missing: string;
  risk: string;
  mitigation: string;
  suggested_clause: string;
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

export interface ContractReviewOutput {
  contract_safety_score: number;
  summary: string;
  clause_analyses: ClauseAnalysis[];
  risk_assessments: RiskAssessment[];
  compliance_findings: ComplianceFinding[];
  negotiation_strategies: NegotiationStrategy[];
  missing_protections: MissingProtection[];
  source_filename: string;
  document_type: string;
}
