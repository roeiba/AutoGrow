import React from 'react';
import { Zap, TrendingUp, CheckCircle } from 'lucide-react';

/**
 * UpgradePrompt component displays when users reach 80% of quota or exceed it
 * Provides clear upgrade paths and pricing information
 */
export function UpgradePrompt({ currentTier, usagePercentage, quotaExceeded, onUpgrade }) {
  // Don't show for enterprise users
  if (currentTier === 'enterprise') return null;

  // Only show if warning threshold reached or quota exceeded
  if (usagePercentage < 80 && !quotaExceeded) return null;

  const targetTier = currentTier === 'free' ? 'pro' : 'enterprise';
  const targetTierName = targetTier === 'pro' ? 'Pro' : 'Enterprise';

  const benefits = {
    pro: [
      '1,000 AI operations per month (10x more)',
      'Up to 10 active projects',
      'Priority support',
      'Advanced features',
      'Analytics dashboard'
    ],
    enterprise: [
      'Unlimited AI operations',
      'Unlimited projects',
      'Dedicated support team',
      'Custom integrations',
      'SLA guarantee',
      'Custom workflows'
    ]
  };

  const pricing = {
    pro: '$49/month',
    enterprise: 'Custom pricing'
  };

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg shadow-md border border-blue-200 p-6 mb-6">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="flex-shrink-0">
          <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
            {quotaExceeded ? (
              <Zap className="w-6 h-6 text-white" />
            ) : (
              <TrendingUp className="w-6 h-6 text-white" />
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900 mb-2">
            {quotaExceeded ? 'Upgrade Required' : 'Time to Scale Up?'}
          </h3>

          <p className="text-gray-700 mb-4">
            {quotaExceeded ? (
              <>
                You've reached your {currentTier} plan limit. Upgrade to {targetTierName} to continue
                building amazing projects with SeedGPT.
              </>
            ) : (
              <>
                You've used {Math.round(usagePercentage)}% of your monthly quota.
                Upgrade to {targetTierName} for more capacity and advanced features.
              </>
            )}
          </p>

          {/* Benefits */}
          <div className="bg-white rounded-lg p-4 mb-4">
            <h4 className="font-semibold text-gray-900 mb-3">
              {targetTierName} Plan Benefits:
            </h4>
            <ul className="space-y-2">
              {benefits[targetTier].map((benefit, index) => (
                <li key={index} className="flex items-start gap-2">
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-gray-700">{benefit}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Pricing and CTA */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold text-gray-900">{pricing[targetTier]}</p>
              {targetTier === 'pro' && (
                <p className="text-sm text-gray-600">Billed monthly</p>
              )}
            </div>
            <button
              onClick={() => onUpgrade(targetTier)}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                quotaExceeded
                  ? 'bg-red-600 hover:bg-red-700 text-white shadow-lg hover:shadow-xl'
                  : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg'
              }`}
            >
              {quotaExceeded ? 'Upgrade Now' : `Upgrade to ${targetTierName}`}
            </button>
          </div>

          {targetTier === 'enterprise' && (
            <p className="text-xs text-gray-600 mt-3">
              Contact our sales team to discuss custom pricing and requirements
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
