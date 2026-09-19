import type { Metadata } from "next";
import { GateBadge } from "@/components/gate-badge";
import { ClickRow } from "@/components/shell";
import { EmptyState, PageHeader, Panel } from "@/components/ui";
import { fetchLeads } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = { title: "Leads" };
export const dynamic = "force-dynamic";

export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  let rows: Awaited<ReturnType<typeof fetchLeads>> = [];
  let error: string | null = null;
  try {
    rows = await fetchLeads();
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  const query = q?.trim().toLowerCase() ?? "";
  const filtered = query
    ? rows.filter((row) =>
        [
          row.lead_id,
          row.customer_name,
          row.agent_name,
          row.plan_name,
          row.retailer_name,
          row.campaign_label,
          row.site_label,
          row.issue,
        ]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query)),
      )
    : rows;

  return (
    <div>
      <PageHeader
        eyebrow="Leads"
        title="Every scored sale"
        description={
          query
            ? `${filtered.length} of ${rows.length} matching “${q}”.`
            : `${rows.length} sales. Open a row to see the customer, rate card, and what the agent said.`
        }
      />

      {error ? (
        <EmptyState title="Leads unavailable" body={error} />
      ) : filtered.length === 0 ? (
        <EmptyState title="No matching leads" body="Clear search or score a lead first." />
      ) : (
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[720px] type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                {["Customer", "Gate", "Agent", "Plan", "Scored at"].map((h) => (
                  <th key={h} className="px-md py-xs type-micro-uppercase text-stone">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <ClickRow key={row.lead_id} href={`/leads/${row.lead_id}`}>
                  <td className="px-md py-sm">
                    <p className="type-body-sm-medium text-brand-blue">{row.customer_name}</p>
                    <p className="type-caption text-stone">Lead {row.lead_id}</p>
                  </td>
                  <td className="px-md py-sm">
                    <GateBadge decision={row.gate_decision} />
                  </td>
                  <td className="px-md py-sm">{row.agent_name}</td>
                  <td className="px-md py-sm">{row.plan_name}</td>
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
