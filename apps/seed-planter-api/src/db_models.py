"""SQLAlchemy database models for freemium pricing system."""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Boolean, JSON
from sqlalchemy.orm import relationship
from .database import Base


class SubscriptionTier(PyEnum):
    """Pricing tiers for the platform."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    usage_metrics = relationship("UsageMetric", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    conversion_events = relationship("ConversionEvent", back_populates="user")


class Subscription(Base):
    """User subscription and tier information."""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)

    # Usage limits based on tier
    monthly_ai_ops_limit = Column(Integer, nullable=False)  # Free: 100, Pro: 1000, Enterprise: -1 (unlimited)

    # Stripe integration
    stripe_customer_id = Column(String, unique=True, nullable=True)
    stripe_subscription_id = Column(String, unique=True, nullable=True)
    stripe_price_id = Column(String, nullable=True)

    # Subscription status
    status = Column(String, default="active")  # active, canceled, past_due, trialing
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)

    # Billing
    monthly_price_cents = Column(Integer, default=0)  # Free: 0, Pro: 4900, Enterprise: custom

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="subscription")

    @property
    def is_unlimited(self):
        """Check if subscription has unlimited usage."""
        return self.tier == SubscriptionTier.ENTERPRISE or self.monthly_ai_ops_limit == -1


class UsageMetric(Base):
    """Track user usage for metering and billing."""
    __tablename__ = "usage_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Usage tracking
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # AI operations count
    ai_operations_count = Column(Integer, default=0)  # Issues generated, PRs created, etc.

    # Detailed breakdown
    projects_created = Column(Integer, default=0)
    issues_generated = Column(Integer, default=0)
    prs_created = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)

    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional usage details

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="usage_metrics")


class Payment(Base):
    """Track payment transactions."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Payment details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="usd")
    status = Column(String, nullable=False)  # succeeded, pending, failed, refunded

    # Stripe integration
    stripe_payment_intent_id = Column(String, unique=True, nullable=True)
    stripe_invoice_id = Column(String, nullable=True)
    stripe_charge_id = Column(String, nullable=True)

    # Payment type
    payment_type = Column(String, nullable=False)  # subscription, upgrade, overage
    description = Column(String, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="payments")


class ConversionEvent(Base):
    """Track conversion metrics for revenue analytics."""
    __tablename__ = "conversion_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Event tracking
    event_type = Column(String, nullable=False)  # free_signup, free_to_pro, pro_to_enterprise, downgrade, churn
    from_tier = Column(Enum(SubscriptionTier), nullable=True)
    to_tier = Column(Enum(SubscriptionTier), nullable=True)

    # Revenue impact
    revenue_impact_cents = Column(Integer, default=0)  # Monthly recurring revenue change

    # Context
    trigger_reason = Column(String, nullable=True)  # quota_reached, upgrade_prompt, manual, etc.
    days_in_previous_tier = Column(Integer, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversion_events")


class PricingConfig(Base):
    """Configuration for pricing tiers (allows dynamic updates)."""
    __tablename__ = "pricing_config"

    id = Column(Integer, primary_key=True, index=True)
    tier = Column(Enum(SubscriptionTier), unique=True, nullable=False)

    # Limits
    monthly_ai_ops_limit = Column(Integer, nullable=False)

    # Pricing
    monthly_price_cents = Column(Integer, nullable=False)
    annual_price_cents = Column(Integer, nullable=True)

    # Stripe integration
    stripe_monthly_price_id = Column(String, nullable=True)
    stripe_annual_price_id = Column(String, nullable=True)

    # Features (JSON for flexibility)
    features = Column(JSON, nullable=True)

    # Display
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
