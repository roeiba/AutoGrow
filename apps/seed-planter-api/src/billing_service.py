"""Billing and subscription management service with Stripe integration."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import stripe
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from .db_models import User, Subscription, Payment, SubscriptionTier, ConversionEvent
from .usage_metering import UsageMeteringService
from .config import settings


class BillingService:
    """Service for managing subscriptions and payments."""

    def __init__(self, db: Session):
        self.db = db
        self.metering_service = UsageMeteringService(db)
        stripe.api_key = settings.stripe_secret_key

    def create_free_subscription(self, user: User) -> Subscription:
        """Create a free tier subscription for a new user."""
        # Check if user already has a subscription
        existing = self.db.query(Subscription).filter(
            Subscription.user_id == user.id
        ).first()

        if existing:
            return existing

        # Create free subscription
        subscription = Subscription(
            user_id=user.id,
            tier=SubscriptionTier.FREE,
            monthly_ai_ops_limit=100,
            monthly_price_cents=0,
            status="active"
        )

        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)

        # Track conversion event
        self.metering_service.track_conversion_event(
            user=user,
            event_type="free_signup",
            to_tier=SubscriptionTier.FREE,
            trigger_reason="registration"
        )

        return subscription

    def create_stripe_customer(self, user: User, payment_method_id: Optional[str] = None) -> str:
        """Create a Stripe customer for the user."""
        subscription = user.subscription
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        # Create Stripe customer
        customer_data = {
            "email": user.email,
            "metadata": {
                "user_id": str(user.id),
                "full_name": user.full_name or ""
            }
        }

        if payment_method_id:
            customer_data["payment_method"] = payment_method_id
            customer_data["invoice_settings"] = {
                "default_payment_method": payment_method_id
            }

        customer = stripe.Customer.create(**customer_data)

        # Update subscription with customer ID
        if not subscription:
            subscription = self.create_free_subscription(user)

        subscription.stripe_customer_id = customer.id
        self.db.commit()

        return customer.id

    def create_checkout_session(
        self,
        user: User,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session for subscription upgrade."""
        if tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create checkout session for free tier"
            )

        # Get or create Stripe customer
        customer_id = self.create_stripe_customer(user)

        # Get price ID for tier
        price_id = None
        if tier == SubscriptionTier.PRO:
            price_id = settings.stripe_pro_price_id
        elif tier == SubscriptionTier.ENTERPRISE:
            price_id = settings.stripe_enterprise_price_id

        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Price not configured for tier: {tier.value}"
            )

        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user.id),
                "tier": tier.value
            }
        )

        return {
            "checkout_session_id": session.id,
            "checkout_url": session.url
        }

    def handle_subscription_created(self, stripe_subscription: Dict[str, Any]):
        """Handle Stripe subscription.created webhook."""
        user_id = int(stripe_subscription["metadata"].get("user_id"))
        tier_value = stripe_subscription["metadata"].get("tier")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User not found: {user_id}")

        tier = SubscriptionTier(tier_value)
        subscription = user.subscription

        # Track previous tier for conversion metrics
        previous_tier = subscription.tier if subscription else None

        # Update subscription
        if not subscription:
            subscription = Subscription(user_id=user.id)
            self.db.add(subscription)

        subscription.tier = tier
        subscription.stripe_subscription_id = stripe_subscription["id"]
        subscription.stripe_customer_id = stripe_subscription["customer"]
        subscription.stripe_price_id = stripe_subscription["items"]["data"][0]["price"]["id"]
        subscription.status = stripe_subscription["status"]
        subscription.current_period_start = datetime.fromtimestamp(
            stripe_subscription["current_period_start"]
        )
        subscription.current_period_end = datetime.fromtimestamp(
            stripe_subscription["current_period_end"]
        )

        # Set limits based on tier
        if tier == SubscriptionTier.PRO:
            subscription.monthly_ai_ops_limit = 1000
            subscription.monthly_price_cents = 4900
        elif tier == SubscriptionTier.ENTERPRISE:
            subscription.monthly_ai_ops_limit = -1  # Unlimited
            subscription.monthly_price_cents = stripe_subscription["items"]["data"][0]["price"]["unit_amount"]

        self.db.commit()

        # Track conversion event
        if previous_tier:
            if previous_tier == SubscriptionTier.FREE and tier == SubscriptionTier.PRO:
                event_type = "free_to_pro"
            elif previous_tier == SubscriptionTier.PRO and tier == SubscriptionTier.ENTERPRISE:
                event_type = "pro_to_enterprise"
            else:
                event_type = "tier_change"

            self.metering_service.track_conversion_event(
                user=user,
                event_type=event_type,
                from_tier=previous_tier,
                to_tier=tier,
                trigger_reason="stripe_subscription",
                metadata={"stripe_subscription_id": stripe_subscription["id"]}
            )

    def handle_payment_succeeded(self, payment_intent: Dict[str, Any]):
        """Handle Stripe payment_intent.succeeded webhook."""
        customer_id = payment_intent["customer"]

        # Find subscription by customer ID
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_customer_id == customer_id
        ).first()

        if not subscription:
            return

        # Create payment record
        payment = Payment(
            user_id=subscription.user_id,
            amount_cents=payment_intent["amount"],
            currency=payment_intent["currency"],
            status="succeeded",
            stripe_payment_intent_id=payment_intent["id"],
            stripe_charge_id=payment_intent.get("charges", {}).get("data", [{}])[0].get("id"),
            payment_type="subscription",
            description=f"Subscription payment for {subscription.tier.value} tier"
        )

        self.db.add(payment)
        self.db.commit()

    def handle_subscription_deleted(self, stripe_subscription: Dict[str, Any]):
        """Handle Stripe subscription.deleted webhook (cancellation/churn)."""
        subscription_id = stripe_subscription["id"]

        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()

        if not subscription:
            return

        previous_tier = subscription.tier
        user = subscription.user

        # Downgrade to free tier
        subscription.tier = SubscriptionTier.FREE
        subscription.monthly_ai_ops_limit = 100
        subscription.monthly_price_cents = 0
        subscription.status = "canceled"
        subscription.stripe_subscription_id = None
        subscription.stripe_price_id = None

        self.db.commit()

        # Track churn event
        self.metering_service.track_conversion_event(
            user=user,
            event_type="churn",
            from_tier=previous_tier,
            to_tier=SubscriptionTier.FREE,
            trigger_reason="subscription_canceled",
            metadata={"stripe_subscription_id": stripe_subscription["id"]}
        )

    def cancel_subscription(self, user: User, immediate: bool = False) -> Subscription:
        """Cancel a user's subscription."""
        subscription = user.subscription
        if not subscription or subscription.tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active subscription to cancel"
            )

        if not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription not managed by Stripe"
            )

        # Cancel in Stripe
        if immediate:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
        else:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True
            self.db.commit()

        return subscription

    def get_subscription_info(self, user: User) -> Dict[str, Any]:
        """Get detailed subscription information for a user."""
        subscription = user.subscription
        if not subscription:
            return {
                "tier": None,
                "status": "no_subscription",
                "message": "No subscription found"
            }

        usage_stats = self.metering_service.get_usage_stats(user)

        return {
            "tier": subscription.tier.value,
            "status": subscription.status,
            "monthly_price_cents": subscription.monthly_price_cents,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "usage": usage_stats
        }
