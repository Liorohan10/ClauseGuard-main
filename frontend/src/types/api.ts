export type ClauseType =
  | 'indemnity'
  | 'liability_cap'
  | 'termination'
  | 'confidentiality'
  | 'ip_assignment'
  | 'governing_law'
  | 'data_protection'
  | 'force_majeure'
  | 'other'
  // Specialized — Data Privacy & Export Control
  | 'export_control'
  | 'sanctions'
  | 'data_transfer'
  | 'subprocessor'
  | 'breach_notification'
  | 'data_subject_rights';

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type Domain = 'privacy' | 'export_control' | 'general';
export type DecisionOutcome = 'pass' | 'conditional_pass' | 'fail' | 'escalate';

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
  export_control_triggered?: boolean;
  final_decision_outcome?: DecisionOutcome;
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

// ---------------------------------------------------------------------------
// Jurisdiction Profile (spec section 2)
// ---------------------------------------------------------------------------

export interface JurisdictionFinding {
  jurisdiction: string;
  basis: string;
  privacy_laws: string[];
  export_laws: string[];
}

export interface JurisdictionProfile {
  privacy_jurisdictions: JurisdictionFinding[];
  export_control_jurisdictions: JurisdictionFinding[];
  export_control_triggered: boolean;
  trigger_rationale: string;
}

// ---------------------------------------------------------------------------
// Compliance Finding (spec sections 3 & 4)
// ---------------------------------------------------------------------------

export interface ComplianceFinding {
  issue_id: string;
  domain: Domain;
  requirement: string;
  status: string;
  severity: Severity;
  explanation: string;
  evidence: string[];
  remediation: string;
  fallback_position: string;
  applicable_laws: string[];
  jurisdictions: string[];
  escalate: boolean;
  escalation_target: string;
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

// ---------------------------------------------------------------------------
// Redline Suggestion (spec section 5)
// ---------------------------------------------------------------------------

export interface RedlineSuggestion {
  issue_id: string;
  domain: 'privacy' | 'export_control';
  clause_reference: string;
  applicable_laws: string[];
  proposed_wording: string;
  drafting_instruction: string;
}

// ---------------------------------------------------------------------------
// Final Decision (spec section 6)
// ---------------------------------------------------------------------------

export interface FinalDecision {
  outcome: DecisionOutcome;
  rationale: string;
  conditions: string[];
  escalation_targets: string[];
}

// ---------------------------------------------------------------------------
// Clause Analysis
// ---------------------------------------------------------------------------

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface ClauseAnalysis {
  clause_text: string;
  clause_name: string;
  clause_type: string;
  domain: Domain;
  summary: string;
  risk_level: RiskLevel;
  impact: string;
  recommendations: string[];
  applicable_laws: string[];
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

// ---------------------------------------------------------------------------
// Missing Protection
// ---------------------------------------------------------------------------

export interface MissingProtection {
  protection: string;
  domain: Domain;
  why_missing: string;
  risk: string;
  mitigation: string;
  suggested_clause: string;
  applicable_laws: string[];
  source_page?: number | null;
  source_section?: string;
  source_clause_id?: string;
  source_excerpt?: string;
  confidence: number;
}

// ---------------------------------------------------------------------------
// Legacy types (kept for backward compatibility with old data)
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Master output type
// ---------------------------------------------------------------------------

export interface ContractReviewOutput {
  contract_safety_score: number;
  summary: string;
  // Spec section 2
  jurisdiction_profile?: JurisdictionProfile | null;
  // Spec sections 3 & 4 (domain field distinguishes them)
  compliance_findings: ComplianceFinding[];
  // Spec section 5
  redline_suggestions: RedlineSuggestion[];
  // Spec section 6
  final_decision?: FinalDecision | null;
  // Supplementary
  clause_analyses: ClauseAnalysis[];
  missing_protections: MissingProtection[];
  // Legacy (empty in new reviews)
  risk_assessments: RiskAssessment[];
  negotiation_strategies: NegotiationStrategy[];
  // Metadata
  export_control_triggered: boolean;
  source_filename: string;
  document_type: string;
}

// ---------------------------------------------------------------------------
// Legacy report types (used by older /report endpoint)
// ---------------------------------------------------------------------------

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
