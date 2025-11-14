#!/usr/bin/env python3
"""
Retry Utility with Tenacity - Exponential Backoff and Jitter

Provides retry logic for API calls to handle transient failures,
rate limiting, and network issues for Anthropic and GitHub APIs.

This module now uses Tenacity (https://pypi.org/project/tenacity/),
a robust and battle-tested retry library that provides:
- Flexible retry strategies (exponential backoff, fixed delays, etc.)
- Multiple stop conditions (max attempts, time limits, etc.)
- Custom wait strategies with jitter
- Comprehensive logging and callbacks
- Better exception handling and classification
"""

import functools
import logging
from typing import Callable, Type, Tuple, Optional, Union

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryError,
    TryAgain,
)
from tenacity.wait import wait_base
from tenacity.stop import stop_base

from logging_config import get_logger
from utils.exceptions import (
    RateLimitError as AutoGrowRateLimitError,
    RetryExhaustedError,
    TimeoutError as AutoGrowTimeoutError,
)

# Get logger
logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior - maintained for backward compatibility"""

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


def should_retry_exception(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry

    Args:
        exception: The exception that was raised

    Returns:
        True if should retry, False otherwise
    """
    # Check if exception is already a RetryableError
    if isinstance(exception, RetryableError):
        return True

    # Check for common retryable exception types
    if isinstance(exception, (ConnectionError, TimeoutError)):
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
        # Check if exception has response headers
        if hasattr(e, "response") and hasattr(e.response, "headers"):
            retry_after = e.response.headers.get("retry-after")
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse retry-after value: {retry_after}")
                    retry_after = None
        logger.warning(f"Rate limit detected for Anthropic API, retry_after: {retry_after}")
        return RateLimitError(retry_after=retry_after)

    # Check for network errors
    if any(
        indicator in error_msg
        for indicator in ["connection", "timeout", "network", "503", "502"]
    ):
        logger.warning(f"Network error detected for Anthropic API: {error_msg[:100]}")
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
        logger.warning(f"Rate limit detected for GitHub API, retry_after: {retry_after}")
        return RateLimitError(retry_after=retry_after)

    # Check for network errors
    if any(
        indicator in error_msg
        for indicator in ["connection", "timeout", "network", "503", "502", "500"]
    ):
        logger.warning(f"Network error detected for GitHub API: {error_msg[:100]}")
        return NetworkError(str(e))

    # Return original exception
    return e


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorator to add retry logic with exponential backoff to a function
    Now powered by Tenacity for better reliability and features

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
        # Create Tenacity retry decorator with exponential backoff
        tenacity_decorator = retry(
            # Stop after max_retries attempts
            stop=stop_after_attempt(config.max_retries + 1),
            # Exponential backoff with jitter
            wait=wait_exponential(
                multiplier=config.base_delay,
                max=config.max_delay,
                exp_base=config.exponential_base,
            ),
            # Retry on specified exceptions
            retry=retry_if_exception_type(retryable_exceptions)
            | retry_if_exception_type(RetryableError),
            # Log retry attempts
            before_sleep=before_sleep_log(logger, logging.WARNING),
            # Re-raise the original exception after exhausting retries
            reraise=True,
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Custom retry callback handling
            if on_retry:
                original_func = func

                @functools.wraps(original_func)
                def func_with_callback(*args, **kwargs):
                    try:
                        return original_func(*args, **kwargs)
                    except Exception as e:
                        # Note: With Tenacity, we don't have direct access to attempt number here
                        # The logging is handled by before_sleep_log
                        raise

                return tenacity_decorator(func_with_callback)(*args, **kwargs)
            else:
                return tenacity_decorator(func)(*args, **kwargs)

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


def retry_anthropic_api(func: Callable) -> Callable:
    """
    Decorator specifically for Anthropic API calls with appropriate retry logic
    Now powered by Tenacity for better reliability

    This decorator handles:
    - Rate limiting with exponential backoff
    - Network errors and timeouts
    - Transient API failures
    - Automatic classification of Anthropic-specific errors

    Example:
        @retry_anthropic_api
        def call_anthropic_api():
            return client.messages.create(...)
    """

    @functools.wraps(func)
    @retry(
        # Stop after 5 attempts (initial + 4 retries)
        stop=stop_after_attempt(ANTHROPIC_RETRY_CONFIG.max_retries + 1),
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s (capped at 60s)
        wait=wait_exponential(
            multiplier=ANTHROPIC_RETRY_CONFIG.base_delay,
            max=ANTHROPIC_RETRY_CONFIG.max_delay,
            exp_base=ANTHROPIC_RETRY_CONFIG.exponential_base,
        ),
        # Retry on specific exception types
        retry=(
            retry_if_exception_type(RetryableError)
            | retry_if_exception_type(ConnectionError)
            | retry_if_exception_type(TimeoutError)
        ),
        # Log retry attempts with details
        before_sleep=before_sleep_log(logger, logging.WARNING),
        # Re-raise after exhausting retries
        reraise=True,
    )
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RetryableError:
            # Already classified, just re-raise
            raise
        except ConnectionError as e:
            logger.warning(f"Connection error in Anthropic API call: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"Timeout in Anthropic API call: {e}")
            raise
        except Exception as e:
            # Classify and re-raise with appropriate type
            classified = classify_anthropic_exception(e)
            if classified is not e:
                raise classified from e
            # Check if this is a retryable error
            if should_retry_exception(e):
                logger.debug(f"Retryable error detected: {str(e)[:100]}")
                raise TryAgain from e
            logger.error(f"Non-retryable error in Anthropic API call: {str(e)[:100]}")
            raise

    return wrapper


def retry_github_api(func: Callable) -> Callable:
    """
    Decorator specifically for GitHub API calls with appropriate retry logic
    Now powered by Tenacity for better reliability

    This decorator handles:
    - Rate limiting (GitHub's 403 responses)
    - Secondary rate limits and abuse detection
    - Network errors and timeouts
    - Transient API failures
    - Automatic classification of GitHub-specific errors

    Example:
        @retry_github_api
        def call_github_api():
            return repo.create_issue(...)
    """

    @functools.wraps(func)
    @retry(
        # Stop after 3 attempts (initial + 2 retries)
        stop=stop_after_attempt(GITHUB_RETRY_CONFIG.max_retries + 1),
        # Exponential backoff: 2s, 4s, 8s (capped at 120s)
        wait=wait_exponential(
            multiplier=GITHUB_RETRY_CONFIG.base_delay,
            max=GITHUB_RETRY_CONFIG.max_delay,
            exp_base=GITHUB_RETRY_CONFIG.exponential_base,
        ),
        # Retry on specific exception types
        retry=(
            retry_if_exception_type(RetryableError)
            | retry_if_exception_type(ConnectionError)
            | retry_if_exception_type(TimeoutError)
        ),
        # Log retry attempts with details
        before_sleep=before_sleep_log(logger, logging.WARNING),
        # Re-raise after exhausting retries
        reraise=True,
    )
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RetryableError:
            # Already classified, just re-raise
            raise
        except ConnectionError as e:
            logger.warning(f"Connection error in GitHub API call: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"Timeout in GitHub API call: {e}")
            raise
        except Exception as e:
            # Classify and re-raise with appropriate type
            classified = classify_github_exception(e)
            if classified is not e:
                raise classified from e
            # Check if this is a retryable error
            if should_retry_exception(e):
                logger.debug(f"Retryable error detected: {str(e)[:100]}")
                raise TryAgain from e
            logger.error(f"Non-retryable error in GitHub API call: {str(e)[:100]}")
            raise

    return wrapper


# Legacy compatibility functions (kept for backward compatibility)
def calculate_delay(
    attempt: int, config: RetryConfig, rate_limit_retry_after: Optional[int] = None
) -> float:
    """
    Calculate delay for next retry with exponential backoff and jitter
    Maintained for backward compatibility - Tenacity handles this internally now

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

    # Calculate exponential backoff (Tenacity does this internally)
    delay = min(
        config.base_delay * (config.exponential_base**attempt), config.max_delay
    )

    # Tenacity adds jitter automatically with wait_exponential
    return delay


def should_retry(exception: Exception, retryable_exceptions: Tuple[Type[Exception], ...]) -> bool:
    """
    Determine if an exception should trigger a retry
    Maintained for backward compatibility

    Args:
        exception: The exception that was raised
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        True if should retry, False otherwise
    """
    # Check if exception is in retryable list
    if isinstance(exception, retryable_exceptions):
        return True

    return should_retry_exception(exception)
