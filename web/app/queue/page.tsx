import type { Metadata } from "next";
import { GateBadge } from "@/components/gate-badge";
import { ClickRow } from "@/components/shell";
import { EmptyState, PageHeader, Panel, PillTabLink } from "@/components/ui";
import { fetchQueue } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { GateDecision } from "@/lib/types";

export const metadata: Metadata = { title: "Inbox" };
export const dynamic = "force-dynamic";

const TABS: { href: string; label: string; decision?: GateDecision }[] = [
  { href: "/queue", label: "Needs a person" },
  { href: "/queue?decision=HELD", label: "Stopped", decision: "HELD" },
  { href: "/queue?decision=QA_REVIEW", label: "Needs QA", decision: "QA_REVIEW" },
  { href: "/queue?decision=AUTO_APPROVED", label: "Can ship", decision: "AUTO_APPROVED" },
  { href: "/queue?decision=HUMAN_SAMPLE", label: "Sampled", decision: "HUMAN_SAMPLE" },
];

export default async function QueuePage({
  searchParams,
}: {
  searchParams: Promise<{ decision?: string }>;
}) {
  const { decision } = await searchParams;
  let rows: Awaited<ReturnType<typeof fetchQueue>> = [];
  let error: string | null = null;
  try {
    rows = await fetchQueue(decision);
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  const view =
    !decision
      ? rows.filter((row) => row.gate_decision === "HELD" || row.gate_decision === "QA_REVIEW")
      : rows;

  return (
    <div>
      <PageHeader
        eyebrow="Inbox"
        title="Work the sale before it ships"
        description={
          view.length === 1
            ? "1 record. Open it to see expected vs said, then hear the timestamp."
            : `${view.length} records. Open a row to see expected vs said, then hear the timestamp.`
        }
      />
      <div className="mb-sm flex flex-wrap gap-xs">
        {TABS.map((tab) => (
          <PillTabLink
            key={tab.href}
            href={tab.href}
            active={(decision ?? "") === (tab.decision ?? "")}
          >
            {tab.label}
          </PillTabLink>
        ))}
      </div>

      {error ? (
        <EmptyState title="Inbox unavailable" body={error} />
      ) : view.length === 0 ? (
        <EmptyState
          title="Nothing waiting"
          body="Held and low-confidence sales land here. Auto-submits stay out of this list unless you open Can ship."
        />
      ) : (
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[860px] type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                {["Customer", "What happened", "Gate", "Agent", "Plan", "Scored"].map((h) => (
                  <th key={h} className="px-md py-xs type-micro-uppercase text-stone">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {view.map((row) => (
                <ClickRow key={row.run_id} href={`/leads/${row.lead_id}`}>
                  <td className="px-md py-sm">
                    <p className="type-body-sm-medium text-brand-blue">
                      {row.customer_name || row.lead_id}
                    </p>
                    <p className="type-caption text-stone">Lead {row.lead_id}</p>
                  </td>
                  <td className="max-w-md px-md py-sm text-slate">
                    {row.issue || row.gate_reason}
                  </td>
                  <td className="px-md py-sm">
                    <GateBadge decision={row.gate_decision} />
                  </td>
                  <td className="px-md py-sm">{row.agent_name || "—"}</td>
                  <td className="px-md py-sm">{row.plan_name || "—"}</td>
                  <td className="whitespace-nowrap px-md py-sm text-steel">
                    {formatDate(row.scored_at)}
                  </td>
                </ClickRow>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  );
}
