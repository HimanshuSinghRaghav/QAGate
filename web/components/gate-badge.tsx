import { Badge } from "@/components/ui";
import { GATE_LABEL, STATUS_LABEL, TYPE_LABEL } from "@/lib/format";
import type { CheckStatus, GateDecision } from "@/lib/types";

export function GateBadge({ decision }: { decision: GateDecision | null }) {
  if (!decision) {
    return <Badge tone="purple">Unscored</Badge>;
  }
  const tone =
    decision === "AUTO_APPROVED"
      ? "success"
      : decision === "HELD"
        ? "coral"
        : decision === "HUMAN_SAMPLE"
          ? "yellow"
          : "purple";
  return <Badge tone={tone}>{GATE_LABEL[decision]}</Badge>;
}

export function StatusBadge({ status }: { status: CheckStatus }) {
  const tone =
    status === "PASS"
      ? "success"
      : status === "FAIL"
        ? "coral"
        : status === "REVIEW"
          ? "purple"
          : status === "ERROR"
            ? "coral"
            : "yellow";
  return <Badge tone={tone}>{STATUS_LABEL[status]}</Badge>;
}

export function TypeBadge({ type }: { type: string }) {
  const tone =
    type === "VERBATIM" ? "yellow" : type === "BEHAVIOUR" ? "coral" : "purple";
  return <Badge tone={tone}>{TYPE_LABEL[type] ?? type}</Badge>;
}
