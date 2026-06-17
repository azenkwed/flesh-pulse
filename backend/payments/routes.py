"""Stripe donation checkout routes."""
import os

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_optional_user
from backend.database.db import get_db
from backend.routes import CATEGORIES, _last_updated, templates

router = APIRouter()

_AMOUNTS = [5, 10, 25, 50]  # EUR preset options


def _stripe():
    import stripe
    key = os.getenv("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not set")
    stripe.api_key = key
    return stripe


@router.get("/donate", response_class=HTMLResponse)
async def donate_page(
    request: Request,
    cancelled: bool = False,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_optional_user(request, db)
    return templates.TemplateResponse("donate.html", {
        "request": request,
        "categories": CATEGORIES,
        "current_user": current_user,
        "last_updated": _last_updated(),
        "amounts": _AMOUNTS,
        "cancelled": cancelled,
    })


@router.post("/donate/checkout")
async def donate_checkout(amount: int = Form(...)):
    if amount < 1 or amount > 10_000:
        return RedirectResponse("/donate?error=1", status_code=303)

    stripe = _stripe()
    app_url = os.getenv("APP_URL", "http://localhost:8000")

    session = stripe.checkout.Session.create(
        mode="payment",
        submit_type="donate",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "unit_amount": amount * 100,
                "product_data": {
                    "name": "Support Sex Health News",
                    "description": "Independent reporting on surveillance, censorship, and authoritarian control.",
                },
            },
            "quantity": 1,
        }],
        success_url=f"{app_url}/donate/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{app_url}/donate?cancelled=1",
    )

    return RedirectResponse(session.url, status_code=303)


@router.get("/donate/success", response_class=HTMLResponse)
async def donate_success(
    request: Request,
    session_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_optional_user(request, db)
    amount = None

    if session_id:
        try:
            stripe = _stripe()
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                amount = session.amount_total // 100
        except Exception:
            pass

    return templates.TemplateResponse("donate_success.html", {
        "request": request,
        "categories": CATEGORIES,
        "current_user": current_user,
        "last_updated": _last_updated(),
        "amount": amount,
    })
