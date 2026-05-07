import json
import logging
import os
import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import BillingAccount, BillingTransaction, Course, Enrollment
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def _stripe():
    key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not configured")
    stripe.api_key = key
    return stripe

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


async def get_or_create_billing_account(db: AsyncSession, user_id: str) -> BillingAccount:
    result = await db.execute(select(BillingAccount).where(BillingAccount.user_id == user_id))
    account = result.scalar_one_or_none()
    if not account:
        account = BillingAccount(user_id=user_id, plan="payg")
        db.add(account)
        await db.flush()
    return account


async def create_checkout_session(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    course_id: str,
) -> dict:
    """Create a Stripe Checkout session for a paid course enrolment."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise ValueError("Course not found")

    price_pence = getattr(course, "price_pence", 0) or 0
    if price_pence <= 0:
        raise ValueError("Course is free — enrol directly via /api/catalog/{id}/enrol")

    account = await get_or_create_billing_account(db, user_id)
    await db.commit()

    s = _stripe()

    # Get or create Stripe customer
    customer_id = account.stripe_customer_id
    if not customer_id:
        customer = s.Customer.create(
            email=user_email,
            metadata={"user_id": user_id},
        )
        account.stripe_customer_id = customer.id
        await db.commit()
        customer_id = customer.id

    session = s.checkout.Session.create(
        mode="payment",
        customer=customer_id,
        success_url=f"{BASE_URL}/learn/{course_id}?paid=1",
        cancel_url=f"{BASE_URL}/catalog/{course_id}",
        automatic_tax={"enabled": True},  # Stripe Tax — automated VAT
        line_items=[{
            "price_data": {
                "currency": "gbp",
                "product_data": {
                    "name": course.title,
                    "metadata": {"course_id": course_id},
                },
                "unit_amount": price_pence,
            },
            "quantity": 1,
        }],
        metadata={"course_id": course_id, "user_id": user_id},
    )
    return {"checkout_url": session.url, "session_id": session.id}


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str) -> dict:
    """Verify and process a Stripe webhook event. Idempotent."""
    s = _stripe()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    try:
        # Use SDK only for signature verification
        s.Webhook.construct_event(payload, sig_header, secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid webhook signature")

    # Parse raw JSON payload for data access — avoids StripeObject quirks in SDK v15
    event_dict = json.loads(payload)
    event_type = event_dict.get("type", "")
    obj = event_dict.get("data", {}).get("object", {})

    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        await _handle_checkout_complete(db, obj)
    elif event_type == "payment_intent.payment_failed":
        await _handle_payment_failed(db, obj)
    elif event_type == "charge.refunded":
        await _handle_refund(db, obj)

    return {"received": True, "type": event_type}


async def _handle_checkout_complete(db: AsyncSession, session: dict) -> None:
    payment_intent_id = session.get("payment_intent")
    course_id = session.get("metadata", {}).get("course_id")
    user_id = session.get("metadata", {}).get("user_id")
    amount = session.get("amount_total", 0)

    if not all([payment_intent_id, course_id, user_id]):
        logger.warning("Incomplete checkout.session.completed metadata: %s", session.get("id"))
        return

    # Idempotency check
    existing = await db.execute(
        select(BillingTransaction).where(BillingTransaction.stripe_payment_intent == payment_intent_id)
    )
    if existing.scalar_one_or_none():
        logger.info("Duplicate webhook for payment_intent %s — skipping", payment_intent_id)
        return

    account = await get_or_create_billing_account(db, user_id)

    txn = BillingTransaction(
        account_id=account.id,
        course_id=course_id,
        stripe_payment_intent=payment_intent_id,
        amount_pence=amount,
        currency="GBP",
        status="succeeded",
    )
    db.add(txn)

    # Create enrollment if not already enrolled
    existing_enrol = await db.execute(
        select(Enrollment).where(Enrollment.user_id == user_id, Enrollment.course_id == course_id)
    )
    if not existing_enrol.scalar_one_or_none():
        db.add(Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
        ))

    await db.commit()
    logger.info("Enrolment created for user=%s course=%s via Stripe", user_id, course_id)


async def _handle_payment_failed(db: AsyncSession, pi: dict) -> None:
    pi_id = pi.get("id")
    if not pi_id:
        return
    existing = await db.execute(
        select(BillingTransaction).where(BillingTransaction.stripe_payment_intent == pi_id)
    )
    txn = existing.scalar_one_or_none()
    if txn:
        txn.status = "failed"
    else:
        # Pre-emptively record the failure (checkout may not have completed)
        logger.info("payment_intent.payment_failed for unknown txn: %s", pi_id)
    await db.commit()


async def _handle_refund(db: AsyncSession, charge: dict) -> None:
    pi_id = charge.get("payment_intent")
    if not pi_id:
        return
    existing = await db.execute(
        select(BillingTransaction).where(BillingTransaction.stripe_payment_intent == pi_id)
    )
    txn = existing.scalar_one_or_none()
    if txn:
        txn.status = "refunded"
        await db.commit()
