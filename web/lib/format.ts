import type { CheckStatus, GateDecision } from "./types";

export function formatClock(ms: number | null | undefined) {
  if (ms == null || Number.isNaN(ms)) return "—";
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) {
    return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const day = d.getUTCDate();
  const month = MONTHS[d.getUTCMonth()];
  const year = d.getUTCFullYear();
  const hours = d.getUTCHours();
  const minutes = String(d.getUTCMinutes()).padStart(2, "0");
  const hour12 = hours % 12 || 12;
  const ampm = hours < 12 ? "am" : "pm";
  return `${day} ${month} ${year}, ${hour12}:${minutes} ${ampm} UTC`;
}

export function formatPct(value: number | null | undefined) {
  if (value == null) return "—";
  return `${Number(value).toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

export function formatScore(value: number | null | undefined) {
  if (value == null) return "—";
  return Number(value).toFixed(1);
}

export function formatConfidence(value: number | null | undefined) {
  if (value == null) return "—";
  return `${Math.round(Number(value) * 100)}%`;
}

export function formatMoney(value: unknown) {
  const n = Number(value);
  if (Number.isNaN(n)) return String(value ?? "—");
  const sign = n < 0 ? "-" : "";
  const [whole, fraction] = Math.abs(n).toFixed(2).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `${sign}$${grouped}.${fraction}`;
}

const ENUM_LABELS: Record<string, string> = {
  month_to_month: "Month to month",
  one_to_one: "One-to-one (likely ASR for month-to-month)",
  no_lock_in: "No lock-in",
};

export function humanize(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return String(value);
  const text = String(value);
  return ENUM_LABELS[text] ?? text.replaceAll("_", " ");
}

export function prettyFact(data: Record<string, unknown> | null | undefined) {
  if (!data || Object.keys(data).length === 0) return "—";
  if (data.final_value != null && data.final_value !== "") {
    const label = humanize(data.final_value);
    return data.conflicted ? `${label} (changed on the call)` : label;
  }
  if ("value" in data && data.value != null && data.value !== "") {
    const unit = String(data.unit ?? "");
    if (unit.toUpperCase().includes("AUD") || unit === "$") {
      return formatMoney(data.value);
    }
    if (unit) return `${humanize(data.value)} ${unit}`;
    return humanize(data.value);
  }
  if (typeof data.script === "string" && data.script) return data.script;
  if (typeof data.best_match === "string" && data.best_match) return data.best_match;
  return Object.entries(data)
    .filter(([k, v]) => v != null && v !== "" && !["unit", "extraction_confidence", "pass_ratio", "match_ratio"].includes(k))
    .map(([k, v]) => `${k.replaceAll("_", " ")}: ${humanize(v)}`)
    .join(" · ") || "—";
}

export const GATE_LABEL: Record<GateDecision, string> = {
  AUTO_APPROVED: "Can ship",
  HELD: "Stopped",
  QA_REVIEW: "Needs QA",
  HUMAN_SAMPLE: "Sampled",
};

export const STATUS_LABEL: Record<CheckStatus, string> = {
  PASS: "Passed",
  FAIL: "Failed",
  REVIEW: "Needs a person",
  NOT_APPLICABLE: "Cannot score",
  ERROR: "Checker error",
};

export const TYPE_LABEL: Record<string, string> = {
  VERBATIM: "Script",
  FACTUAL: "Fact",
  BEHAVIOUR: "Behaviour",
};

export function agentLabel(id: string) {
  if (id === "agent_a") return "Marco Santos";
  if (id === "agent_b") return "Aisha Rahman";
  return id.replaceAll("_", " ");
}

export function speakerLabel(
  speaker: string | null | undefined,
  names?: { agent?: string; customer?: string },
) {
  const s = (speaker ?? "").toLowerCase();
  if (s === "agent" || s === "marco") return names?.agent || "Agent";
  if (s === "customer" || s === "helen") return names?.customer || "Customer";
  if (!speaker || s === "unknown") return "Unknown speaker";
  return speaker;
}

export const STATUS_RANK: Record<string, number> = {
  FAIL: 0,
  ERROR: 1,
  REVIEW: 2,
  PASS: 3,
  NOT_APPLICABLE: 4,
};
