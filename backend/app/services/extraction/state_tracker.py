"""Conversation state, not first-occurrence matching.

In the supplied call the delivery address is asserted three times and changes:
same-as-service -> [DELIVERY_ADDRESS] -> agent re-reads the service address ->
customer corrects again. Taking the first mention gives a confident false PASS.
This module resolves the *latest asserted value* and reports the conflict.
"""
from dataclasses import dataclass

from app.services.extraction.facts import FactStore, Observation


@dataclass
class ResolvedFact:
    key: str
    value: object
    confidence: float
    winner: Observation | None
    trail: list[Observation]
    conflicted: bool
    reason: str

    @property
    def found(self) -> bool:
        return self.winner is not None


def resolve(store: FactStore, key: str, *, prefer_speaker: str | None = None) -> ResolvedFact:
    trail = store.get(key)
    if not trail:
        return ResolvedFact(key, None, 0.0, None, [], False, "No mention found in transcript.")

    ordered = sorted(trail, key=lambda o: o.segment_index)
    candidates = [o for o in ordered if o.confidence >= 0.35] or ordered

    if prefer_speaker:
        speaker_matched = [
            o for o in candidates
            if o.speaker == prefer_speaker and o.speaker_confidence >= 0.5
        ]
        if speaker_matched:
            candidates = speaker_matched

    winner = candidates[-1]
    distinct = {str(o.value) for o in candidates}
    conflicted = len(distinct) > 1

    if conflicted:
        # A value that changed mid-call is a real signal. Never average it away:
        # take the last assertion and drop confidence so the gate can route it.
        confidence = min(winner.confidence, 0.75) - 0.10 * (len(distinct) - 1)
        reason = (
            f"{len(distinct)} different values asserted during the call "
            f"({', '.join(sorted(distinct))}); latest assertion taken as final."
        )
    else:
        agreement_bonus = 0.03 * (len(candidates) - 1)
        confidence = min(0.99, winner.confidence + agreement_bonus)
        reason = (
            f"Consistent across {len(candidates)} mention(s)."
            if len(candidates) > 1 else "Single mention."
        )

    return ResolvedFact(
        key=key,
        value=winner.value,
        confidence=round(max(confidence, 0.0), 3),
        winner=winner,
        trail=ordered,
        conflicted=conflicted,
        reason=reason,
    )
