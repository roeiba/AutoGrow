import { useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * useBilling hook for managing subscriptions and usage
 * Handles fetching usage stats, subscription info, and upgrades
 */
export function useBilling(token) {
  const [usage, setUsage] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch usage and subscription data
  const fetchBillingData = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      // Fetch usage
      const usageResponse = await fetch(`${API_URL}/api/v1/billing/usage`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (usageResponse.ok) {
        const usageData = await usageResponse.json();
        setUsage(usageData);
      }

      // Fetch subscription
      const subResponse = await fetch(`${API_URL}/api/v1/billing/subscription`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (subResponse.ok) {
        const subData = await subResponse.json();
        setSubscription(subData);
      }

      setError(null);
    } catch (err) {
      console.error('Failed to fetch billing data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch on mount and when token changes
  useEffect(() => {
    fetchBillingData();
  }, [token]);

  const createCheckoutSession = async (tier, successUrl, cancelUrl) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/billing/checkout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          tier,
          success_url: successUrl,
          cancel_url: cancelUrl
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create checkout session');
      }

      const data = await response.json();
      return data.checkout_url;
    } catch (err) {
      console.error('Failed to create checkout session:', err);
      throw err;
    }
  };

  const cancelSubscription = async (immediate = false) => {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/billing/cancel?immediate=${immediate}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to cancel subscription');
      }

      // Refresh billing data
      await fetchBillingData();
      return true;
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      throw err;
    }
  };

  const refreshBillingData = () => {
    return fetchBillingData();
  };

  // Helper to check if upgrade prompt should show
  const shouldShowUpgradePrompt = () => {
    if (!usage || !subscription) return false;
    return usage.quota_warning || usage.quota_exceeded;
  };

  return {
    usage,
    subscription,
    loading,
    error,
    createCheckoutSession,
    cancelSubscription,
    refreshBillingData,
    shouldShowUpgradePrompt
  };
}
