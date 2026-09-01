import razorpay

from app.core.config import settings

_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_rupees: float, receipt: str) -> dict:
    """
    Creates a Razorpay order. Amount must be in paise (smallest unit),
    so we multiply by 100 here — this is the one place that conversion
    happens, keep it that way to avoid paise/rupee bugs elsewhere.
    """
    amount_paise = int(round(amount_rupees * 100))
    order = _client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,  # auto-capture on success
    })
    return order


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Used on Day 3 — verifies the webhook actually came from Razorpay."""
    try:
        _client.utility.verify_webhook_signature(
            body.decode("utf-8"), signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
