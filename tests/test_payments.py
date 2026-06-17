"""Tests for the Stripe donation flow."""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Donate page
# ---------------------------------------------------------------------------

async def test_donate_page_loads(client):
    resp = await client.get("/donate")
    assert resp.status_code == 200
    assert b"donate" in resp.content.lower() or b"support" in resp.content.lower()


async def test_donate_page_unauthenticated(client):
    """Donate page is public — no auth required."""
    resp = await client.get("/donate")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Checkout validation
# ---------------------------------------------------------------------------

async def test_checkout_rejects_zero_amount(client):
    resp = await client.post("/donate/checkout", data={"amount": "0"})
    assert resp.status_code in (302, 303, 422, 400)


async def test_checkout_rejects_negative_amount(client):
    resp = await client.post("/donate/checkout", data={"amount": "-5"})
    assert resp.status_code in (302, 303, 422, 400)


async def test_checkout_rejects_excessive_amount(client):
    resp = await client.post("/donate/checkout", data={"amount": "100000"})
    assert resp.status_code in (302, 303, 422, 400)


async def test_checkout_rejects_non_numeric(client):
    resp = await client.post("/donate/checkout", data={"amount": "abc"})
    assert resp.status_code in (302, 303, 422, 400)


# ---------------------------------------------------------------------------
# Checkout with mocked Stripe
# ---------------------------------------------------------------------------

async def test_checkout_valid_amount_redirects_to_stripe(client):
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test-session"

    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = mock_session

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        resp = await client.post("/donate/checkout", data={"amount": "10"})

    assert resp.status_code in (302, 303)
    assert "stripe.com" in resp.headers.get("location", "")


async def test_checkout_preset_amount_5(client):
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/5"
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = mock_session

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        resp = await client.post("/donate/checkout", data={"amount": "5"})

    assert resp.status_code in (302, 303)


async def test_checkout_preset_amount_25(client):
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay/25"
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = mock_session

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        resp = await client.post("/donate/checkout", data={"amount": "25"})

    assert resp.status_code in (302, 303)


async def test_checkout_creates_session_with_correct_amount(client):
    """Verify the Stripe session is created with the right unit amount (cents)."""
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/pay"
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.create.return_value = mock_session

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        await client.post("/donate/checkout", data={"amount": "15"})

    create_kwargs = mock_stripe.checkout.Session.create.call_args
    assert create_kwargs is not None
    # Price data unit_amount should be 1500 (€15.00 in cents)
    price_data = create_kwargs.kwargs.get("line_items", [{}])[0].get("price_data", {})
    assert price_data.get("unit_amount") == 1500


# ---------------------------------------------------------------------------
# Success page
# ---------------------------------------------------------------------------

async def test_success_page_without_session_id(client):
    resp = await client.get("/donate/success")
    assert resp.status_code == 200


async def test_success_page_with_invalid_session_id(client):
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.retrieve.side_effect = Exception("No such session")

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        resp = await client.get("/donate/success?session_id=cs_test_invalid")

    assert resp.status_code == 200


async def test_success_page_with_valid_session(client):
    mock_session = MagicMock()
    mock_session.payment_status = "paid"
    mock_session.amount_total = 1000  # €10.00

    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.retrieve.return_value = mock_session

    with patch("backend.payments.routes._stripe", return_value=mock_stripe):
        resp = await client.get("/donate/success?session_id=cs_test_valid")

    assert resp.status_code == 200
    assert b"10" in resp.content  # amount shown on page
