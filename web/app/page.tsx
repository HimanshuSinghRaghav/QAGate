import type { Metadata } from "next";
import Link from "next/link";
import { GateBadge } from "@/components/gate-badge";
import { ClickRow } from "@/components/shell";
import { ButtonLink, EmptyState, PageHeader, Panel } from "@/components/ui";
import { fetchAgents, fetchDashboard, fetchQueue } from "@/lib/api";
import { formatPct } from "@/lib/format";

export const metadata: Metadata = { title: "Home" };
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let overview: Awaited<ReturnType<typeof fetchDashboard>> | null = null;
  let agents: Awaited<ReturnType<typeof fetchAgents>> = [];
  let inbox: Awaited<ReturnType<typeof fetchQueue>> = [];
  let error: string | null = null;
  try {
    [overview, agents, inbox] = await Promise.all([
      fetchDashboard(),
      fetchAgents(),
      fetchQueue(),
    ]);
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  if (!overview) {
    return (
      <EmptyState
        title="API offline"
        body={error ?? "Start the backend on :8000."}
      />
    );
  }

  const kpis = [
    { label: "Sales scored", value: overview.totals.sales_scored, href: "/leads" },
    { label: "Can ship", value: overview.totals.auto_approved, href: "/queue?decision=AUTO_APPROVED" },
    { label: "Stopped", value: overview.totals.held, href: "/queue?decision=HELD" },
    { label: "Needs QA", value: overview.totals.qa_review, href: "/queue?decision=QA_REVIEW" },
    { label: "First-pass yield", value: formatPct(overview.first_pass_yield_pct) },
    { label: "Critical fail rate", value: formatPct(overview.critical_fail_rate_pct) },
  ];

  const openInbox = inbox.filter(
    (row) => row.gate_decision === "HELD" || row.gate_decision === "QA_REVIEW",
  );

  return (
    <div className="space-y-md">
      <PageHeader
        eyebrow="Home"
        title="Score the sale before it ships"
        description="A FibreLink call is not done at hang-up. Critical fails stop the sale. Uncertainty never auto-passes."
        actions={<ButtonLink href="/queue">Open inbox</ButtonLink>}
      />

      <Panel className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
        {kpis.map((kpi) => {
          const inner = (
            <div className="border-b border-r border-hairline-soft px-md py-sm">
              <p className="type-caption text-stone">{kpi.label}</p>
              <p className="mt-xxs type-heading-4 text-ink">{kpi.value}</p>
            </div>
          );
          return kpi.href ? (
            <Link key={kpi.label} href={kpi.href}>
              {inner}
            </Link>
          ) : (
            <div key={kpi.label}>{inner}</div>
          );
        })}
      </Panel>

      <div className="grid gap-md xl:grid-cols-2">
        <Panel>
          <div className="flex items-center justify-between border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Inbox · stopped and unsure</p>
            <ButtonLink variant="link" href="/queue">
              View all
            </ButtonLink>
          </div>
          <table className="w-full type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                <th className="px-md py-xs type-micro-uppercase text-stone">Customer</th>
                <th className="px-md py-xs type-micro-uppercase text-stone">Issue</th>
                <th className="px-md py-xs type-micro-uppercase text-stone">Gate</th>
              </tr>
            </thead>
            <tbody>
              {openInbox.length === 0 ? (
                <tr>
                  <td className="px-md py-md text-slate" colSpan={3}>
                    No held or QA records.
                  </td>
                </tr>
              ) : (
                openInbox.slice(0, 6).map((row) => (
                  <ClickRow key={row.run_id} href={`/leads/${row.lead_id}`}>
                    <td className="px-md py-sm">
                      <p className="type-body-sm-medium text-brand-blue">
                        {row.customer_name || row.lead_id}
                      </p>
                      <p className="type-caption text-stone">{row.agent_name}</p>
                    </td>
                    <td className="max-w-xs truncate px-md py-sm text-slate">
                      {row.issue || row.gate_reason}
                    </td>
                    <td className="px-md py-sm">
                      <GateBadge decision={row.gate_decision} />
                    </td>
                  </ClickRow>
                ))
              )}
            </tbody>
          </table>
        </Panel>

        <Panel>
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Repeat offences</p>
            <p className="type-caption text-stone">Same critical fail, same agent, three times in seven days.</p>
          </div>
          {overview.repeat_offences.length === 0 ? (
            <p className="px-md py-md type-body-sm text-slate">No team-lead warnings.</p>
          ) : (
            <ul>
              {overview.repeat_offences.map((row) => (
                <li
                  key={`${row.agent_id}-${row.check_id}`}
                  className="border-t border-hairline-soft px-md py-sm first:border-t-0"
                >
                  <p className="type-body-sm-medium">
                    {row.agent_name || row.agent_id} · {row.check_name || row.check_id}
                  </p>
                  <p className="type-caption text-slate">{row.action}</p>
                  <div className="mt-xs flex flex-wrap gap-sm">
                    {row.lead_ids.map((id) => (
                      <Link key={id} href={`/leads/${id}`} className="type-caption text-brand-blue">
                        Lead {id}
                      </Link>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="grid gap-md xl:grid-cols-2">
        <Panel>
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Checks that stop sales</p>
          </div>
          <table className="w-full type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                <th className="px-md py-xs type-micro-uppercase text-stone">Check</th>
                <th className="px-md py-xs type-micro-uppercase text-stone">Fails</th>
                <th className="px-md py-xs type-micro-uppercase text-stone">Share</th>
              </tr>
            </thead>
            <tbody>
              {overview.top_failing_checks.length === 0 ? (
                <tr>
                  <td className="px-md py-md text-slate" colSpan={3}>
                    No critical failures.
                  </td>
                </tr>
              ) : (
                overview.top_failing_checks.map((row) => (
                  <tr key={row.check} className="border-t border-hairline-soft">
                    <td className="px-md py-sm">{row.check}</td>
                    <td className="px-md py-sm">{row.failures}</td>
                    <td className="px-md py-sm">{formatPct(row.share_pct)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Panel>

        <Panel>
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Agents</p>
          </div>
          <table className="w-full type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                {["Agent", "Scored", "Stopped", "QA", "Yield"].map((h) => (
                  <th key={h} className="px-md py-xs type-micro-uppercase text-stone">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {agents.map((row) => (
                <tr key={row.agent_id} className="border-t border-hairline-soft">
                  <td className="px-md py-sm type-body-sm-medium">
                    {row.agent_name || row.agent_id}
                  </td>
                  <td className="px-md py-sm">{row.scored}</td>
                  <td className="px-md py-sm">{row.held}</td>
                  <td className="px-md py-sm">{row.qa_review}</td>
                  <td className="px-md py-sm">{formatPct(row.first_pass_yield_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  );
}
