"""Billing and subscription management API routes."""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from .database import get_db
from .db_models import User, SubscriptionTier
from .auth import get_current_active_user
from .billing_service import BillingService
from .usage_metering import UsageMeteringService
from .config import settings
import stripe

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: SubscriptionTier
    success_url: HttpUrl
    cancel_url: HttpUrl


class SubscriptionResponse(BaseModel):
    """Subscription information response."""
    tier: str
    status: str
    monthly_price_cents: int
    current_period_start: str | None
    current_period_end: str | None
    cancel_at_period_end: bool
    usage: Dict[str, Any]


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current usage statistics for the authenticated user."""
    metering_service = UsageMeteringService(db)
    return metering_service.get_usage_stats(current_user)


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get subscription information for the authenticated user."""
    billing_service = BillingService(db)
    return billing_service.get_subscription_info(current_user)


@router.post("/checkout")
async def create_checkout_session(
    checkout_request: CheckoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe checkout session for subscription upgrade."""
    billing_service = BillingService(db)

    # Validate upgrade path
    current_subscription = current_user.subscription
    if not current_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription found"
        )

    # Check if it's an upgrade
    tier_order = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.PRO: 1,
        SubscriptionTier.ENTERPRISE: 2
    }

    current_tier_level = tier_order.get(current_subscription.tier, 0)
    target_tier_level = tier_order.get(checkout_request.tier, 0)

    if target_tier_level <= current_tier_level:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upgrade to a higher tier"
        )

    return billing_service.create_checkout_session(
        user=current_user,
        tier=checkout_request.tier,
        success_url=str(checkout_request.success_url),
        cancel_url=str(checkout_request.cancel_url)
    )


@router.post("/cancel")
async def cancel_subscription(
    immediate: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel the user's subscription."""
    billing_service = BillingService(db)
    subscription = billing_service.cancel_subscription(current_user, immediate)

    return {
        "message": "Subscription canceled successfully",
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "current_period_end": subscription.current_period_end
    }


@router.get("/pricing")
async def get_pricing():
    """Get pricing information for all tiers."""
    return {
        "tiers": [
            {
                "name": "Free",
                "tier": "free",
                "monthly_price_cents": 0,
                "monthly_ai_ops_limit": 100,
                "features": [
                    "100 AI operations per month",
                    "1 active project",
                    "Community support",
                    "Basic features"
                ]
            },
            {
                "name": "Pro",
                "tier": "pro",
                "monthly_price_cents": 4900,
                "monthly_price_display": "$49/month",
                "monthly_ai_ops_limit": 1000,
                "features": [
                    "1,000 AI operations per month",
                    "Up to 10 active projects",
                    "Priority support",
                    "Advanced features",
                    "Analytics dashboard"
                ]
            },
            {
                "name": "Enterprise",
                "tier": "enterprise",
                "monthly_price_cents": None,
                "monthly_price_display": "Custom pricing",
                "monthly_ai_ops_limit": -1,
                "features": [
                    "Unlimited AI operations",
                    "Unlimited projects",
                    "Dedicated support",
                    "Custom integrations",
                    "SLA guarantee",
                    "Custom workflows"
                ]
            }
        ]
    }


@router.get("/metrics")
async def get_conversion_metrics(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get conversion metrics (admin only - add role check in production)."""
    # TODO: Add admin role check
    metering_service = UsageMeteringService(db)
    return metering_service.get_conversion_metrics(days)


@router.post("/webhooks/stripe", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks for subscription events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    billing_service = BillingService(db)

    # Handle different event types
    if event["type"] == "customer.subscription.created":
        billing_service.handle_subscription_created(event["data"]["object"])
    elif event["type"] == "customer.subscription.updated":
        billing_service.handle_subscription_created(event["data"]["object"])
    elif event["type"] == "customer.subscription.deleted":
        billing_service.handle_subscription_deleted(event["data"]["object"])
    elif event["type"] == "payment_intent.succeeded":
        billing_service.handle_payment_succeeded(event["data"]["object"])

    return {"status": "success"}
