#!/usr/bin/env python3
"""
Retry Handler with Exponential Backoff and Jitter

Provides robust retry logic for API calls to prevent cascading failures
from network issues and rate limiting.
"""

import time
import random
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type, Union

# Setup logger
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""

    # Anthropic API specific settings
    ANTHROPIC_MAX_RETRIES = 5
    ANTHROPIC_BASE_DELAY = 1.0  # Start with 1 second
    ANTHROPIC_MAX_DELAY = 60.0  # Cap at 60 seconds
    ANTHROPIC_BACKOFF_MULTIPLIER = 2.0
    ANTHROPIC_JITTER_RANGE = 0.1  # +/- 10% jitter

    # GitHub API specific settings
    GITHUB_MAX_RETRIES = 5
    GITHUB_BASE_DELAY = 2.0  # Start with 2 seconds
    GITHUB_MAX_DELAY = 120.0  # Cap at 120 seconds
    GITHUB_BACKOFF_MULTIPLIER = 2.0
    GITHUB_JITTER_RANGE = 0.15  # +/- 15% jitter

    # General network error settings
    NETWORK_MAX_RETRIES = 3
    NETWORK_BASE_DELAY = 0.5
    NETWORK_MAX_DELAY = 30.0
    NETWORK_BACKOFF_MULTIPLIER = 2.0
    NETWORK_JITTER_RANGE = 0.2  # +/- 20% jitter


def calculate_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    multiplier: float,
    jitter_range: float,
) -> float:
    """
    Calculate delay with exponential backoff and jitter

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Exponential backoff multiplier
        jitter_range: Percentage of jitter to apply (0.0 to 1.0)

    Returns:
        Delay in seconds with jitter applied
    """
    # Exponential backoff: base_delay * (multiplier ^ attempt)
    delay = min(base_delay * (multiplier**attempt), max_delay)

    # Add jitter to prevent thundering herd
    jitter = delay * jitter_range * (2 * random.random() - 1)
    final_delay = max(0, delay + jitter)

    return final_delay


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    jitter_range: float = 0.1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    rate_limit_exceptions: Tuple[Type[Exception], ...] = (),
    log_errors: bool = True,
):
    """
    Decorator for retrying functions with exponential backoff and jitter

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        multiplier: Exponential backoff multiplier
        jitter_range: Percentage of jitter (0.0 to 1.0)
        exceptions: Tuple of exceptions to catch and retry
        rate_limit_exceptions: Tuple of rate limit specific exceptions
        log_errors: Whether to log errors

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except rate_limit_exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        if log_errors:
                            logger.error(
                                f"Rate limit exceeded after {max_retries} retries in {func.__name__}: {e}"
                            )
                        raise

                    # For rate limits, use longer delays
                    delay = calculate_backoff_delay(
                        attempt + 1,  # Use longer delays for rate limits
                        base_delay * 2,
                        max_delay,
                        multiplier,
                        jitter_range,
                    )

                    if log_errors:
                        logger.warning(
                            f"Rate limited in {func.__name__} (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {delay:.2f}s... Error: {e}"
                        )

                    time.sleep(delay)

                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        if log_errors:
                            logger.error(
                                f"Failed after {max_retries} retries in {func.__name__}: {e}"
                            )
                        raise

                    delay = calculate_backoff_delay(
                        attempt, base_delay, max_delay, multiplier, jitter_range
                    )

                    if log_errors:
                        logger.warning(
                            f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {delay:.2f}s... Error: {e}"
                        )

                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_anthropic_api(func: Callable) -> Callable:
    """
    Decorator specifically for Anthropic API calls

    Handles common Anthropic API errors with appropriate retry logic
    """
    # Import here to avoid circular dependencies
    try:
        from anthropic import (
            APIError,
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )

        anthropic_exceptions = (
            APIConnectionError,
            APITimeoutError,
            InternalServerError,
        )
        rate_limit_exceptions = (RateLimitError,)
    except ImportError:
        # Fallback if anthropic not installed
        anthropic_exceptions = (Exception,)
        rate_limit_exceptions = ()
        logger.warning("Anthropic SDK not found, using generic exception handling")

    return retry_with_backoff(
        max_retries=RetryConfig.ANTHROPIC_MAX_RETRIES,
        base_delay=RetryConfig.ANTHROPIC_BASE_DELAY,
        max_delay=RetryConfig.ANTHROPIC_MAX_DELAY,
        multiplier=RetryConfig.ANTHROPIC_BACKOFF_MULTIPLIER,
        jitter_range=RetryConfig.ANTHROPIC_JITTER_RANGE,
        exceptions=anthropic_exceptions,
        rate_limit_exceptions=rate_limit_exceptions,
        log_errors=True,
    )(func)


def retry_github_api(func: Callable) -> Callable:
    """
    Decorator specifically for GitHub API calls (via PyGithub)

    Handles common GitHub API errors with appropriate retry logic
    """
    # Import here to avoid circular dependencies
    try:
        from github import GithubException, RateLimitExceededException

        github_exceptions = (GithubException,)
        rate_limit_exceptions = (RateLimitExceededException,)
    except ImportError:
        # Fallback if PyGithub not installed
        github_exceptions = (Exception,)
        rate_limit_exceptions = ()
        logger.warning("PyGithub not found, using generic exception handling")

    return retry_with_backoff(
        max_retries=RetryConfig.GITHUB_MAX_RETRIES,
        base_delay=RetryConfig.GITHUB_BASE_DELAY,
        max_delay=RetryConfig.GITHUB_MAX_DELAY,
        multiplier=RetryConfig.GITHUB_BACKOFF_MULTIPLIER,
        jitter_range=RetryConfig.GITHUB_JITTER_RANGE,
        exceptions=github_exceptions,
        rate_limit_exceptions=rate_limit_exceptions,
        log_errors=True,
    )(func)


def retry_network_call(func: Callable) -> Callable:
    """
    Decorator for general network calls

    Handles common network errors with retry logic
    """
    import requests.exceptions

    network_exceptions = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        OSError,  # For low-level network errors
    )

    return retry_with_backoff(
        max_retries=RetryConfig.NETWORK_MAX_RETRIES,
        base_delay=RetryConfig.NETWORK_BASE_DELAY,
        max_delay=RetryConfig.NETWORK_MAX_DELAY,
        multiplier=RetryConfig.NETWORK_BACKOFF_MULTIPLIER,
        jitter_range=RetryConfig.NETWORK_JITTER_RANGE,
        exceptions=network_exceptions,
        log_errors=True,
    )(func)


class RetryableAPICall:
    """
    Context manager for retryable API calls

    Useful when you need more control over the retry logic
    or want to wrap multiple operations together.

    Example:
        with RetryableAPICall(max_retries=3) as retry:
            result = retry.execute(lambda: api_client.some_call())
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter_range: float = 0.1,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter_range = jitter_range

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, func: Callable, *args, **kwargs):
        """Execute a function with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt == self.max_retries:
                    logger.error(
                        f"Failed after {self.max_retries} retries: {e}"
                    )
                    raise

                delay = calculate_backoff_delay(
                    attempt,
                    self.base_delay,
                    self.max_delay,
                    self.multiplier,
                    self.jitter_range,
                )

                logger.warning(
                    f"Error (attempt {attempt + 1}/{self.max_retries}). "
                    f"Retrying in {delay:.2f}s... Error: {e}"
                )

                time.sleep(delay)

        if last_exception:
            raise last_exception
