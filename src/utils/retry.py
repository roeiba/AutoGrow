#!/usr/bin/env python3
"""
Retry Utility with Exponential Backoff and Jitter

Provides retry logic for API calls to handle transient failures,
rate limiting, and network issues for Anthropic and GitHub APIs.
"""

import time
import random
import functools
from typing import Callable, Type, Tuple, Optional
from datetime import datetime
import logging

# Get logger
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry configuration

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class RetryableError(Exception):
    """Base exception for retryable errors"""

    pass


class RateLimitError(RetryableError):
    """Exception for rate limit errors"""

    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class NetworkError(RetryableError):
    """Exception for network-related errors"""

    pass


def calculate_delay(
    attempt: int, config: RetryConfig, rate_limit_retry_after: Optional[int] = None
) -> float:
    """
    Calculate delay for next retry with exponential backoff and jitter

    Args:
        attempt: Current retry attempt number (0-indexed)
        config: Retry configuration
        rate_limit_retry_after: Explicit retry-after value from rate limit response

    Returns:
        Delay in seconds before next retry
    """
    # If rate limit specifies retry-after, use that
    if rate_limit_retry_after is not None:
        return min(float(rate_limit_retry_after), config.max_delay)

    # Calculate exponential backoff
    delay = min(
        config.base_delay * (config.exponential_base**attempt), config.max_delay
    )

    # Add jitter to prevent thundering herd
    if config.jitter:
        # Add random jitter of ±25% of the delay
        jitter_amount = delay * 0.25
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
        # Ensure delay is never negative
        delay = max(0.1, delay)

    return delay


def should_retry(exception: Exception, retryable_exceptions: Tuple[Type[Exception], ...]) -> bool:
    """
    Determine if an exception should trigger a retry

    Args:
        exception: The exception that was raised
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        True if should retry, False otherwise
    """
    # Check if exception is in retryable list
    if isinstance(exception, retryable_exceptions):
        return True

    # Check for specific error messages indicating transient failures
    error_msg = str(exception).lower()
    transient_indicators = [
        "timeout",
        "timed out",
        "connection",
        "network",
        "temporary",
        "unavailable",
        "503",
        "502",
        "429",
        "rate limit",
        "too many requests",
    ]

    return any(indicator in error_msg for indicator in transient_indicators)


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorator to add retry logic with exponential backoff to a function

    Args:
        config: Retry configuration (uses defaults if None)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called before each retry
                  Signature: on_retry(exception, attempt, delay)

    Example:
        @retry_with_backoff(
            config=RetryConfig(max_retries=3, base_delay=1.0),
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        def call_api():
            # API call logic
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        logger.info(
                            f"Success after {attempt} retry/retries: {func.__name__}"
                        )
                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we've exhausted retries
                    if attempt >= config.max_retries:
                        logger.error(
                            f"Max retries ({config.max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        raise

                    # Check if exception is retryable
                    if not should_retry(e, retryable_exceptions):
                        logger.error(
                            f"Non-retryable exception in {func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    rate_limit_retry_after = None
                    if isinstance(e, RateLimitError):
                        rate_limit_retry_after = e.retry_after

                    delay = calculate_delay(attempt, config, rate_limit_retry_after)

                    # Log retry attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                        f"after {delay:.2f}s (error: {type(e).__name__}: {str(e)[:100]})"
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt + 1, delay)

                    # Wait before retrying
                    time.sleep(delay)

            # This should never be reached, but just in case
            raise last_exception

        return wrapper

    return decorator


# Anthropic-specific retry configuration
ANTHROPIC_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    jitter=True,
)


# GitHub-specific retry configuration
GITHUB_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
)


def classify_anthropic_exception(e: Exception) -> Exception:
    """
    Classify Anthropic API exceptions for retry logic

    Args:
        e: Original exception

    Returns:
        Classified exception (RateLimitError, NetworkError, or original)
    """
    error_msg = str(e).lower()

    # Check for rate limiting
    if "rate limit" in error_msg or "429" in error_msg or "too many requests" in error_msg:
        # Try to extract retry-after if available
        retry_after = None
        # This is a simplified extraction - actual implementation may need
        # to parse response headers for Retry-After
        return RateLimitError(retry_after=retry_after)

    # Check for network errors
    if any(
        indicator in error_msg
        for indicator in ["connection", "timeout", "network", "503", "502"]
    ):
        return NetworkError(str(e))

    # Return original exception
    return e


def classify_github_exception(e: Exception) -> Exception:
    """
    Classify GitHub API exceptions for retry logic

    Args:
        e: Original exception

    Returns:
        Classified exception (RateLimitError, NetworkError, or original)
    """
    error_msg = str(e).lower()

    # Check for rate limiting (GitHub returns 403 for rate limits)
    if "rate limit" in error_msg or "403" in error_msg or "abuse" in error_msg:
        # Try to extract rate limit reset time from exception
        # GithubException often includes this info
        retry_after = None
        if hasattr(e, "data") and isinstance(e.data, dict):
            # GitHub rate limit info may be in exception data
            if "retry-after" in e.data:
                retry_after = e.data["retry-after"]
        return RateLimitError(retry_after=retry_after)

    # Check for network errors
    if any(
        indicator in error_msg
        for indicator in ["connection", "timeout", "network", "503", "502", "500"]
    ):
        return NetworkError(str(e))

    # Return original exception
    return e


def retry_anthropic_api(func: Callable) -> Callable:
    """
    Decorator specifically for Anthropic API calls with appropriate retry logic

    Example:
        @retry_anthropic_api
        def call_anthropic_api():
            return client.messages.create(...)
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        @retry_with_backoff(
            config=ANTHROPIC_RETRY_CONFIG,
            retryable_exceptions=(RetryableError, ConnectionError, TimeoutError),
        )
        def inner():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Classify and re-raise with appropriate type
                classified = classify_anthropic_exception(e)
                if classified is not e:
                    raise classified from e
                raise

        return inner()

    return wrapper


def retry_github_api(func: Callable) -> Callable:
    """
    Decorator specifically for GitHub API calls with appropriate retry logic

    Example:
        @retry_github_api
        def call_github_api():
            return repo.create_issue(...)
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        @retry_with_backoff(
            config=GITHUB_RETRY_CONFIG,
            retryable_exceptions=(RetryableError, ConnectionError, TimeoutError),
        )
        def inner():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Classify and re-raise with appropriate type
                classified = classify_github_exception(e)
                if classified is not e:
                    raise classified from e
                raise

        return inner()

    return wrapper
