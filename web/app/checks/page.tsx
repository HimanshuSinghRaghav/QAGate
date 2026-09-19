import type { Metadata } from "next";
import { TypeBadge } from "@/components/gate-badge";
import { Badge, EmptyState, PageHeader, Panel } from "@/components/ui";
import { fetchChecks } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = { title: "Playbooks" };
export const dynamic = "force-dynamic";

export default async function ChecksPage() {
  let checks: Awaited<ReturnType<typeof fetchChecks>> = [];
  let error: string | null = null;
  try {
    checks = await fetchChecks();
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  return (
    <div>
      <PageHeader
        eyebrow="Playbooks"
        title="What the engine scores"
        description="Script, fact, and behaviour checks. Scoring uses the version live on the call date, not today's wording."
      />

      {error ? (
        <EmptyState title="Library unavailable" body={error} />
      ) : (
        <Panel className="overflow-x-auto">
          <table className="w-full min-w-[860px] type-body-sm">
            <thead className="bg-surface-soft text-left">
              <tr>
                {["Name", "Type", "Severity", "Version", "Handler", "Effective"].map((h) => (
                  <th key={h} className="px-md py-xs type-micro-uppercase text-stone">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {checks.map((check) => (
                <tr
                  key={`${check.check_id}-${check.version}`}
                  className="border-t border-hairline-soft"
                >
                  <td className="px-md py-sm">
                    <p className="type-body-sm-medium">{check.name}</p>
                    <p className="type-caption text-stone">{check.check_id}</p>
                  </td>
                  <td className="px-md py-sm">
                    <TypeBadge type={check.type} />
                  </td>
                  <td className="px-md py-sm">
                    {check.critical ? (
                      <Badge tone="coral">Critical</Badge>
                    ) : (
                      <Badge tone="yellow">Coaching</Badge>
                    )}
                  </td>
                  <td className="px-md py-sm">v{check.version}</td>
                  <td className="px-md py-sm text-slate">{check.handler ?? "—"}</td>
                  <td className="px-md py-sm text-steel">
                    {formatDate(check.effective_from)}
                    {check.effective_to ? ` → ${formatDate(check.effective_to)}` : " → open"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  );
}
