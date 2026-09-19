"""Spoken-number parsing. These are the cases the supplied call actually contains."""
import pytest

from app.services.extraction import normalizer as nz


@pytest.mark.parametrize("text,expected", [
    ("only forty two dollars and ninety", 42.90),
    ("only forty two dollars and ninetyMhmm", 42.90),   # glued to the next word
    ("Seventy two dollars and ninety. That's the regular price.", 72.90),
    ("total minimum cost of three hundred seventeen dollars", 317.0),
    ("development fee, right, of two hundred seventy five dollars", 275.0),
    ("Sixty five dollars for how many MBPS?", 65.0),
    ("$42.90 per month", 42.90),
])
def test_money(text, expected):
    assert nz.find_money(text)[0][0] == expected


@pytest.mark.parametrize("text,expected", [
    ("I can give you a twenty five MBBS", [25.0]),
    ("provides twenty five Mbps typical in download speed and eight point five Mbps "
     "typical in the upload speed", [25.0, 8.5]),
])
def test_speeds(text, expected):
    assert [v for v, _ in nz.find_speeds(text)] == expected


def test_speed_is_not_a_price():
    """'Sixty five dollars for how many MBPS' must not yield a 65 Mbps reading."""
    assert nz.find_speeds("Sixty five dollars for how many MBPS?") == []


def test_day_range():
    assert nz.find_day_range("delivered to you within three to five business days")[:2] == (3, 5)


def test_months():
    assert nz.find_months("only per month for the first six months")[0][0] == 6


def test_squash_absorbs_run_together_words():
    a = nz.squash("recorded for quality assuranceand, training purposes")
    b = nz.squash("recorded for quality assurance and training purposes")
    assert a == b
