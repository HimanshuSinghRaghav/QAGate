"""Mock identity used to un-redact the supplied transcript for the demo.

The organiser file hides names, contact details and addresses behind tags such as
[EMAIL] and [SERVICE_ADDRESS]. Scoring still works on tags, but a demo is easier
to follow when the CRM row and the transcript say the same invented person.

Nothing here is a real customer. Card numbers stay out; payment collection is
still muted on the call.
"""

CUSTOMER_NAME = "Helen"
CUSTOMER_FULL_NAME = "Helen Carter"
EMAIL = "helen.carter@gmail.com"
PHONE = "0412 887 364"
DOB = "12 March 1978"
SERVICE_ADDRESS = "14 Harbour Street, Parramatta NSW 2150"
DELIVERY_ADDRESS = "Unit 3, 22 River Road, Parramatta NSW 2150"
STREET_NAME = "Harbour Street"
RESIDENTIAL_COMPLEX = "Harbour Gardens"
ACCOUNT_NUMBER = "84729103"
OTP_CODE = "448291"
REFERENCE_NUMBER = "APP-3613790"
AGENT_NAME = "Marco Santos"
PROVIDER_A = "FibreLink"
UNCLEAR_NAME = "Ellen"

# Longer tags first so CUSTOMER_FULL_NAME is not eaten by CUSTOMER_NAME.
PLACEHOLDERS: dict[str, str] = {
    "CUSTOMER_FULL_NAME": CUSTOMER_FULL_NAME,
    "CUSTOMER_NAME": CUSTOMER_NAME,
    "SERVICE_ADDRESS": SERVICE_ADDRESS,
    "DELIVERY_ADDRESS": DELIVERY_ADDRESS,
    "RESIDENTIAL_COMPLEX": RESIDENTIAL_COMPLEX,
    "REFERENCE_NUMBER": REFERENCE_NUMBER,
    "ACCOUNT_NUMBER": ACCOUNT_NUMBER,
    "STREET_NAME": STREET_NAME,
    "UNCLEAR_NAME": UNCLEAR_NAME,
    "AGENT_NAME": AGENT_NAME,
    "PROVIDER_A": PROVIDER_A,
    "OTP_CODE": OTP_CODE,
    "EMAIL": EMAIL,
    "PHONE": PHONE,
    "DOB": DOB,
}


def fill(text: str) -> str:
    """Replace [TAG] placeholders with the mock identity, longest tag first."""
    filled = text
    for tag, value in sorted(PLACEHOLDERS.items(), key=lambda item: -len(item[0])):
        filled = filled.replace(f"[{tag}]", value)
    return filled


CRM_FIELDS = {
    "customer_name": CUSTOMER_NAME,
    "customer_full_name": CUSTOMER_FULL_NAME,
    "email": EMAIL,
    "phone": PHONE,
    "dob": DOB,
    "service_address": SERVICE_ADDRESS,
    "current_provider": "iPRIMUS",
    "account_number": ACCOUNT_NUMBER,
    "otp_code": OTP_CODE,
    "reference_number": REFERENCE_NUMBER,
    "development_fee_applicable": False,
}
