"""Latest-confirmed-value resolution, the delivery-address case."""
from app.services.extraction.facts import FactStore, Observation
from app.services.extraction.state_tracker import resolve


def _obs(value, index, confidence=0.9):
    return Observation(key="delivery_address", value=value, confidence=confidence,
                       segment_id=f"seg_{index}", segment_index=index,
                       text=str(value), timestamp="00:00")


def test_latest_assertion_wins():
    store = FactStore()
    store.add(_obs("SERVICE_ADDRESS", 10))
    store.add(_obs("DELIVERY_ADDRESS", 40))
    fact = resolve(store, "delivery_address")
    assert fact.value == "DELIVERY_ADDRESS"
    assert fact.conflicted


def test_conflict_lowers_confidence_below_threshold():
    store = FactStore()
    store.add(_obs("SERVICE_ADDRESS", 10))
    store.add(_obs("DELIVERY_ADDRESS", 40))
    assert resolve(store, "delivery_address").confidence < 0.8


def test_agreement_raises_confidence():
    store = FactStore()
    for i in (1, 2, 3):
        store.add(_obs("DELIVERY_ADDRESS", i, confidence=0.85))
    fact = resolve(store, "delivery_address")
    assert not fact.conflicted and fact.confidence > 0.85


def test_absent_fact_is_not_a_value():
    assert not resolve(FactStore(), "delivery_address").found
