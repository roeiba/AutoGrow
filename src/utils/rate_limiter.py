#!/usr/bin/env python3
"""
Rate Limiter - Prevents issue generation spam spiral

Provides safeguards:
1. Time-based rate limiting (max issues per time window)
2. Duplicate prevention tracking
3. Quality threshold enforcement
4. Cooldown periods after high rejection rates
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_issues_per_hour: int = 10
    max_issues_per_day: int = 50
    max_duplicate_rate: float = 0.7  # Max % of duplicates before cooldown
    max_quality_reject_rate: float = 0.5  # Max % of quality rejections before cooldown
    cooldown_minutes: int = 60
    min_time_between_generations_minutes: int = 5


@dataclass
class GenerationAttempt:
    """Record of a single generation attempt"""
    timestamp: str
    issues_proposed: int
    issues_created: int
    duplicates_filtered: int
    quality_rejected: int
    success: bool


class RateLimiter:
    """Rate limiter to prevent issue generation spam"""

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        state_path: Optional[Path] = None
    ):
        """
        Initialize rate limiter

        Args:
            config: Rate limit configuration
            state_path: Path to state file (defaults to .autogrow/rate_limit_state.json)
        """
        self.config = config or RateLimitConfig()

        if state_path is None:
            state_path = Path.cwd() / ".autogrow" / "rate_limit_state.json"

        self.state_path = state_path
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load rate limiter state from disk"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load rate limit state: {e}")

        # Default state
        return {
            "attempts": [],
            "last_generation_timestamp": None,
            "cooldown_until": None
        }

    def _save_state(self):
        """Save rate limiter state to disk"""
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save rate limit state: {e}")

    def can_generate(self) -> Tuple[bool, Optional[str]]:
        """
        Check if issue generation is allowed

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
            If not allowed, reason explains why
        """
        now = datetime.utcnow()

        # Check cooldown period
        if self.state.get("cooldown_until"):
            cooldown_until = datetime.fromisoformat(self.state["cooldown_until"])
            if now < cooldown_until:
                remaining = (cooldown_until - now).total_seconds() / 60
                return False, f"In cooldown period (remaining: {remaining:.1f} minutes)"

        # Check minimum time between generations
        last_gen = self.state.get("last_generation_timestamp")
        if last_gen:
            last_gen_time = datetime.fromisoformat(last_gen)
            min_interval = timedelta(minutes=self.config.min_time_between_generations_minutes)
            if now - last_gen_time < min_interval:
                remaining = (last_gen_time + min_interval - now).total_seconds() / 60
                return False, f"Too soon since last generation (wait {remaining:.1f} minutes)"

        # Check hourly rate limit
        one_hour_ago = now - timedelta(hours=1)
        recent_attempts = self._get_attempts_since(one_hour_ago)
        total_created_hour = sum(a["issues_created"] for a in recent_attempts)

        if total_created_hour >= self.config.max_issues_per_hour:
            return False, f"Hourly rate limit reached ({total_created_hour}/{self.config.max_issues_per_hour})"

        # Check daily rate limit
        one_day_ago = now - timedelta(days=1)
        daily_attempts = self._get_attempts_since(one_day_ago)
        total_created_day = sum(a["issues_created"] for a in daily_attempts)

        if total_created_day >= self.config.max_issues_per_day:
            return False, f"Daily rate limit reached ({total_created_day}/{self.config.max_issues_per_day})"

        # Check duplicate rate (triggers cooldown)
        if len(recent_attempts) >= 3:  # Need at least 3 attempts to assess pattern
            total_proposed = sum(a["issues_proposed"] for a in recent_attempts)
            total_duplicates = sum(a["duplicates_filtered"] for a in recent_attempts)

            if total_proposed > 0:
                duplicate_rate = total_duplicates / total_proposed

                if duplicate_rate >= self.config.max_duplicate_rate:
                    self._trigger_cooldown("high duplicate rate")
                    return False, f"High duplicate rate detected ({duplicate_rate:.1%}), entering cooldown"

        # Check quality rejection rate (triggers cooldown)
        if len(recent_attempts) >= 3:
            total_proposed = sum(a["issues_proposed"] for a in recent_attempts)
            total_rejected = sum(a["quality_rejected"] for a in recent_attempts)

            if total_proposed > 0:
                reject_rate = total_rejected / total_proposed

                if reject_rate >= self.config.max_quality_reject_rate:
                    self._trigger_cooldown("high quality rejection rate")
                    return False, f"High quality rejection rate ({reject_rate:.1%}), entering cooldown"

        return True, None

    def record_generation(
        self,
        issues_proposed: int,
        issues_created: int,
        duplicates_filtered: int,
        quality_rejected: int = 0
    ):
        """
        Record a generation attempt

        Args:
            issues_proposed: Number of issues proposed by AI
            issues_created: Number of issues actually created
            duplicates_filtered: Number of duplicates filtered out
            quality_rejected: Number of issues rejected for low quality
        """
        now = datetime.utcnow()

        attempt = GenerationAttempt(
            timestamp=now.isoformat(),
            issues_proposed=issues_proposed,
            issues_created=issues_created,
            duplicates_filtered=duplicates_filtered,
            quality_rejected=quality_rejected,
            success=issues_created > 0
        )

        # Add to state
        if "attempts" not in self.state:
            self.state["attempts"] = []

        self.state["attempts"].append(asdict(attempt))
        self.state["last_generation_timestamp"] = now.isoformat()

        # Cleanup old attempts (keep last 7 days)
        self._cleanup_old_attempts()

        # Save state
        self._save_state()

        # Log statistics
        logger.info("Generation recorded", extra={
            "proposed": issues_proposed,
            "issues_created": issues_created,
            "duplicates": duplicates_filtered,
            "quality_rejected": quality_rejected,
            "success": attempt.success
        })

    def _get_attempts_since(self, cutoff: datetime) -> List[Dict]:
        """Get all attempts since cutoff time"""
        attempts = self.state.get("attempts", [])
        return [
            a for a in attempts
            if datetime.fromisoformat(a["timestamp"]) >= cutoff
        ]

    def _cleanup_old_attempts(self):
        """Remove attempts older than 7 days"""
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.state["attempts"] = [
            a for a in self.state.get("attempts", [])
            if datetime.fromisoformat(a["timestamp"]) >= cutoff
        ]

    def _trigger_cooldown(self, reason: str):
        """Trigger cooldown period"""
        now = datetime.utcnow()
        cooldown_until = now + timedelta(minutes=self.config.cooldown_minutes)
        self.state["cooldown_until"] = cooldown_until.isoformat()
        self._save_state()

        logger.warning(f"Cooldown triggered: {reason} (until {cooldown_until.isoformat()})")

    def get_statistics(self) -> Dict:
        """Get rate limiting statistics"""
        now = datetime.utcnow()

        # Last hour stats
        one_hour_ago = now - timedelta(hours=1)
        hour_attempts = self._get_attempts_since(one_hour_ago)
        hour_created = sum(a["issues_created"] for a in hour_attempts)

        # Last day stats
        one_day_ago = now - timedelta(days=1)
        day_attempts = self._get_attempts_since(one_day_ago)
        day_created = sum(a["issues_created"] for a in day_attempts)

        # Overall stats
        all_attempts = self.state.get("attempts", [])
        if all_attempts:
            total_proposed = sum(a["issues_proposed"] for a in all_attempts)
            total_created = sum(a["issues_created"] for a in all_attempts)
            total_duplicates = sum(a["duplicates_filtered"] for a in all_attempts)
            total_quality_rejected = sum(a["quality_rejected"] for a in all_attempts)

            duplicate_rate = total_duplicates / total_proposed if total_proposed > 0 else 0
            quality_reject_rate = total_quality_rejected / total_proposed if total_proposed > 0 else 0
        else:
            total_proposed = 0
            total_created = 0
            total_duplicates = 0
            total_quality_rejected = 0
            duplicate_rate = 0
            quality_reject_rate = 0

        return {
            "last_hour": {
                "issues_created": hour_created,
                "limit": self.config.max_issues_per_hour,
                "remaining": max(0, self.config.max_issues_per_hour - hour_created)
            },
            "last_day": {
                "issues_created": day_created,
                "limit": self.config.max_issues_per_day,
                "remaining": max(0, self.config.max_issues_per_day - day_created)
            },
            "lifetime": {
                "total_attempts": len(all_attempts),
                "total_proposed": total_proposed,
                "total_created": total_created,
                "total_duplicates": total_duplicates,
                "total_quality_rejected": total_quality_rejected,
                "duplicate_rate": duplicate_rate,
                "quality_reject_rate": quality_reject_rate
            },
            "cooldown": {
                "active": self.state.get("cooldown_until") is not None and
                          datetime.fromisoformat(self.state["cooldown_until"]) > now,
                "until": self.state.get("cooldown_until")
            }
        }

    def reset_cooldown(self):
        """Manually reset cooldown (for testing or administrative override)"""
        self.state["cooldown_until"] = None
        self._save_state()
        logger.info("Cooldown manually reset")
