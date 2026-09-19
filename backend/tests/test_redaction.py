from app.services.transcript.redaction import redact


def test_card_number_is_removed_and_flagged():
    report = redact("My card number is 4111 1111 1111 1111 thanks")
    assert "4111" not in report.text
    assert "[REDACTED_CARD]" in report.text
    assert report.card_data_found


def test_non_card_digits_survive():
    report = redact("The reference is 4111 1111 1111 1112")  # fails Luhn
    assert not report.card_data_found


def test_demo_email_is_not_stripped():
    report = redact("Your email is helen.carter@gmail.com")
    assert "helen.carter@gmail.com" in report.text
