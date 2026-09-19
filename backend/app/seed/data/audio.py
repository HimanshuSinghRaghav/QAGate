"""Demo recordings produced by scripts/generate_demo_audio.py.

The generator writes, next to each mp3, the start and end time of every character
it synthesized. Loading that manifest is what lets the seeded transcript carry real
audio timings instead of a words-per-second estimate.

No manifest, no problem: ingestion falls back to estimated timings and says so.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from app.services.transcript.timing import chars_to_tokens

AUDIO_DIR = Path(__file__).resolve().parents[3] / "demo" / "audio"


@dataclass
class Recording:
    lead_id: str
    path: Path
    duration_ms: int
    tokens: list[dict]

    @property
    def duration_seconds(self) -> int:
        return round(self.duration_ms / 1000)

    @property
    def url(self) -> str:
        """Served by the web app at /api/audio/{lead_id}."""
        return f"/api/audio/{self.lead_id}"


def recording_for(lead_id: str) -> Recording | None:
    manifest = AUDIO_DIR / f"{lead_id}.timings.json"
    audio = AUDIO_DIR / f"{lead_id}.mp3"
    if not (manifest.exists() and audio.exists()):
        return None

    data = json.loads(manifest.read_text(encoding="utf-8"))
    return Recording(
        lead_id=lead_id,
        path=audio,
        duration_ms=int(data["duration_ms"]),
        tokens=chars_to_tokens(data["chars"], data["starts_ms"], data["ends_ms"]),
    )
