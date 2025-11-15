"""Usage metering service for tracking AI operations and enforcing quotas."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fastapi import HTTPException, status
from .db_models import User, Subscription, UsageMetric, SubscriptionTier, ConversionEvent


class UsageMeteringService:
    """Service for tracking and enforcing usage limits."""

    # Tier limits (AI operations per month)
    TIER_LIMITS = {
        SubscriptionTier.FREE: 100,
        SubscriptionTier.PRO: 1000,
        SubscriptionTier.ENTERPRISE: -1  # Unlimited
    }

    # Tier pricing (cents per month)
    TIER_PRICING = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.PRO: 4900,
        SubscriptionTier.ENTERPRISE: None  # Custom pricing
    }

    def __init__(self, db: Session):
        self.db = db

    def get_current_period(self) -> tuple[datetime, datetime]:
        """Get the current billing period (month)."""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Get first day of next month
        if now.month == 12:
            period_end = period_start.replace(year=now.year + 1, month=1)
        else:
            period_end = period_start.replace(month=now.month + 1)
        return period_start, period_end

    def get_or_create_usage_metric(self, user_id: int) -> UsageMetric:
        """Get or create usage metric for current period."""
        period_start, period_end = self.get_current_period()

        # Try to find existing metric
        metric = self.db.query(UsageMetric).filter(
            and_(
                UsageMetric.user_id == user_id,
                UsageMetric.period_start == period_start,
                UsageMetric.period_end == period_end
            )
        ).first()

        if not metric:
            # Create new metric for this period
            metric = UsageMetric(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                ai_operations_count=0,
                projects_created=0,
                issues_generated=0,
                prs_created=0,
                api_calls=0
            )
            self.db.add(metric)
            self.db.commit()
            self.db.refresh(metric)

        return metric

    def get_usage_stats(self, user: User) -> Dict[str, Any]:
        """Get current usage statistics for a user."""
        metric = self.get_or_create_usage_metric(user.id)

        # Get subscription and limits
        subscription = user.subscription
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User subscription not found"
            )

        limit = subscription.monthly_ai_ops_limit
        current_usage = metric.ai_operations_count
        is_unlimited = subscription.is_unlimited

        # Calculate usage percentage
        if is_unlimited:
            usage_percentage = 0.0
        elif limit > 0:
            usage_percentage = (current_usage / limit) * 100
        else:
            usage_percentage = 100.0 if current_usage > 0 else 0.0

        return {
            "user_id": user.id,
            "subscription_tier": subscription.tier.value,
            "period_start": metric.period_start,
            "period_end": metric.period_end,
            "usage": {
                "ai_operations": current_usage,
                "projects_created": metric.projects_created,
                "issues_generated": metric.issues_generated,
                "prs_created": metric.prs_created,
                "api_calls": metric.api_calls
            },
            "limits": {
                "monthly_ai_ops_limit": limit if not is_unlimited else None,
                "is_unlimited": is_unlimited
            },
            "usage_percentage": usage_percentage,
            "quota_warning": usage_percentage >= 80.0 and not is_unlimited,
            "quota_exceeded": current_usage >= limit and not is_unlimited and limit > 0
        }

    def check_quota(self, user: User, operation_count: int = 1) -> bool:
        """Check if user has quota available for operation."""
        subscription = user.subscription
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User subscription not found"
            )

        # Enterprise/unlimited users always pass
        if subscription.is_unlimited:
            return True

        metric = self.get_or_create_usage_metric(user.id)
        limit = subscription.monthly_ai_ops_limit

        return (metric.ai_operations_count + operation_count) <= limit

    def increment_usage(
        self,
        user: User,
        ai_operations: int = 1,
        projects: int = 0,
        issues: int = 0,
        prs: int = 0,
        api_calls: int = 1
    ) -> UsageMetric:
        """Increment usage counters for a user."""
        metric = self.get_or_create_usage_metric(user.id)

        metric.ai_operations_count += ai_operations
        metric.projects_created += projects
        metric.issues_generated += issues
        metric.prs_created += prs
        metric.api_calls += api_calls
        metric.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(metric)

        return metric

    def enforce_quota(self, user: User, operation_count: int = 1):
        """Enforce quota limits, raise exception if exceeded."""
        if not self.check_quota(user, operation_count):
            stats = self.get_usage_stats(user)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Usage quota exceeded",
                    "current_usage": stats["usage"]["ai_operations"],
                    "limit": stats["limits"]["monthly_ai_ops_limit"],
                    "tier": stats["subscription_tier"],
                    "message": f"You've reached your {stats['subscription_tier']} plan limit. Please upgrade to continue.",
                    "upgrade_url": "/billing/upgrade"
                }
            )

    def get_usage_history(self, user_id: int, months: int = 6) -> list[UsageMetric]:
        """Get usage history for the past N months."""
        cutoff_date = datetime.utcnow() - timedelta(days=30 * months)

        metrics = self.db.query(UsageMetric).filter(
            and_(
                UsageMetric.user_id == user_id,
                UsageMetric.period_start >= cutoff_date
            )
        ).order_by(UsageMetric.period_start.desc()).all()

        return metrics

    def track_conversion_event(
        self,
        user: User,
        event_type: str,
        from_tier: Optional[SubscriptionTier] = None,
        to_tier: Optional[SubscriptionTier] = None,
        trigger_reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversionEvent:
        """Track a conversion event for analytics."""
        # Calculate revenue impact
        revenue_impact = 0
        if from_tier and to_tier:
            from_price = self.TIER_PRICING.get(from_tier, 0) or 0
            to_price = self.TIER_PRICING.get(to_tier, 0) or 0
            revenue_impact = to_price - from_price

        # Calculate days in previous tier
        days_in_previous_tier = None
        if from_tier:
            previous_event = self.db.query(ConversionEvent).filter(
                and_(
                    ConversionEvent.user_id == user.id,
                    ConversionEvent.to_tier == from_tier
                )
            ).order_by(ConversionEvent.created_at.desc()).first()

            if previous_event:
                days_in_previous_tier = (datetime.utcnow() - previous_event.created_at).days

        event = ConversionEvent(
            user_id=user.id,
            event_type=event_type,
            from_tier=from_tier,
            to_tier=to_tier,
            revenue_impact_cents=revenue_impact,
            trigger_reason=trigger_reason,
            days_in_previous_tier=days_in_previous_tier,
            metadata=metadata
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_conversion_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get conversion metrics for analytics dashboard."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Total signups
        total_signups = self.db.query(func.count(ConversionEvent.id)).filter(
            and_(
                ConversionEvent.event_type == "free_signup",
                ConversionEvent.created_at >= cutoff_date
            )
        ).scalar()

        # Free to paid conversions
        free_to_paid = self.db.query(func.count(ConversionEvent.id)).filter(
            and_(
                ConversionEvent.event_type == "free_to_pro",
                ConversionEvent.created_at >= cutoff_date
            )
        ).scalar()

        # Expansion revenue (upgrades)
        expansion_revenue = self.db.query(func.sum(ConversionEvent.revenue_impact_cents)).filter(
            and_(
                ConversionEvent.event_type.in_(["free_to_pro", "pro_to_enterprise"]),
                ConversionEvent.created_at >= cutoff_date
            )
        ).scalar() or 0

        # Churn by tier
        churn_by_tier = {}
        for tier in SubscriptionTier:
            churn_count = self.db.query(func.count(ConversionEvent.id)).filter(
                and_(
                    ConversionEvent.event_type == "churn",
                    ConversionEvent.from_tier == tier,
                    ConversionEvent.created_at >= cutoff_date
                )
            ).scalar()
            churn_by_tier[tier.value] = churn_count

        # Conversion rate
        conversion_rate = (free_to_paid / total_signups * 100) if total_signups > 0 else 0.0

        return {
            "period_days": days,
            "total_signups": total_signups,
            "free_to_paid_conversions": free_to_paid,
            "conversion_rate_percent": round(conversion_rate, 2),
            "expansion_revenue_cents": expansion_revenue,
            "churn_by_tier": churn_by_tier
        }
