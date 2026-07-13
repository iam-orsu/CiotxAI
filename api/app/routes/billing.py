"""CIOTX API — Billing Routes"""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.billing import Invoice, Subscription
from app.services.auth import decode_access_token, get_user_by_id

router = APIRouter(tags=["billing"])

PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 39900,    # in paise (₹399)
        "price_annual": 399900,     # in paise (₹3,999)
        "scans_per_month": 20,
        "max_loc": 50000,
        "features": ["ai_review", "github_connect", "secrets_detection", "dependency_check", "basic_report"],
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 149900,    # in paise (₹1,499)
        "price_annual": 1499900,    # in paise (₹14,999)
        "scans_per_month": -1,      # unlimited
        "max_loc": 200000,
        "features": ["ai_review", "cross_file_analysis", "github_pr_scanning", "scheduled_monitoring",
                     "detailed_report", "team_dashboard", "priority_support", "secrets_detection", "dependency_check"],
    },
}


async def get_current_user(request: Request, db: AsyncSession):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    payload = decode_access_token(auth.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = await get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/billing/plans")
async def list_plans():
    return {"plans": PLANS}


@router.get("/billing/subscription")
async def get_subscription(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)

    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    if not sub:
        return {
            "has_subscription": False,
            "plan": user.plan,
            "plan_status": user.plan_status,
            "trial_ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else None,
        }

    return {
        "has_subscription": True,
        "plan": sub.plan,
        "billing_period": sub.billing_period,
        "status": sub.status,
        "scans_used": sub.scans_used,
        "scans_limit": PLANS.get(sub.plan, {}).get("scans_per_month", 20),
        "current_period_start": sub.current_period_start.isoformat(),
        "current_period_end": sub.current_period_end.isoformat(),
        "created_at": sub.created_at.isoformat(),
    }


@router.post("/billing/subscribe", status_code=201)
async def create_subscription(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)
    body = await request.json()
    plan = body.get("plan", "starter")
    period = body.get("billing_period", "monthly")

    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose 'starter' or 'pro'.")

    if period not in ("monthly", "annual"):
        raise HTTPException(status_code=400, detail="Invalid billing period.")

    plan_info = PLANS[plan]
    amount = plan_info["price_annual"] if period == "annual" else plan_info["price_monthly"]

    # DEV_MODE: skip payment, activate directly
    if settings.DEV_MODE:
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=365 if period == "annual" else 30)

        existing = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = existing.scalar_one_or_none()

        if sub:
            sub.plan = plan
            sub.billing_period = period
            sub.status = "active"
            sub.current_period_end = period_end
        else:
            sub = Subscription(
                user_id=user.id,
                plan=plan,
                billing_period=period,
                status="active",
                current_period_start=now,
                current_period_end=period_end,
            )
            db.add(sub)

        user.plan = plan
        user.plan_status = "active"
        await db.flush()

        return {
            "message": f"Subscribed to {plan_info['name']} ({period}) — DEV MODE",
            "plan": plan,
            "status": "active",
            "current_period_end": period_end.isoformat(),
        }

    # PRODUCTION: Create Razorpay order
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.razorpay.com/v1/orders",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            json={
                "amount": amount,
                "currency": "INR",
                "notes": {
                    "user_id": user.id,
                    "plan": plan,
                    "period": period,
                },
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to create payment order.")

        order = resp.json()

    # Create invoice record
    invoice = Invoice(
        user_id=user.id,
        amount=amount,
        currency="INR",
        status="pending",
        razorpay_order_id=order["id"],
        description=f"{plan_info['name']} ({period})",
    )
    db.add(invoice)
    await db.flush()

    return {
        "order_id": order["id"],
        "amount": amount,
        "currency": "INR",
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "invoice_id": invoice.id,
    }


@router.post("/billing/cancel")
async def cancel_subscription(request: Request, db: AsyncSession = Depends(get_db)):
    user = await get_current_user(request, db)

    result = await db.execute(select(Subscription).where(Subscription.user_id == user.id))
    sub = result.scalar_one_or_none()

    if not sub:
        raise HTTPException(status_code=400, detail="No active subscription.")

    sub.status = "cancelled"
    sub.cancelled_at = datetime.now(timezone.utc)
    await db.flush()

    return {"message": "Subscription cancelled. Access continues until end of billing period."}
