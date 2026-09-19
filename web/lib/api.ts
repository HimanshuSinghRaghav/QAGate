import type {
  AgentRow,
  AuditEvent,
  CheckDefinition,
  DashboardOverview,
  LeadCase,
  OverrideResponse,
  QueueItem,
  ScoredLead,
  Transcript,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail) detail = JSON.stringify(body.detail);
    } catch {
      detail = (await res.text().catch(() => "")) || detail;
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const fetchDashboard = () => api<DashboardOverview>("/api/v1/dashboard");
export const fetchAgents = () => api<AgentRow[]>("/api/v1/dashboard/agents");
export const fetchLeads = () => api<LeadCase[]>("/api/v1/leads");
export const fetchLead = (leadId: string) => api<LeadCase>(`/api/v1/leads/${leadId}`);
export const fetchQueue = (decision?: string) =>
  api<QueueItem[]>(
    decision
      ? `/api/v1/reviews/queue?decision=${encodeURIComponent(decision)}`
      : "/api/v1/reviews/queue",
  );
export const fetchResults = (leadId: string) =>
  api<ScoredLead>(`/api/v1/leads/${leadId}/results`);
export const scoreLead = (leadId: string) =>
  api<ScoredLead>(`/api/v1/leads/${leadId}/score`, { method: "POST" });
export const fetchTranscript = (leadId: string) =>
  api<Transcript>(`/api/v1/leads/${leadId}/transcript`);
export const fetchAudit = (leadId: string) =>
  api<AuditEvent[]>(`/api/v1/leads/${leadId}/audit`);
export const fetchChecks = () => api<CheckDefinition[]>("/api/v1/checks");

export function overrideResult(resultId: string, payload: {
  new_status: "PASS" | "FAIL" | "REVIEW";
  actor: string;
  reason: string;
  reason_code?: string;
}) {
  return api<OverrideResponse>(
    `/api/v1/reviews/results/${resultId}/override`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
