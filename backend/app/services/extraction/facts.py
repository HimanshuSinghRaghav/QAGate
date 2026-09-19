"""Transcript -> candidate facts, each one carrying its own evidence.

An Observation is a value the call *claims*, bound to the segment and timestamp it
came from. Nothing here decides PASS or FAIL. Checks do that, by comparing these
observations to CRM fields and the rate card.
"""
import re
from dataclasses import asdict, dataclass, field

from app.models import Segment
from app.services.extraction import normalizer as nz

PLACEHOLDER_RE = re.compile(r"\[([A-Z_]+)\]")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}")
AU_MOBILE_RE = re.compile(r"\b0[45]\d{2}\s?\d{3}\s?\d{3}\b")

# CRM keys that, when spoken, become facts. delivery_address is stateful and handled
# separately because "same address" means the service address, not a new string.
CRM_FACT_KEYS = (
    "email", "phone", "dob", "customer_full_name", "customer_name",
    "service_address", "account_number", "otp_code", "reference_number",
)


def _crm_mentions(crm: dict) -> list[tuple[str, str]]:
    """Prefer longer CRM values first so 'Helen Carter' wins over 'Helen'."""
    items = []
    for key in CRM_FACT_KEYS:
        value = crm.get(key)
        if isinstance(value, str) and len(value.strip()) >= 3:
            items.append((key, value.strip()))
    return sorted(items, key=lambda kv: -len(kv[1]))


def _contains(text: str, value: str) -> bool:
    return value.lower() in text.lower()

# Keyword -> fact key, scored against the text immediately around a money mention.
MONEY_CONTEXT = {
    "intro_price": ("first six months", "for the first", "offer ongoing", "only per month",
                    "promotion", "you will get this plan as"),
    # Keywords must be specific. "and then" or a bare "regular" would swallow any
    # amount that happens to follow a sentence connector.
    "regular_price": ("regular price", "original plan cost", "goes up to", "go up to",
                      "ongoing price", "after the first",
                      # "...for the first six months and then seventy two ninety":
                      # the price after the intro term, cued by the connector itself.
                      "months and then", "and then it", "reverts to"),
    "total_minimum_cost": ("total minimum cost", "minimum cost", "still showing that minimum"),
    "development_fee": ("development fee",),
    "current_price": ("are you paying", "reduced it", "they reduced", "how much are you"),
}

SPEED_CONTEXT = {
    "download_mbps": ("download", "typical in download"),
    "upload_mbps": ("upload", "typical in the upload"),
}

CONTEXT_WINDOW = 140


@dataclass
class Observation:
    key: str
    value: object
    unit: str | None = None
    confidence: float = 0.9
    segment_id: str = ""
    segment_index: int = 0
    speaker: str = "unknown"
    speaker_confidence: float = 0.5
    text: str = ""
    start_ms: int = 0
    end_ms: int = 0
    timing_source: str = "estimated"
    timestamp: str = "00:00"
    note: str = ""

    def to_evidence(self) -> dict:
        d = asdict(self)
        d.pop("key", None)
        return d


@dataclass
class FactStore:
    observations: dict[str, list[Observation]] = field(default_factory=dict)

    def add(self, obs: Observation) -> None:
        self.observations.setdefault(obs.key, []).append(obs)

    def get(self, key: str) -> list[Observation]:
        return self.observations.get(key, [])

    def keys(self) -> list[str]:
        return sorted(self.observations)


def _classify(text: str, pos: int, mapping: dict[str, tuple[str, ...]],
              direction: str = "both") -> tuple[str | None, float]:
    """Pick the fact key whose keyword sits closest to this mention.

    `direction` matters. Speeds are qualified *after* the number - "twenty five Mbps
    typical in download speed and eight point five Mbps typical in the upload speed" -
    so searching backwards would label the upload figure as download. Money is
    qualified on either side, so it stays bidirectional.
    """
    lowered = text.lower()
    window_start = pos if direction == "after" else max(0, pos - CONTEXT_WINDOW)
    window_end = pos if direction == "before" else pos + CONTEXT_WINDOW
    window = lowered[window_start: window_end]
    best_key, best_distance = None, 10**6
    for key, keywords in mapping.items():
        for kw in keywords:
            idx = window.find(kw)
            if idx == -1:
                continue
            distance = abs((window_start + idx) - pos)
            if distance < best_distance:
                best_key, best_distance = key, distance
    if best_key is None:
        return None, 0.0
    confidence = 0.95 if best_distance <= 40 else 0.80 if best_distance <= 90 else 0.65
    return best_key, confidence


