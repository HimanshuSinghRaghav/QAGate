import { LeadWorkspace } from "@/components/lead-workspace";
import { EmptyState } from "@/components/ui";
import { fetchAudit, fetchLead, fetchResults, fetchTranscript } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const record = await fetchLead(id);
    return { title: record.customer_name };
  } catch {
    return { title: `Lead ${id}` };
  }
}

export default async function LeadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const [results, transcript, audit, record] = await Promise.all([
      fetchResults(id),
      fetchTranscript(id),
      fetchAudit(id),
      fetchLead(id),
    ]);
    return (
      <LeadWorkspace
        leadId={id}
        initial={results}
        transcript={transcript}
        audit={audit}
        record={record}
      />
    );
  } catch (err) {
    return (
      <EmptyState
        title="This sale is not ready to review"
        body={err instanceof Error ? err.message : "Score this lead from the API first."}
      />
    );
  }
}
