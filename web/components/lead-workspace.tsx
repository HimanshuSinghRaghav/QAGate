"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { GateBadge, StatusBadge, TypeBadge } from "@/components/gate-badge";
import {
  Badge,
  Button,
  ButtonLink,
  Field,
  PageHeader,
  Panel,
  PillTab,
  SearchField,
  TextArea,
  TextInput,
} from "@/components/ui";
import { fetchAudit, overrideResult, scoreLead } from "@/lib/api";
import { cn } from "@/lib/cn";
import {
  TYPE_LABEL,
  formatClock,
  formatConfidence,
  formatDate,
  formatMoney,
  formatScore,
  humanize,
  prettyFact,
  speakerLabel,
  STATUS_RANK,
} from "@/lib/format";
import type {
  AuditEvent,
  CheckResult,
  CheckStatus,
  Evidence,
  LeadCase,
  ScoredLead,
  Segment,
  Transcript,
} from "@/lib/types";

type CheckTab = "critical" | "coaching" | "unscorable";
type DetailTab = "transcript" | "evidence" | "history";

export function LeadWorkspace({
  leadId,
  initial,
  transcript,
  audit,
  record,
}: {
  leadId: string;
  initial: ScoredLead;
  transcript: Transcript;
  audit: AuditEvent[];
  record: LeadCase | null;
}) {
  const [bundle, setBundle] = useState(initial);
  const [events, setEvents] = useState(audit);
  const [checkTab, setCheckTab] = useState<CheckTab>("critical");
  const [detailTab, setDetailTab] = useState<DetailTab>("evidence");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(pickDefault(initial));
  const [segmentId, setSegmentId] = useState<string | null>(null);
  const [seek, setSeek] = useState<{ ms: number; key: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const names = {
    agent: record?.agent_name || bundle.case?.agent_name || "Agent",
    customer: record?.customer_first_name || bundle.case?.customer_first_name || "Customer",
  };
  const customer = record?.customer_name || bundle.case?.customer_name || `Lead ${leadId}`;
  const retailer = record?.retailer_name || bundle.case?.retailer_name || "Retailer";
  const planName = record?.plan_name || bundle.case?.plan_name || "Plan";
  const headline = record?.gate_headline || bundle.case?.gate_headline || bundle.run.gate_reason;
  const nextStep = record?.gate_next_step || bundle.case?.gate_next_step;
  const purpose = record?.purpose || bundle.case?.purpose;

  const allChecks = [...bundle.critical, ...bundle.non_critical, ...bundle.unscorable];

  const checks = useMemo(() => {
    const pool =
      checkTab === "critical"
        ? bundle.critical
        : checkTab === "coaching"
          ? bundle.non_critical
          : bundle.unscorable;
    return [...pool].sort(
      (a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9),
    );
  }, [bundle, checkTab]);

  const selected =
    allChecks.find((c) => c.id === selectedId) ?? checks[0] ?? null;

  const openIssues = useMemo(
    () =>
      bundle.critical
        .filter((c) => c.status === "FAIL" || c.status === "REVIEW" || c.status === "ERROR")
        .sort((a, b) => (STATUS_RANK[a.status] ?? 9) - (STATUS_RANK[b.status] ?? 9)),
    [bundle],
  );

  useEffect(() => {
    if (!selected) return;
    const first = selected.evidence.find((e) => e.segment_id || e.start_ms != null);
    if (first?.segment_id) setSegmentId(first.segment_id);
  }, [selected?.id]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return transcript.segments;
    return transcript.segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [query, transcript.segments]);

  function jumpToEvidence(item: CheckResult) {
    setSelectedId(item.id);
    setCheckTab(item.status === "NOT_APPLICABLE" ? "unscorable" : item.critical ? "critical" : "coaching");
    setDetailTab("evidence");
    const first = item.evidence.find((e) => e.start_ms != null) ?? item.evidence[0];
    if (first?.segment_id) setSegmentId(first.segment_id);
    if (first?.start_ms != null) setSeek({ ms: first.start_ms, key: Date.now() });
  }

  async function rescore() {
    setBusy(true);
    setError(null);
    try {
      const next = await scoreLead(leadId);
      setBundle(next);
      setEvents(await fetchAudit(leadId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rescore failed");
    } finally {
      setBusy(false);
    }
  }

  async function onOverride(payload: {
    new_status: Extract<CheckStatus, "PASS" | "FAIL" | "REVIEW">;
    actor: string;
    reason: string;
  }) {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const next = await overrideResult(selected.id, payload);
      setBundle((prev) => {
        const patch = (rows: CheckResult[]) =>
          rows.map((row) => (row.id === next.result.id ? next.result : row));
        return {
          run: next.run,
          critical: patch(prev.critical),
          non_critical: patch(prev.non_critical),
          unscorable: patch(prev.unscorable),
          case: prev.case,
        };
      });
      setEvents(await fetchAudit(leadId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Override failed");
    } finally {
      setBusy(false);
    }
  }

  const { run } = bundle;
  const crmRows = record?.crm?.length ? record.crm : bundle.case?.crm ?? [];
  const planRows = record?.plan_rows?.length ? record.plan_rows : bundle.case?.plan_rows ?? [];

  return (
    <div className="space-y-md">
      <PageHeader
        eyebrow={`${retailer} · ${planName}`}
        title={customer}
        description={`Lead ${leadId} · ${names.agent} sold this call. ${purpose ?? "The gate decides if the sale can auto-submit."}`}
        actions={
          <>
            <GateBadge decision={run.gate_decision} />
            {run.sampled_for_human ? <Badge tone="promo">Sampled for QA</Badge> : null}
            {/* <Button variant="secondary" onClick={rescore} disabled={busy}>
              {busy ? "Working…" : "Rescore"}
            </Button> */}
            <ButtonLink variant="secondary" href="/queue">
              Inbox
            </ButtonLink>
          </>
        }
      />

      <Panel>
        <div className="border-b border-hairline-soft px-md py-sm">
          <p className="type-body-sm-medium">Customer information</p>
          <p className="type-caption text-stone">
            Lead {leadId} · {retailer} {planName}
          </p>
        </div>
        <dl className="grid grid-cols-2 gap-md p-md md:grid-cols-4 xl:grid-cols-8">
          <Field label="Customer">{customer}</Field>
          <Field label="Agent">{names.agent}</Field>
          <Field label="Team lead">{record?.tl_name || "Priya Nair"}</Field>
          <Field label="Campaign">{record?.campaign_label || "—"}</Field>
          <Field label="Site">{record?.site_label || "—"}</Field>
          <Field label="Call date">{formatDate(run.call_date)}</Field>
          <Field label="Score">{formatScore(run.score_with_fatals)}</Field>
          <Field label="Timing">
            {transcript.timing_source === "asr" ? "Word-level timestamps" : "Estimated timestamps"}
          </Field>
        </dl>
      </Panel>

      <div className="grid gap-md xl:grid-cols-2">
        <Panel>
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Submitted in CRM</p>
            <p className="type-caption text-stone">What the sale record holds for {customer}.</p>
          </div>
          <dl className="grid grid-cols-1 gap-sm p-md sm:grid-cols-2">
            {crmRows.length === 0 ? (
              <p className="type-body-sm text-slate">No CRM snapshot.</p>
            ) : (
              crmRows.map((row) => (
                <Field key={row.label} label={row.label}>
                  {row.value}
                </Field>
              ))
            )}
          </dl>
        </Panel>
        <Panel>
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">Rate card · what should have been said</p>
            <p className="type-caption text-stone">{retailer} {planName}. Factual checks compare the call to this, not to another model.</p>
          </div>
          <dl className="grid grid-cols-1 gap-sm p-md sm:grid-cols-2">
            {planRows.length === 0 ? (
              <p className="type-body-sm text-slate">No rate card on this lead.</p>
            ) : (
              planRows.map((row) => (
                <Field key={row.label} label={row.label}>
                  {row.value}
                </Field>
              ))
            )}
          </dl>
        </Panel>
      </div>

      {error ? (
        <div className="rounded-md border border-brand-red-dark bg-brand-red px-md py-sm type-body-sm text-coral-dark">
          {error}
        </div>
      ) : null}

      <AudioBar leadId={leadId} seek={seek} />

      <Panel
        className={cn(
          "px-md py-sm",
          run.gate_decision === "HELD" && "border-brand-red-dark bg-brand-red",
          run.gate_decision === "QA_REVIEW" && "bg-surface-pricing-featured",
          run.gate_decision === "AUTO_APPROVED" && "bg-surface-soft",
        )}
      >
        <p className="type-heading-5 text-ink">{headline}</p>
        <p className="mt-xxs type-body-sm text-slate">
          {openIssues[0]?.issue ?? run.gate_reason}
        </p>
        {nextStep ? <p className="mt-xs type-caption text-steel">{nextStep}</p> : null}
      </Panel>

      {openIssues.length > 0 ? (
        <Panel className="overflow-hidden">
          <div className="border-b border-hairline-soft px-md py-sm">
            <p className="type-body-sm-medium">
              Open issues · {openIssues.length}
            </p>
            <p className="type-caption text-stone">
              Expected vs what was said. Click a row to hear that timestamp.
            </p>
          </div>
          <ul>
            {openIssues.map((item) => {
              const expected = item.expected_label || prettyFact(item.expected);
              const observed = item.observed_label || prettyFact(item.observed);
              const mismatch = expected !== "—" && observed !== "—" && expected !== observed;
              return (
                <li key={item.id} className="border-t border-hairline-soft first:border-t-0">
                  <button
                    type="button"
                    onClick={() => jumpToEvidence(item)}
                    className="flex w-full flex-col gap-xs px-md py-sm text-left"
                  >
                    <div className="flex flex-wrap items-center gap-xs">
                      <StatusBadge status={item.status} />
                      <span className="type-body-sm-medium">{item.check_name}</span>
                      <span className="type-caption text-stone">
                        {item.evidence[0]?.timestamp ?? "No timestamp"}
                      </span>
                    </div>
                    {mismatch ? (
                      <p className="type-body-sm text-slate">
                        <span className="text-stone">{item.expected_caption || "Expected"}: </span>
                        <span className="type-body-sm-medium text-ink">{expected}</span>
                        <span className="mx-xs text-stone">→</span>
                        <span className="text-stone">{item.observed_caption || "Said"}: </span>
                        <span className="type-body-sm-medium text-coral-dark">{observed}</span>
                      </p>
                    ) : (
                      <p className="type-body-sm text-slate">{item.issue || item.reason}</p>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      ) : null}

      <div className="grid gap-md xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.2fr)]">
        <Panel className="overflow-hidden">
          <div className="flex flex-wrap gap-xs border-b border-hairline-soft px-md py-sm">
            <PillTab active={checkTab === "critical"} onClick={() => setCheckTab("critical")}>
              Critical {bundle.critical.length}
            </PillTab>
            <PillTab active={checkTab === "coaching"} onClick={() => setCheckTab("coaching")}>
              Coaching {bundle.non_critical.length}
            </PillTab>
            <PillTab active={checkTab === "unscorable"} onClick={() => setCheckTab("unscorable")}>
              Cannot score {bundle.unscorable.length}
            </PillTab>
          </div>
          <div className="max-h-[70vh] overflow-auto">
            <table className="w-full type-body-sm">
              <thead className="sticky top-0 bg-surface-soft text-left">
                <tr>
                  <th className="px-md py-xs type-micro-uppercase text-stone">Check</th>
                  <th className="px-md py-xs type-micro-uppercase text-stone">Result</th>
                  <th className="px-md py-xs type-micro-uppercase text-stone">Time</th>
                </tr>
              </thead>
              <tbody>
                {checks.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => jumpToEvidence(item)}
                    className={cn(
                      "cursor-pointer border-t border-hairline-soft",
                      selected?.id === item.id ? "bg-surface-yellow" : "bg-canvas",
                    )}
                  >
                    <td className="px-md py-sm">
                      <p className="type-body-sm-medium">{item.check_name}</p>
                      <p className="type-caption text-stone">
                        {item.type_label || TYPE_LABEL[item.type] || item.type}
                        {item.status !== "PASS" && item.issue
                          ? ` · ${item.issue.replace(`${item.check_name}: `, "")}`
                          : ""}
                      </p>
                    </td>
                    <td className="px-md py-sm">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="px-md py-sm text-steel">
                      {item.evidence[0]?.timestamp ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-sm border-b border-hairline-soft px-md py-sm">
            <div className="flex flex-wrap gap-xs">
              <PillTab
                active={detailTab === "evidence"}
                onClick={() => setDetailTab("evidence")}
              >
                Evidence
              </PillTab>
              <PillTab
                active={detailTab === "transcript"}
                onClick={() => setDetailTab("transcript")}
              >
                Full transcript · {transcript.segments.length}
              </PillTab>
              <PillTab
                active={detailTab === "history"}
                onClick={() => setDetailTab("history")}
              >
                History
              </PillTab>
            </div>
            {detailTab === "transcript" ? (
              <SearchField
                placeholder="Find a word or price"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="max-w-56"
              />
            ) : null}
          </div>

          {detailTab === "transcript" ? (
            <TranscriptPane
              segments={filtered}
              total={transcript.segments.length}
              query={query}
              names={names}
              activeId={segmentId}
              estimated={transcript.timing_source !== "asr"}
              onSelect={(seg) => {
                setSegmentId(seg.id);
                setSeek({ ms: seg.start_ms, key: Date.now() });
              }}
            />
          ) : null}

          {detailTab === "evidence" && selected ? (
            <EvidencePanel
              item={selected}
              names={names}
              busy={busy}
              onJump={(ev) => {
                if (ev.segment_id) setSegmentId(ev.segment_id);
                if (ev.start_ms != null) setSeek({ ms: ev.start_ms, key: Date.now() });
                setDetailTab("transcript");
              }}
              onOverride={onOverride}
            />
          ) : null}

          {detailTab === "evidence" && !selected ? (
            <p className="px-md py-md type-body-sm text-slate">Select a check.</p>
          ) : null}

          {detailTab === "history" ? (
            <ul className="max-h-[70vh] divide-y divide-hairline-soft overflow-auto">
              {events.length === 0 ? (
                <li className="px-md py-md type-body-sm text-slate">No events yet.</li>
              ) : (
                events.map((event) => (
                  <li key={event.id} className="px-md py-sm">
                    <p className="type-body-sm-medium">
                      {event.event_label || event.event.replaceAll("_", " ")}
                    </p>
                    <p className="type-caption text-stone">
                      {event.actor} · {formatDate(event.at)}
                    </p>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </Panel>
      </div>
    </div>
  );
}

function trailValue(obs: Evidence, item: CheckResult) {
  if (obs.value == null || obs.value === "") return obs.text ?? "—";
  const unit = item.expected && typeof item.expected.unit === "string" ? item.expected.unit : "";
  if (unit.toUpperCase().includes("AUD") || unit === "$") {
    return formatMoney(obs.value);
  }
  return humanize(obs.value);
}

function pickDefault(bundle: ScoredLead) {
  const pool = [...bundle.critical, ...bundle.non_critical];
  return (
    pool.find((c) => c.status === "FAIL")?.id ??
    pool.find((c) => c.status === "REVIEW")?.id ??
    pool[0]?.id ??
    null
  );
}

function TranscriptPane({
  segments,
  total,
  query,
  names,
  activeId,
  estimated,
  onSelect,
}: {
  segments: Segment[];
  total: number;
  query: string;
  names: { agent: string; customer: string };
  activeId: string | null;
  estimated: boolean;
  onSelect: (seg: Segment) => void;
}) {
  const activeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "center" });
  }, [activeId]);

  return (
    <div className="max-h-[70vh] overflow-auto">
      <div className="border-b border-hairline-soft px-md py-sm">
        <p className="type-caption text-stone">
          Complete call · {total} lines
          {estimated ? " · timestamps are estimated from the transcript" : " · word-level timestamps"}
          . Click a line to play from that second.
        </p>
      </div>
      {segments.length === 0 ? (
        <p className="px-md py-md type-body-sm text-slate">
          No lines match “{query}”.
        </p>
      ) : (
        segments.map((seg) => {
          const active = seg.id === activeId;
          return (
            <button
              key={seg.id}
              ref={active ? activeRef : undefined}
              type="button"
              id={`seg-${seg.id}`}
              onClick={() => onSelect(seg)}
              className={cn(
                "flex w-full gap-sm border-b border-hairline-soft px-md py-xs text-left",
                active ? "bg-surface-yellow" : "bg-canvas",
              )}
            >
              <span className="w-12 shrink-0 type-caption text-stone">{seg.timestamp}</span>
              <span className="min-w-0 flex-1">
                <span className="type-caption-bold text-slate">
                  {speakerLabel(seg.speaker, names)}
                </span>
                <span className="mt-xxs block type-body-sm text-ink">{seg.text}</span>
              </span>
            </button>
          );
        })
      )}
    </div>
  );
}

function AudioBar({
  leadId,
  seek,
}: {
  leadId: string;
  seek: { ms: number; key: number } | null;
}) {
  const ref = useRef<HTMLAudioElement>(null);
  const [mounted, setMounted] = useState(false);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    fetch(`/api/audio/${leadId}`, { method: "HEAD" })
      .then((res) => setAvailable(res.ok))
      .catch(() => setAvailable(false));
  }, [leadId]);

  useEffect(() => {
    if (!seek || !ref.current) return;
    ref.current.currentTime = seek.ms / 1000;
    void ref.current.play().catch(() => undefined);
  }, [seek]);

  return (
    <Panel className="flex flex-wrap items-center gap-md px-md py-sm">
      <div className="min-w-[180px]">
        <p className="type-caption text-stone">Recording</p>
        <p className="type-body-sm-medium">
          {seek
            ? `Playing from ${formatClock(seek.ms)} — you do not need the whole call.`
            : "Open a failed check to jump to the 20 seconds that matter."}
        </p>
      </div>
      {mounted && available ? (
        <audio
          ref={ref}
          className="min-w-[240px] flex-1"
          controls
          preload="metadata"
          src={`/api/audio/${leadId}`}
        />
      ) : (
        <div className="h-10 min-w-60 flex-1 rounded-md bg-surface" />
      )}
    </Panel>
  );
}

function EvidencePanel({
  item,
  names,
  busy,
  onJump,
  onOverride,
}: {
  item: CheckResult;
  names: { agent: string; customer: string };
  busy: boolean;
  onJump: (ev: Evidence) => void;
  onOverride: (payload: {
    new_status: Extract<CheckStatus, "PASS" | "FAIL" | "REVIEW">;
    actor: string;
    reason: string;
  }) => Promise<void>;
}) {
  const [actor, setActor] = useState("Priya Nair");
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<Extract<CheckStatus, "PASS" | "FAIL" | "REVIEW">>(
    item.status === "FAIL" ? "PASS" : item.status === "PASS" ? "FAIL" : "PASS",
  );

  useEffect(() => {
    setReason("");
    setStatus(item.status === "FAIL" ? "PASS" : item.status === "PASS" ? "FAIL" : "PASS");
  }, [item.id, item.status]);

  const expected = item.expected_label || prettyFact(item.expected);
  const observed = item.observed_label || prettyFact(item.observed);
  const mismatch = expected !== "—" && observed !== "—" && expected !== observed;
  const firstCue = item.evidence.find((e) => e.start_ms != null);

  return (
    <div className="max-h-[70vh] overflow-auto p-md">
      <div className="flex items-start justify-between gap-sm">
        <div>
          <p className="type-caption text-stone">
            {item.type_label || TYPE_LABEL[item.type] || item.type}
            {item.critical ? " · stops the sale if it fails" : " · coaching only"}
          </p>
          <h2 className="type-heading-5">{item.check_name}</h2>
        </div>
        <StatusBadge status={item.status} />
      </div>
      <div className="mt-sm flex flex-wrap gap-xs">
        <TypeBadge type={item.type} />
        {item.critical ? <Badge tone="coral">Critical</Badge> : <Badge tone="yellow">Coaching</Badge>}
        <Badge tone="neutral">{formatConfidence(item.confidence)} confidence</Badge>
      </div>
      <p className="mt-sm type-body-sm text-slate">{item.reason}</p>

      {(expected !== "—" || observed !== "—") ? (
        <dl className="mt-md grid gap-sm md:grid-cols-2">
          <div className="rounded-md bg-surface p-sm">
            <dt className="type-caption text-stone">
              {item.expected_caption || "Expected"}
            </dt>
            <dd className="type-body-sm-medium">{expected}</dd>
          </div>
          <div
            className={cn(
              "rounded-md p-sm",
              mismatch ? "border border-brand-red-dark bg-brand-red" : "bg-surface",
            )}
          >
            <dt className="type-caption text-stone">
              {item.observed_caption || "Said on the call"}
            </dt>
            <dd className={cn("type-body-sm-medium", mismatch && "text-coral-dark")}>
              {observed}
            </dd>
          </div>
        </dl>
      ) : null}

      {firstCue?.start_ms != null ? (
        <Button
          type="button"
          variant="secondary"
          className="mt-md"
          onClick={() => onJump(firstCue)}
        >
          Play from {firstCue.timestamp ?? formatClock(firstCue.start_ms)}
        </Button>
      ) : null}

      <p className="mt-md type-caption text-stone">Proof on the transcript</p>
      <ul className="mt-xs space-y-xs">
        {item.evidence.length === 0 ? (
          <li className="type-caption text-slate">No transcript line attached.</li>
        ) : (
          item.evidence.map((ev, i) => (
            <li key={`${ev.segment_id ?? "ev"}-${ev.start_ms ?? "t"}-${i}`}>
              <button
                type="button"
                onClick={() => onJump(ev)}
                className="w-full rounded-md border border-hairline-soft px-sm py-xs text-left"
              >
                <span className="type-caption-bold text-brand-blue">
                  {ev.timestamp ?? formatClock(ev.start_ms)} ·{" "}
                  {speakerLabel(ev.speaker, names)}
                </span>
                <span className="mt-xxs block type-body-sm">“{ev.text}”</span>
              </button>
            </li>
          ))
        )}
      </ul>

      {item.observation_trail.length > 1 ? (
        <>
          <p className="mt-md type-caption text-stone">How the story changed on the call</p>
          <ol className="mt-xs space-y-xs">
            {item.observation_trail.map((obs, i) => (
              <li
                key={`${obs.segment_id ?? "obs"}-${obs.start_ms ?? "t"}-${i}`}
                className="rounded-md bg-surface-soft px-sm py-xs"
              >
                <p className="type-caption text-stone">
                  {obs.timestamp} · {obs.note || "mention"}
                </p>
                <p className="type-body-sm">
                  {trailValue(obs, item)}
                </p>
              </li>
            ))}
          </ol>
        </>
      ) : null}

      <form
        className="mt-md space-y-sm border-t border-hairline-soft pt-md"
        onSubmit={(e) => {
          e.preventDefault();
          void onOverride({ new_status: status, actor, reason });
        }}
      >
        <p className="type-body-sm-medium">Human override</p>
        <p className="type-caption text-slate">
          Logs who decided and why, then re-runs the gate. It does not rewrite the sale.
        </p>
        <div className="flex flex-wrap gap-xs">
          {(["PASS", "FAIL", "REVIEW"] as const).map((s) => (
            <PillTab key={s} type="button" active={status === s} onClick={() => setStatus(s)}>
              {s === "PASS" ? "Pass" : s === "FAIL" ? "Fail" : "Needs a person"}
            </PillTab>
          ))}
        </div>
        <TextInput
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          placeholder="Your name"
          aria-label="Reviewer name"
          required
        />
        <TextArea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why are you changing the machine’s call?"
          aria-label="Override reason"
          required
          minLength={3}
        />
        <Button type="submit" disabled={busy || reason.trim().length < 3}>
          Save override
        </Button>
      </form>
    </div>
  );
}
