export type GateDecision =
  | "AUTO_APPROVED"
  | "HELD"
  | "QA_REVIEW"
  | "HUMAN_SAMPLE";

export type CheckStatus =
  | "PASS"
  | "FAIL"
  | "REVIEW"
  | "NOT_APPLICABLE"
  | "ERROR";

export type CheckType = "VERBATIM" | "FACTUAL" | "BEHAVIOUR";

export type Evidence = {
  segment_id?: string | null;
  text?: string | null;
  timestamp?: string | null;
  start_ms?: number | null;
  end_ms?: number | null;
  timing_source?: string | null;
  speaker?: string | null;
  speaker_confidence?: number | null;
  note?: string | null;
  value?: unknown;
  confidence?: number | null;
  context?: string | null;
};

export type LabelValue = { label: string; value: string };

export type OpenIssue = {
  result_id: string;
  check_id: string;
  check_name: string;
  status: CheckStatus | string;
  status_label?: string;
  type_label?: string;
  critical: boolean;
  reason: string;
  issue: string;
  expected_label?: string;
  observed_label?: string;
  expected_caption?: string;
  observed_caption?: string;
  timestamp?: string | null;
  start_ms?: number | null;
  speaker?: string | null;
  text?: string | null;
};

export type LeadCase = {
  lead_id: string;
  customer_name: string;
  customer_first_name: string;
  agent_id: string;
  agent_name: string;
  tl_id: string | null;
  tl_name: string;
  retailer_id: string;
  retailer_name: string;
  plan_id: string | null;
  plan_name: string;
  campaign: string | null;
  campaign_label: string;
  site: string | null;
  site_label: string;
  email?: string | null;
  phone?: string | null;
  service_address?: string | null;
  current_provider?: string | null;
  gate_decision: GateDecision | null;
  gate_headline: string;
  gate_next_step: string;
  gate_reason: string | null;
  criticals_failed: number | null;
  scored_at: string | null;
  issue: string | null;
  open_count: number;
  open_issues: OpenIssue[];
  crm: LabelValue[];
  plan: Record<string, string | number | null> | null;
  plan_rows: LabelValue[];
  purpose: string;
};

export type CheckResult = {
  id: string;
  check_id: string;
  check_version: number;
  check_name: string;
  type: CheckType | string;
  critical: boolean;
  weight: number;
  status: CheckStatus;
  confidence: number;
  method: string;
  reason: string;
  expected: Record<string, unknown> | null;
  observed: Record<string, unknown> | null;
  evidence: Evidence[];
  observation_trail: Evidence[];
  expected_label?: string | null;
  observed_label?: string | null;
  expected_caption?: string | null;
  observed_caption?: string | null;
  status_label?: string | null;
  type_label?: string | null;
  issue?: string | null;
};

export type ScoringRun = {
  id: string;
  lead_id: string;
  call_id: string;
  transcript_id: string;
  call_date: string;
  engine_version: string;
  gate_decision: GateDecision;
  gate_reason: string;
  score_with_fatals: number;
  score_without_fatals: number;
  lowest_confidence: number;
  checks_total: number;
  criticals_failed: number;
  sampled_for_human: boolean;
};

export type ScoredLead = {
  run: ScoringRun;
  critical: CheckResult[];
  non_critical: CheckResult[];
  unscorable: CheckResult[];
  case?: LeadCase | null;
};

export type LeadRow = LeadCase;

export type Segment = {
  id: string;
  index: number;
  speaker: string;
  speaker_confidence: number;
  text: string;
  start_ms: number;
  end_ms: number;
  timing_source: string;
  timestamp: string;
};

export type Transcript = {
  transcript_id: string;
  lead_id: string;
  timing_source: string;
  diarization_reliable: boolean;
  segments: Segment[];
};

export type QueueItem = {
  run_id: string;
  lead_id: string;
  gate_decision: GateDecision;
  gate_reason: string;
  gate_headline?: string;
  criticals_failed: number;
  lowest_confidence: number;
  scored_at: string;
  customer_name?: string;
  agent_name?: string;
  plan_name?: string;
  retailer_name?: string;
  issue?: string | null;
  campaign_label?: string;
  site_label?: string;
};

export type CheckDefinition = {
  check_id: string;
  version: number;
  name: string;
  type: string;
  critical: boolean;
  weight: number;
  effective_from: string;
  effective_to: string | null;
  handler: string | null;
};

export type AuditEvent = {
  id: string;
  at: string;
  actor: string;
  event: string;
  event_label?: string;
  payload: Record<string, unknown>;
};

export type DashboardOverview = {
  totals: {
    sales_scored: number;
    auto_approved: number;
    held: number;
    qa_review: number;
    human_sample: number;
  };
  first_pass_yield_pct: number;
  critical_fail_rate_pct: number;
  avg_score_with_fatals: number;
  avg_score_without_fatals: number;
  top_failing_checks: { check: string; failures: number; share_pct: number }[];
  auditor_agreement: {
    human_reviewed_results: number;
    overturned: number;
    agreement_rate_pct: number | null;
    note: string;
  };
  repeat_offences: RepeatOffence[];
  unscorable_checks: { check: string; count: number }[];
};

export type RepeatOffence = {
  agent_id: string;
  agent_name?: string;
  check_id: string;
  check_name?: string;
  failures: number;
  lead_ids: string[];
  window_days: number;
  action: string;
};

export type AgentRow = {
  agent_id: string;
  agent_name?: string;
  scored: number;
  auto_approved: number;
  held: number;
  qa_review: number;
  first_pass_yield_pct: number;
};

export type OverrideResponse = {
  result: CheckResult;
  run: ScoringRun;
  previous_gate: GateDecision;
  new_gate: GateDecision;
};
