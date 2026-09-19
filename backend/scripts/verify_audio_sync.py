"""Prove the transcript timestamps point at the right moment in the recording.

Three independent things are checked, because a timestamp that is merely
plausible is the failure mode we care about:

  1. The manifest's duration equals the mp3's real duration. Any gap means the
     chunks were joined in a way that shifted the timeline.
  2. Every parsed segment maps onto the timed payload, in order, inside the audio.
  3. Sampled segments open on speech - not a second early, and not partway
     through the word either. Silence *inside* a span is fine, since people pause
     mid-sentence.

    python scripts/verify_audio_sync.py
    python scripts/verify_audio_sync.py --lead 3613790 --sample 40
"""
from __future__ import annotations

import argparse
import array
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed.data.audio import Recording, recording_for  # noqa: E402
from app.seed.data.leads import LEADS  # noqa: E402
from app.services.transcript import parser  # noqa: E402
from app.services.transcript.timing import (  # noqa: E402
    TimingAlignmentError, apply_asr_timings,
)

PROBE_RATE = 16000
FRAME_MS = 10
SILENCE_THRESHOLD = 300
MAX_DURATION_DRIFT_MS = 50
MAX_ONSET_GAP_MS = 120
LOOKBACK_MS = 60
# Sentences that run together inside one breath have no audible boundary, so
# where one ends and the next begins is soft to within a few tens of ms. Only a
# pause this long counts as a break the timestamps are expected to land on.
BREAK_MS = 200


def clock(ms: int) -> str:
    return f"{ms // 60000}:{ms // 1000 % 60:02d}"


def mp3_duration_ms(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return round(float(out) * 1000)


class Track:
    """The whole recording decoded once, as a frame-by-frame map of where it is loud.

    Decoding up front matters for correctness, not just speed: seeking into an mp3
    only lands on a frame boundary, which is enough slack to make a correct
    timestamp look wrong.
    """

    def __init__(self, path: Path) -> None:
        pcm = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path),
             "-f", "s16le", "-ac", "1", "-ar", str(PROBE_RATE), "pipe:1"],
            capture_output=True, check=True,
        ).stdout
        samples = array.array("h")
        samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
        frame = max(PROBE_RATE * FRAME_MS // 1000, 1)
        self.audible = [
            max(abs(v) for v in samples[i: i + frame]) > SILENCE_THRESHOLD
            for i in range(0, len(samples) - frame + 1, frame)
        ]
        self.duration_ms = round(len(samples) * 1000 / PROBE_RATE)

    def _frames(self, start_ms: int, end_ms: int) -> list[bool]:
        lo = max(start_ms // FRAME_MS, 0)
        hi = min(-(-end_ms // FRAME_MS), len(self.audible))
        return self.audible[lo:hi]

    def onset_gap_ms(self, start_ms: int, end_ms: int) -> int | None:
        """How long after the span starts the voice comes in; None if never."""
        frames = self._frames(start_ms, end_ms)
        for i, loud in enumerate(frames):
            if loud:
                return max((start_ms // FRAME_MS + i) * FRAME_MS - start_ms, 0)
        return None

    def opens_mid_word(self, start_ms: int) -> bool:
        """True when sound runs straight through the start rather than beginning at it.

        The previous speaker's tail decaying nearby is fine; sound that never stops
        on its way into the span means the word had already begun.
        """
        if start_ms < LOOKBACK_MS:
            return False
        frames = self._frames(start_ms - LOOKBACK_MS, start_ms + LOOKBACK_MS)
        return bool(frames) and all(frames)


def check_lead(spec: dict, sample: int) -> bool:
    lead_id = spec["id"]
    recording: Recording | None = recording_for(lead_id)
    if recording is None:
        print(f"{lead_id}: no recording, transcript will use estimated timings")
        return True

    problems: list[str] = []
    track = Track(recording.path)

    real_ms = mp3_duration_ms(recording.path)
    drift = abs(real_ms - recording.duration_ms)
    if drift > MAX_DURATION_DRIFT_MS:
        problems.append(
            f"manifest says {recording.duration_ms} ms, mp3 is {real_ms} ms "
            f"({drift} ms apart)"
        )

    parsed, _ = parser.parse(spec["transcript"])
    texts = [p.text for p in parsed]
    try:
        spans = apply_asr_timings(recording.tokens, texts)
    except TimingAlignmentError as exc:
        print(f"{lead_id}: FAIL - {exc}")
        return False

    if any(a[1] > b[0] for a, b in zip(spans, spans[1:], strict=False)):
        problems.append("segment spans overlap")
    if spans[-1][1] > real_ms:
        problems.append(f"last segment ends at {clock(spans[-1][1])}, past the audio")

    step = max(len(spans) // sample, 1)
    early: list[str] = []
    clipped: list[str] = []
    gaps: list[int] = []
    for index in range(0, len(spans), step):
        start, end = spans[index]
        if end - start < 200:
            continue
        gap = track.onset_gap_ms(start, end)
        if gap is None:
            early.append(f"{clock(start)} silent {texts[index][:40]!r}")
        elif gap > MAX_ONSET_GAP_MS:
            early.append(f"{clock(start)} +{gap}ms {texts[index][:40]!r}")
        else:
            gaps.append(gap)

        # A segment that follows a real break must not open in the middle of a word.
        previous_end = spans[index - 1][1] if index else 0
        if (gap is not None and start - previous_end > BREAK_MS
                and track.opens_mid_word(start)):
            clipped.append(f"{clock(start)} {texts[index][:40]!r}")

    if early:
        problems.append("spans that open before the speech: " + "; ".join(early[:5]))
    if clipped:
        problems.append("spans that open mid-word: " + "; ".join(clipped[:5]))

    worst = max(gaps) if gaps else 0
    status = "FAIL" if problems else "ok"
    print(
        f"{lead_id}: {status}  audio {clock(real_ms)}  {len(spans)} segments  "
        f"last ends {clock(spans[-1][1])}  drift {drift} ms  "
        f"worst onset +{worst} ms over {len(gaps) + len(early)} sampled"
    )
    for problem in problems:
        print(f"    - {problem}")
    return not problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead", help="one lead id, otherwise every seeded lead")
    ap.add_argument("--sample", type=int, default=25,
                    help="how many segments to listen to per call")
    args = ap.parse_args()

    specs = [s for s in LEADS if not args.lead or s["id"] == args.lead]
    if not specs:
        sys.exit(f"Unknown lead {args.lead}")

    if all(check_lead(spec, args.sample) for spec in specs):
        print("\nTimestamps match the recordings.")
    else:
        sys.exit("\nTimestamps do not match the recordings.")


if __name__ == "__main__":
    main()
