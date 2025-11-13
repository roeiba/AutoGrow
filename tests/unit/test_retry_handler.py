#!/usr/bin/env python3
"""
Unit tests for retry handler with exponential backoff and jitter
"""

import time
import pytest
from unittest.mock import Mock, patch
from src.utils.retry_handler import (
    calculate_backoff_delay,
    retry_with_backoff,
    retry_anthropic_api,
    retry_github_api,
    RetryableAPICall,
    RetryConfig,
)


class TestBackoffCalculation:
    """Test backoff delay calculation"""

    def test_exponential_growth(self):
        """Test that delays grow exponentially"""
        base_delay = 1.0
        multiplier = 2.0
        max_delay = 100.0

        # First attempt (attempt 0)
        delay_0 = calculate_backoff_delay(0, base_delay, max_delay, multiplier, 0.0)
        assert delay_0 == base_delay

        # Second attempt (attempt 1)
        delay_1 = calculate_backoff_delay(1, base_delay, max_delay, multiplier, 0.0)
        assert delay_1 == base_delay * multiplier

        # Third attempt (attempt 2)
        delay_2 = calculate_backoff_delay(2, base_delay, max_delay, multiplier, 0.0)
        assert delay_2 == base_delay * (multiplier ** 2)

    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay"""
        base_delay = 1.0
        multiplier = 2.0
        max_delay = 10.0

        # Large attempt number should still be capped
        delay = calculate_backoff_delay(100, base_delay, max_delay, multiplier, 0.0)
        assert delay == max_delay

    def test_jitter_range(self):
        """Test that jitter is within expected range"""
        base_delay = 10.0
        multiplier = 2.0
        max_delay = 100.0
        jitter_range = 0.2  # +/- 20%

        # Run multiple times to check jitter variation
        delays = []
        for _ in range(20):
            delay = calculate_backoff_delay(
                0, base_delay, max_delay, multiplier, jitter_range
            )
            delays.append(delay)

        # Should have some variation due to jitter
        assert len(set(delays)) > 1

        # All delays should be within jitter range of base delay
        min_expected = base_delay * (1 - jitter_range)
        max_expected = base_delay * (1 + jitter_range)
        for delay in delays:
            assert min_expected <= delay <= max_expected


class TestRetryDecorator:
    """Test retry decorator functionality"""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't retry"""
        mock_func = Mock(return_value="success")

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_on_exception(self):
        """Test that function retries on exception"""
        mock_func = Mock(side_effect=[Exception("error"), Exception("error"), "success"])

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries"""
        mock_func = Mock(side_effect=Exception("persistent error"))

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def test_func():
            return mock_func()

        with pytest.raises(Exception, match="persistent error"):
            test_func()

        assert mock_func.call_count == 3  # Initial + 2 retries

    def test_specific_exception_types(self):
        """Test that only specific exceptions trigger retry"""

        class RetryableError(Exception):
            pass

        class NonRetryableError(Exception):
            pass

        mock_func = Mock(side_effect=NonRetryableError("won't retry"))

        @retry_with_backoff(
            max_retries=3, base_delay=0.01, exceptions=(RetryableError,)
        )
        def test_func():
            return mock_func()

        # Should not retry on NonRetryableError
        with pytest.raises(NonRetryableError):
            test_func()

        assert mock_func.call_count == 1  # No retries

    def test_rate_limit_exceptions(self):
        """Test that rate limit exceptions use longer delays"""

        class RateLimitError(Exception):
            pass

        mock_func = Mock(side_effect=[RateLimitError("rate limited"), "success"])

        with patch("time.sleep") as mock_sleep:

            @retry_with_backoff(
                max_retries=3,
                base_delay=1.0,
                rate_limit_exceptions=(RateLimitError,),
            )
            def test_func():
                return mock_func()

            result = test_func()
            assert result == "success"
            assert mock_func.call_count == 2

            # Verify sleep was called (rate limit uses longer delay)
            assert mock_sleep.call_count == 1


class TestAnthropicRetryDecorator:
    """Test Anthropic-specific retry decorator"""

    @patch("src.utils.retry_handler.Anthropic")
    def test_anthropic_decorator_retries(self, mock_anthropic):
        """Test that Anthropic decorator handles API errors"""
        from anthropic import APIConnectionError

        mock_func = Mock(side_effect=[APIConnectionError("connection failed"), "success"])

        @retry_anthropic_api
        def test_func():
            return mock_func()

        with patch("time.sleep"):
            result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2


class TestGitHubRetryDecorator:
    """Test GitHub-specific retry decorator"""

    @patch("src.utils.retry_handler.GithubException")
    def test_github_decorator_retries(self, mock_github_exc):
        """Test that GitHub decorator handles API errors"""
        from github import GithubException

        mock_func = Mock(
            side_effect=[
                GithubException(500, "server error", headers={}),
                "success",
            ]
        )

        @retry_github_api
        def test_func():
            return mock_func()

        with patch("time.sleep"):
            result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2


class TestRetryableAPICall:
    """Test RetryableAPICall context manager"""

    def test_context_manager_success(self):
        """Test successful execution with context manager"""
        with RetryableAPICall(max_retries=3, base_delay=0.01) as retry:
            result = retry.execute(lambda: "success")
            assert result == "success"

    def test_context_manager_retry(self):
        """Test retry with context manager"""
        mock_func = Mock(side_effect=[Exception("error"), "success"])

        with patch("time.sleep"):
            with RetryableAPICall(max_retries=3, base_delay=0.01) as retry:
                result = retry.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 2

    def test_context_manager_max_retries(self):
        """Test max retries with context manager"""
        mock_func = Mock(side_effect=Exception("persistent error"))

        with pytest.raises(Exception, match="persistent error"):
            with patch("time.sleep"):
                with RetryableAPICall(max_retries=2, base_delay=0.01) as retry:
                    retry.execute(mock_func)

        assert mock_func.call_count == 3


class TestRetryConfig:
    """Test retry configuration constants"""

    def test_anthropic_config(self):
        """Test Anthropic retry configuration"""
        assert RetryConfig.ANTHROPIC_MAX_RETRIES == 5
        assert RetryConfig.ANTHROPIC_BASE_DELAY == 1.0
        assert RetryConfig.ANTHROPIC_MAX_DELAY == 60.0
        assert RetryConfig.ANTHROPIC_BACKOFF_MULTIPLIER == 2.0
        assert 0 <= RetryConfig.ANTHROPIC_JITTER_RANGE <= 1.0

    def test_github_config(self):
        """Test GitHub retry configuration"""
        assert RetryConfig.GITHUB_MAX_RETRIES == 5
        assert RetryConfig.GITHUB_BASE_DELAY == 2.0
        assert RetryConfig.GITHUB_MAX_DELAY == 120.0
        assert RetryConfig.GITHUB_BACKOFF_MULTIPLIER == 2.0
        assert 0 <= RetryConfig.GITHUB_JITTER_RANGE <= 1.0

    def test_network_config(self):
        """Test network retry configuration"""
        assert RetryConfig.NETWORK_MAX_RETRIES == 3
        assert RetryConfig.NETWORK_BASE_DELAY == 0.5
        assert RetryConfig.NETWORK_MAX_DELAY == 30.0
        assert RetryConfig.NETWORK_BACKOFF_MULTIPLIER == 2.0
        assert 0 <= RetryConfig.NETWORK_JITTER_RANGE <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
