"""Turn the seeded call scripts into demo recordings, with real timings.

Helen = customer, Marco = agent. Each turn is synthesized with the matching voice
using ElevenLabs `with-timestamps`, which returns the audio AND the start/end time
of every character. Those character times are what the transcript is stamped with,
so a timestamp shown next to a check result is the exact moment in the mp3.

Two accuracy rules this file exists to enforce:

  * Never concatenate mp3 frames. Every chunk is decoded to PCM, joined sample by
    sample, and encoded once. Frame-copy concatenation added ~26 ms of encoder
    padding per chunk - about 8.5 s of drift across a 120-turn call.
  * Never estimate. Offsets come from the decoded sample count of each chunk, not
    from a words-per-second guess.

    # key goes in .env as ELEVENLABS_API_KEY
    python scripts/generate_demo_audio.py --list-voices
    python scripts/generate_demo_audio.py                 # all unique calls
    python scripts/generate_demo_audio.py --lead 3613790
    python scripts/generate_demo_audio.py --force         # re-synthesize

Writes demo/audio/{lead}.mp3 and demo/audio/{lead}.timings.json.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API = "https://api.elevenlabs.io/v1"
MODEL = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")
OUTPUT_FORMAT = "mp3_44100_128"

SAMPLE_RATE = 44100
CHANNELS = 1
BYTES_PER_SAMPLE = 2

DEFAULT_HELEN = "XrExE9yKIg1WjnnlVkGX"
DEFAULT_MARCO = "pNInz6obpgDQGcFmaJgB"

UNIQUE_LEADS = ("3613790", "3613791", "3613792")
REUSE = {"3613792": ("3613793", "3613794")}
ALL_REUSED = {dest for dests in REUSE.values() for dest in dests}

TURN_RE = re.compile(r"^(Helen|Marco):\s*(.*)$")
MUTE_SPLIT_RE = re.compile(
    r"(.*?\bmute the recording\.\s*K\?)\s*(Okay\.\s*The recording is already resumed\..*)",
    re.IGNORECASE | re.DOTALL,
)
MUTE_GAP_SECONDS = 4.0

SCRIPTS = ROOT / "demo" / "tts"
AUDIO_DIR = ROOT / "demo" / "audio"
CACHE_DIR = AUDIO_DIR / "_turns"


@dataclass
class Piece:
    """One synthesized turn: its audio, and where every character lands in it."""

    pcm: bytes
    text: str
    char_starts_ms: list[int]
    char_ends_ms: list[int]

    @property
    def duration_ms(self) -> int:
        samples = len(self.pcm) // (BYTES_PER_SAMPLE * CHANNELS)
        return round(samples * 1000 / SAMPLE_RATE)


def require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        sys.exit(f"{binary} is required. Install it with: brew install ffmpeg")
    return path


def api_key() -> str:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ELEVENLABS_API_KEY is missing. Add it to .env and re-run.\n"
            "  ELEVENLABS_API_KEY=sk_...\n"
            "  ELEVENLABS_MODEL=eleven_flash_v2_5"
        )
    return key


def list_voices(key: str) -> None:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{API}/voices", headers={"xi-api-key": key})
        resp.raise_for_status()
    for v in sorted(resp.json().get("voices", []), key=lambda x: x.get("name", "")):
        labels = v.get("labels") or {}
        meta = ", ".join(f"{k}={val}" for k, val in labels.items() if val)
        print(f"{v.get('name', ''):24} {v.get('voice_id', ''):28} {meta}")


def parse_turns(text: str) -> list[tuple[str, str]]:
    """Script file -> [(speaker, text)], with a silence marker where the agent mutes."""
    turns: list[tuple[str, str]] = []
    speaker, buf = None, []
    for line in text.splitlines():
        m = TURN_RE.match(line)
        if m:
            if speaker and buf:
                turns.append((speaker, " ".join(buf).strip()))
            speaker, buf = m.group(1), [m.group(2).strip()]
        elif speaker and line.strip():
            buf.append(line.strip())
    if speaker and buf:
        turns.append((speaker, " ".join(buf).strip()))

    expanded: list[tuple[str, str]] = []
    for who, spoken in turns:
        split = MUTE_SPLIT_RE.match(spoken) if who == "Marco" else None
        if split:
            expanded.append((who, split.group(1).strip()))
            expanded.append(("_silence", str(MUTE_GAP_SECONDS)))
            expanded.append((who, split.group(2).strip()))
        elif spoken:
            expanded.append((who, spoken))
    return expanded


def synthesize(
    client: httpx.Client,
    key: str,
    voice_id: str,
    text: str,
    previous_text: str | None,
    next_text: str | None,
) -> dict:
    """Call with-timestamps and return the raw ElevenLabs payload."""
    payload: dict = {
        "text": text,
        "model_id": MODEL,
        "voice_settings": {
            "stability": 0.42,
            "similarity_boost": 0.78,
            "style": 0.12,
            "use_speaker_boost": True,
            "speed": 1.02,
        },
    }
    if previous_text:
        payload["previous_text"] = previous_text[-400:]
    if next_text:
        payload["next_text"] = next_text[:400]

    url = f"{API}/text-to-speech/{voice_id}/with-timestamps"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    for attempt in range(5):
        resp = client.post(
            url, headers=headers, params={"output_format": OUTPUT_FORMAT},
            json=payload, timeout=180,
        )
        if resp.status_code == 429:
            wait = 2 ** attempt
            print(f"      rate-limited, retry in {wait}s")
            time.sleep(wait)
            continue
        if resp.status_code >= 400:
            raise RuntimeError(f"ElevenLabs {resp.status_code}: {resp.text[:400]}")
        return resp.json()
    raise RuntimeError("ElevenLabs kept returning 429.")


def decode_to_pcm(mp3: bytes) -> bytes:
    """mp3 -> raw mono PCM. Joining PCM is sample-exact; joining mp3 frames is not."""
    proc = subprocess.run(
        [
            require("ffmpeg"), "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0",
            "-f", "s16le", "-acodec", "pcm_s16le",
            "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "pipe:1",
        ],
        input=mp3, capture_output=True, check=True,
    )
    return proc.stdout


def encode_mp3(pcm: bytes, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            require("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), "-i", "pipe:0",
            "-codec:a", "libmp3lame", "-b:a", "128k", str(dest),
        ],
        input=pcm, check=True,
    )


FRAME_MS = 10
SILENCE_THRESHOLD = 300
# A run this long means speech is under way here, so a timestamp inside it is left
# where it is.
CONTINUES_RUN = 3
# A word is at least this long. Snapping targets only runs of this size, so a
# start never lands on a breath or a mouth click between sentences.
ONSET_RUN = 10
# A start is sitting in the previous word's sound if speech has already been
# going for LEAD_MS, stops within TAIL_MS, and a pause of MIN_PAUSE_MS follows.
LEAD_MS = 50
TAIL_MS = 120
MIN_PAUSE_MS = 180
# How far back a start may be pulled to reach the onset of the word it is inside.
BACKPULL_MS = 150
# However wrong a reading looks, never relocate a timestamp this far.
MAX_SNAP_MS = 1500


def audible_frames(pcm: bytes) -> list[bool]:
    samples = memoryview(pcm).cast("h")
    frame = max(int(SAMPLE_RATE * FRAME_MS / 1000), 1)
    return [
        any(abs(v) > SILENCE_THRESHOLD for v in samples[i: i + frame])
        for i in range(0, len(samples), frame)
    ]


def sound_bounds(pcm: bytes) -> tuple[int, int]:
    """Where the speech in one synthesized turn starts and stops.

    ElevenLabs pads every clip and charges the padding to the characters at each
    end: a clip whose voice only comes in after 800 ms still reports its first
    character as starting at 0. This is measured per clip rather than across the
    finished call, so the decay tail of the previous turn cannot anchor it.
    """
    frames = audible_frames(pcm)
    total_ms = len(frames) * FRAME_MS
    loud = [i for i, on in enumerate(frames) if on]
    if not loud:
        return 0, total_ms
    return loud[0] * FRAME_MS, (loud[-1] + 1) * FRAME_MS


class Silence:
    """Where the finished call is quiet, used to trim pauses off character times.

    A hesitation rendered mid-turn - the beat before "Twenty dollars" - gets
    charged to the T, and a start can also land in the decay of the word before
    it. Either way the fix is to push the start to where the voice really comes
    in. Three things stop that from overcorrecting:

      * A start inside speech that keeps going is left alone.
      * A start is only treated as someone else's tail when speech was already
        running before it, stops right after it, and a real pause follows. A
        short word of one's own does not meet that description.
      * Nothing moves further than MAX_SNAP_MS, so a bad reading can nudge a
        timestamp but never relocate it to a different sentence.
    """

    def __init__(self, pcm: bytes) -> None:
        audible = audible_frames(pcm)
        count = len(audible)
        self._count = count

        speech_from = [0] * (count + 1)
        silence_from = [0] * (count + 1)
        for i in range(count - 1, -1, -1):
            speech_from[i] = speech_from[i + 1] + 1 if audible[i] else 0
            silence_from[i] = 0 if audible[i] else silence_from[i + 1] + 1
        self._speech_from = speech_from
        self._silence_from = silence_from

        self._run_start = [0] * (count + 1)
        for i in range(count):
            self._run_start[i] = (
                self._run_start[i - 1] if audible[i] and i else i
            )

        self._next = [count] * (count + 1)
        for i in range(count - 1, -1, -1):
            self._next[i] = i if speech_from[i] >= ONSET_RUN else self._next[i + 1]
        self._prev = [-1] * (count + 1)
        for i in range(count):
            self._prev[i + 1] = i if audible[i] else self._prev[i]

    def _frame(self, ms: int) -> int:
        return min(max(ms // FRAME_MS, 0), self._count)

    def _is_someone_elses_tail(self, frame: int) -> bool:
        remaining = self._speech_from[frame]
        if not remaining or remaining * FRAME_MS > TAIL_MS:
            return False
        if (frame - self._run_start[frame]) * FRAME_MS < LEAD_MS:
            return False
        # Measure the pause to the next real onset, not to the next sample above
        # the threshold: a breath between sentences should not count as speech.
        stops = frame + remaining
        resumes = self._next[stops]
        return (resumes < self._count
                and (resumes - stops) * FRAME_MS >= MIN_PAUSE_MS)

    def next_sound(self, ms: int) -> int:
        frame = self._frame(ms)
        tail = self._is_someone_elses_tail(frame)
        if self._speech_from[frame] >= CONTINUES_RUN and not tail:
            return self._start_of_word(frame, ms)

        # A tail is still speech, so the search has to start past the end of it.
        target = self._next[frame + self._speech_from[frame] if tail else frame]
        if target < self._count and target * FRAME_MS - ms <= MAX_SNAP_MS:
            return max(ms, target * FRAME_MS)

        # Nothing is said for a long time after this, so the words were not spoken
        # later - they were the tail end of what came before. ElevenLabs charges a
        # long rendered pause to the characters that follow it, which is how a "K?"
        # at the end of a sentence ends up reported in the middle of the silence.
        return self._end_of_previous_sound(frame) if not tail else ms

    def _start_of_word(self, frame: int, ms: int) -> int:
        """Pull a start back to the word's onset when it landed just inside it.

        A soft consonant gets reported a few tens of ms late. That only needs
        correcting where the word follows a real pause; inside continuous speech
        there is no onset to find and the reported time is the best there is.
        """
        run_start = self._run_start[frame]
        if (frame - run_start) * FRAME_MS > BACKPULL_MS:
            return ms
        before = self._prev[run_start]
        if before >= 0 and (run_start - 1 - before) * FRAME_MS < MIN_PAUSE_MS:
            return ms
        return min(ms, run_start * FRAME_MS)

    def _end_of_previous_sound(self, frame: int) -> int:
        previous = self._prev[frame]
        return frame * FRAME_MS if previous < 0 else previous * FRAME_MS

    def previous_sound(self, ms: int) -> int:
        frame = self._frame(ms)
        # An end sitting on the first moments of a run that follows a real pause is
        # the start of the *next* thing said, not the end of this one.
        if (self._speech_from[frame]
                and (frame - self._run_start[frame]) * FRAME_MS <= LEAD_MS):
            run_start = self._run_start[frame]
            before = self._prev[run_start]
            if before >= 0 and (run_start - 1 - before) * FRAME_MS >= MIN_PAUSE_MS:
                return (before + 1) * FRAME_MS

        previous = self._prev[frame]
        return ms if previous < 0 else min(ms, (previous + 1) * FRAME_MS)


def build_piece(payload: dict, text: str) -> Piece:
    alignment = payload.get("alignment") or payload.get("normalized_alignment")
    if not alignment:
        raise RuntimeError("ElevenLabs returned no alignment; cannot stamp timings.")

    characters = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    if not (len(characters) == len(starts) == len(ends)):
        raise RuntimeError("Alignment arrays disagree in length.")

    aligned_text = "".join(characters)
    if aligned_text != text:
        # The alignment must describe the text we sent, or every downstream
        # timestamp is quietly wrong. Fail loudly instead.
        raise RuntimeError(
            "Alignment text does not match the request text.\n"
            f"  sent:    {text[:80]!r}\n"
            f"  aligned: {aligned_text[:80]!r}"
        )

    pcm = decode_to_pcm(base64.b64decode(payload["audio_base64"]))
    floor, ceiling = sound_bounds(pcm)
    clamp = lambda ms: min(max(ms, floor), ceiling)  # noqa: E731
    return Piece(
        pcm=pcm,
        text=text,
        char_starts_ms=[clamp(round(s * 1000)) for s in starts],
        char_ends_ms=[clamp(round(e * 1000)) for e in ends],
    )


SENTENCE_END = ".?!"


def pull_orphans(chars: list[str], starts: list[int], ends: list[int]) -> None:
    """Keep a character with the letter it follows.

    A long pause gets charged to whatever comes after it, which is how the "?" of
    a "K?" ending one sentence is reported three seconds later, at the moment the
    next sentence begins. A character cannot be spoken that long after the letter
    before it unless a word or a sentence ended in between.
    """
    for i in range(1, len(chars)):
        previous = chars[i - 1]
        if previous.isspace() or previous in SENTENCE_END:
            continue
        if starts[i] - ends[i - 1] < MIN_PAUSE_MS:
            continue
        duration = ends[i] - starts[i]
        starts[i] = ends[i - 1]
        ends[i] = starts[i] + duration


def cached_payload(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def render_lead(
    lead_id: str, key: str, voices: dict[str, str], force: bool, resynthesize: bool
) -> None:
    script_path = SCRIPTS / f"{lead_id}_elevenlabs.txt"
    if not script_path.exists():
        sys.exit(f"Missing script: {script_path}")
    turns = parse_turns(script_path.read_text(encoding="utf-8"))
    if not turns:
        sys.exit(f"No Helen/Marco turns in {script_path}")

    dest_audio = AUDIO_DIR / f"{lead_id}.mp3"
    dest_timings = AUDIO_DIR / f"{lead_id}.timings.json"
    if dest_audio.exists() and dest_timings.exists() and not force:
        print(f"{lead_id}: already built, skipping (use --force to rebuild)")
        return

    print(f"{lead_id}: {len(turns)} turns  model={MODEL}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    spoken = [(w, t) for w, t in turns if w != "_silence"]
    pcm_parts: list[bytes] = []
    chars: list[str] = []
    starts_ms: list[int] = []
    ends_ms: list[int] = []
    offset_ms = 0

    with httpx.Client() as client:
        spoken_index = 0
        for i, (who, text) in enumerate(turns, start=1):
            if who == "_silence":
                gap_samples = int(float(text) * SAMPLE_RATE)
                pcm_parts.append(b"\x00" * (gap_samples * BYTES_PER_SAMPLE * CHANNELS))
                offset_ms += round(gap_samples * 1000 / SAMPLE_RATE)
                print(f"  {i:03d} silence {text}s  -> {offset_ms / 1000:7.2f}s")
                continue

            cache = CACHE_DIR / f"{lead_id}_{i:03d}_{who}.json"
            payload = None if resynthesize else cached_payload(cache)
            if payload is None:
                payload = synthesize(
                    client, key, voices[who], text,
                    spoken[spoken_index - 1][1] if spoken_index else None,
                    spoken[spoken_index + 1][1] if spoken_index + 1 < len(spoken) else None,
                )
                cache.write_text(json.dumps(payload), encoding="utf-8")
                time.sleep(0.08)

            piece = build_piece(payload, text)
            pcm_parts.append(piece.pcm)
            chars.extend(piece.text)
            starts_ms.extend(offset_ms + t for t in piece.char_starts_ms)
            ends_ms.extend(offset_ms + t for t in piece.char_ends_ms)
            offset_ms += piece.duration_ms
            print(f"  {i:03d} {who:6} {len(text):5} chars -> {offset_ms / 1000:7.2f}s")
            spoken_index += 1

    pcm = b"".join(pcm_parts)
    encode_mp3(pcm, dest_audio)
    duration_ms = round(len(pcm) // (BYTES_PER_SAMPLE * CHANNELS) * 1000 / SAMPLE_RATE)

    silence = Silence(pcm)
    starts_ms = [silence.next_sound(t) for t in starts_ms]
    ends_ms = [max(silence.previous_sound(e), s)
               for s, e in zip(starts_ms, ends_ms, strict=True)]
    pull_orphans(chars, starts_ms, ends_ms)

    dest_timings.write_text(
        json.dumps(
            {
                "lead_id": lead_id,
                "audio": dest_audio.name,
                "model": MODEL,
                "source": "elevenlabs_with_timestamps",
                "sample_rate": SAMPLE_RATE,
                "duration_ms": duration_ms,
                "chars": "".join(chars),
                "starts_ms": starts_ms,
                "ends_ms": ends_ms,
            }
        ),
        encoding="utf-8",
    )
    print(
        f"{lead_id}: wrote {dest_audio.name} "
        f"({duration_ms / 1000:.1f}s, {dest_audio.stat().st_size // 1024} KB) "
        f"and {dest_timings.name} ({len(chars)} timed characters)"
    )


def copy_reuses(force: bool) -> None:
    """3613793/3613794 are the same call as 3613792, so they share its recording."""
    for src_id, dests in REUSE.items():
        src_audio = AUDIO_DIR / f"{src_id}.mp3"
        src_timings = AUDIO_DIR / f"{src_id}.timings.json"
        if not (src_audio.exists() and src_timings.exists()):
            continue
        for dest_id in dests:
            dest_audio = AUDIO_DIR / f"{dest_id}.mp3"
            dest_timings = AUDIO_DIR / f"{dest_id}.timings.json"
            if dest_audio.exists() and dest_timings.exists() and not force:
                continue
            shutil.copyfile(src_audio, dest_audio)
            manifest = json.loads(src_timings.read_text(encoding="utf-8"))
            manifest["lead_id"] = dest_id
            manifest["audio"] = dest_audio.name
            manifest["copied_from"] = src_id
            dest_timings.write_text(json.dumps(manifest), encoding="utf-8")
            print(f"{dest_id}: copied from {src_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead", help="one lead id, otherwise all unique calls")
    parser.add_argument("--list-voices", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="rebuild the mp3 and timings from the cached turns")
    parser.add_argument("--resynthesize", action="store_true",
                        help="call ElevenLabs again instead of reusing cached turns")
    args = parser.parse_args()
    force = args.force or args.resynthesize

    key = api_key()
    if args.list_voices:
        list_voices(key)
        return

    require("ffmpeg")
    voices = {
        "Helen": os.getenv("ELEVENLABS_HELEN_VOICE_ID", DEFAULT_HELEN),
        "Marco": os.getenv("ELEVENLABS_MARCO_VOICE_ID", DEFAULT_MARCO),
    }

    leads = (args.lead,) if args.lead else UNIQUE_LEADS
    for lead_id in leads:
        if lead_id not in UNIQUE_LEADS and lead_id not in ALL_REUSED:
            sys.exit(f"Unknown lead {lead_id}. Try: {', '.join(UNIQUE_LEADS)}")

    generate = [lid for lid in leads if lid in UNIQUE_LEADS]
    if any(lid in ALL_REUSED for lid in leads):
        generate = list(dict.fromkeys([*generate, "3613792"]))

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for lead_id in generate:
        render_lead(lead_id, key, voices, force, args.resynthesize)
    copy_reuses(force)
    print("\nDone. Now re-seed so the transcript carries these timings:")
    print("  python -m app.seed.run --drop")


if __name__ == "__main__":
    main()