def _base(seg: Segment, **kwargs) -> dict:
    return dict(
        segment_id=seg.id,
        segment_index=seg.index,
        speaker=seg.speaker,
        speaker_confidence=float(seg.speaker_confidence),
        text=seg.redacted_text,
        start_ms=seg.start_ms,
        end_ms=seg.end_ms,
        timing_source=seg.timing_source,
        timestamp=seg.timestamp_label,
        **kwargs,
    )


def extract(segments: list[Segment], crm: dict | None = None) -> FactStore:
    """Pull observations out of the transcript.

    `crm` is optional. When present, spoken mentions of CRM values (the mock
    identity, or a real record) are captured as facts so placeholder tags are not
    required. Tags such as [EMAIL] still work if the official sanitised file is
    loaded unchanged.
    """
    crm = crm or {}
    service_addr = str(crm.get("service_address") or "").strip()
    delivery_addr = str(crm.get("delivery_address") or "").strip()
    crm_mentions = _crm_mentions(crm)

    store = FactStore()
    joined = [
        (s, s.raw_text,
         segments[i - 1].raw_text if i else "",
         segments[i + 1].raw_text if i + 1 < len(segments) else "")
        for i, s in enumerate(segments)
    ]

    for seg, text, prev_text, next_text in joined:
        lowered = text.lower()
        # Neighbour text widens context for amounts stated in one sentence and
        # labelled in the next: "Seventy two dollars and ninety." / "That's the regular
        # price." - or "only forty two dollars and ninety" / "For the first six months."
        widened = f"{prev_text} {text} {next_text}"
        offset = len(prev_text) + 1

        # ---- money ----
        for amount, pos in nz.find_money(text):
            key, conf = _classify(text, pos, MONEY_CONTEXT)
            if key is None:
                key, conf = _classify(widened, pos + offset, MONEY_CONTEXT)
                conf = max(conf - 0.15, 0.0) if key else 0.0
            if key is None:
                key, conf = "unclassified_amount", 0.30
            store.add(Observation(key=key, value=amount, unit="AUD", confidence=conf,
                                  **_base(seg)))

        # ---- speeds ----
        for value, pos in nz.find_speeds(text):
            key, conf = _classify(text, pos, SPEED_CONTEXT, direction="after")
            if key is None:
                key, conf = "quoted_speed_mbps", 0.60
            store.add(Observation(key=key, value=value, unit="Mbps", confidence=conf,
                                  **_base(seg)))

        # ---- intro term ----
        if "first" in lowered:
            for months, _pos in nz.find_months(text):
                store.add(Observation(key="intro_term_months", value=months, unit="months",
                                      confidence=0.9, **_base(seg)))

        # ---- contract term ----
        if "month to month" in lowered:
            store.add(Observation(key="contract_term", value="month_to_month",
                                  confidence=0.95, **_base(seg)))
        elif re.search(r"\bone to one\s+contract\b", lowered):
            # Near-certain ASR mangling of "month to month contract". Flagged, not assumed.
            store.add(Observation(
                key="contract_term", value="one_to_one", confidence=0.40,
                note="Likely ASR error for 'month to month contract'; needs adjudication.",
                **_base(seg)))
        elif re.search(r"\b(no lock in|not locked in|no contract)\b", lowered):
            store.add(Observation(key="contract_term", value="no_lock_in",
                                  confidence=0.85, **_base(seg)))

        # ---- modem model ----
        if "netcom" in lowered:
            m = re.search(r"netcom\s+([a-z\s\.]{0,8}?)\s*(forty|40)\b", lowered)
            if m:
                letters = re.sub(r"[^a-z]", "", m.group(1))
                if letters in ("cf", "c f"):
                    store.add(Observation(key="modem_model", value="CF40", confidence=0.95,
                                          **_base(seg)))
                else:
                    store.add(Observation(
                        key="modem_model", value=f"{letters.upper() or '??'}40",
                        confidence=0.45,
                        note=f"Model letters transcribed as '{letters}'; "
                             f"same product family and number, spelling uncertain.",
                        **_base(seg)))

        # ---- modem upfront cost ----
        if re.search(r"(zero dollar|\$\s*0\b|hundred percent free|free modem|no extra cost)", lowered):
            store.add(Observation(key="modem_upfront_cost", value=0.0, unit="AUD",
                                  confidence=0.9, **_base(seg)))

        # ---- delivery timeframe ----
        day_range = nz.find_day_range(text)
        if day_range:
            lo, hi, _ = day_range
            store.add(Observation(key="delivery_days", value=[lo, hi], unit="business_days",
                                  confidence=0.95, **_base(seg)))

        # ---- development fee applicability ----
        if "development fee" in lowered or "not applicable" in lowered:
            if re.search(r"(not applicable|will not pay|don't have to worry|"
                         r"not be charged|already an nbn ready|already nbn ready)", lowered):
                store.add(Observation(key="development_fee_waived_claim", value=True,
                                      confidence=0.85, **_base(seg)))

        # ---- recording disclaimer / mute compliance ----
        if "mute the recording" in lowered:
            store.add(Observation(key="recording_muted", value=True, confidence=0.95,
                                  **_base(seg)))
        if "recording is already resumed" in lowered or "recording resumed" in lowered:
            store.add(Observation(key="recording_resumed", value=True, confidence=0.95,
                                  **_base(seg)))
        if re.search(r"(credit card or debit card|preferred payment method|card details)", lowered):
            store.add(Observation(key="payment_collection_started", value=True,
                                  confidence=0.9, **_base(seg)))

        # ---- delivery address state ----
        # Latest-asserted-value: "same address" means the service address; a later
        # spoken delivery address is a correction. Tags still work if unfilled.
        spoken_delivery = (
            "[DELIVERY_ADDRESS]" in text
            or (bool(delivery_addr) and _contains(text, delivery_addr)
                and (not service_addr or delivery_addr.lower() != service_addr.lower()
                     or "deliver" in f"{prev_text} {text} {next_text}".lower()))
        )
        if spoken_delivery and not re.search(r"\bsame address\b", lowered):
            value = delivery_addr if delivery_addr and _contains(text, delivery_addr) \
                else "DELIVERY_ADDRESS"
            store.add(Observation(key="delivery_address", value=value,
                                  confidence=0.9, **_base(seg)))
        elif re.search(r"\bsame address\b", lowered):
            in_delivery_context = bool(
                re.search(r"deliver", f"{prev_text} {text} {next_text}".lower()))
            value = service_addr or "SERVICE_ADDRESS"
            store.add(Observation(
                key="delivery_address", value=value,
                confidence=0.85 if in_delivery_context else 0.55,
                note="Confirmed as the same as the service address."
                     if in_delivery_context else "Mentioned in passing.",
                **_base(seg)))

        # ---- identity: leftover [TAGS] and spoken CRM values ----
        window = f"{prev_text} {text} {next_text}".lower()
        verified = bool(
            re.search(r"(verify|confirm|correct|what is|can you please|"
                      r"date of birth|email address|mobile number)", window)
            or prev_text.strip().endswith("?")
            or next_text.strip().lower().startswith(("right?", "correct?",
                                                     "am i correct"))
        )
        note = "stated in a verification exchange" if verified else ""
        conf = 0.9 if verified else 0.6

        for tag in PLACEHOLDER_RE.findall(text):
            key = {
                "EMAIL": "email", "PHONE": "phone", "DOB": "dob",
                "CUSTOMER_FULL_NAME": "customer_full_name",
                "CUSTOMER_NAME": "customer_name",
                "SERVICE_ADDRESS": "service_address",
                "ACCOUNT_NUMBER": "account_number",
                "OTP_CODE": "otp_code",
                "REFERENCE_NUMBER": "reference_number",
            }.get(tag)
            if key:
                store.add(Observation(key=key, value=f"[{tag}]",
                                      confidence=conf, note=note, **_base(seg)))

        for key, value in crm_mentions:
            if _contains(text, value):
                store.add(Observation(key=key, value=value,
                                      confidence=conf, note=note, **_base(seg)))

        for match in EMAIL_RE.findall(text):
            if match.startswith("["):
                continue
            store.add(Observation(key="email", value=match, confidence=conf,
                                  note=note, **_base(seg)))
        for match in AU_MOBILE_RE.findall(text):
            store.add(Observation(key="phone", value=match, confidence=conf,
                                  note=note, **_base(seg)))

        # ---- current provider ----
        for provider in ("iprimus", "i primus"):
            if provider in lowered:
                store.add(Observation(key="current_provider", value="iPRIMUS",
                                      confidence=0.9, **_base(seg)))
                break

    return store
