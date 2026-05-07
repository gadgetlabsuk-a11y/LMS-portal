import logging
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import BillingTransaction
from app.services.billing_service import create_checkout_session, handle_webhook_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["billing"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def get_user(x_user_id: str = Header(default="system")) -> str:
    return x_user_id


class CheckoutBody(BaseModel):
    course_id: str


@router.post("/billing/checkout")
async def checkout(
    body: CheckoutBody,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
    x_user_email: str = Header(default=""),
):
    """Create a Stripe Checkout session for a paid course."""
    try:
        result = await create_checkout_session(
            db=db,
            user_id=user_id,
            user_email=x_user_email or f"{user_id}@placeholder.invalid",
            course_id=body.course_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        logger.error("Checkout error: %s", e)
        raise HTTPException(502, "Payment service unavailable")


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Stripe webhook — verified via signature. Must be unauthenticated."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        result = await handle_webhook_event(db, payload, sig)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error("Webhook processing error: %s", e)
        raise HTTPException(500, "Webhook processing failed")


@router.get("/billing/transactions")
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_user),
):
    """Return the authenticated user's own billing transactions."""
    from app.models import BillingAccount
    result = await db.execute(
        select(BillingAccount).where(BillingAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        return []

    txns = await db.execute(
        select(BillingTransaction)
        .where(BillingTransaction.account_id == account.id)
        .order_by(BillingTransaction.created_at.desc())
    )
    return [
        {
            "id": t.id,
            "course_id": t.course_id,
            "amount_pence": t.amount_pence,
            "currency": t.currency,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in txns.scalars().all()
    ]
