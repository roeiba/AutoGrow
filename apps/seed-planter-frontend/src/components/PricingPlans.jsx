import React from 'react';
import { Check } from 'lucide-react';

/**
 * PricingPlans component displays all available pricing tiers
 * Used in the upgrade flow and pricing page
 */
export function PricingPlans({ currentTier, onSelectPlan }) {
  const plans = [
    {
      name: 'Free',
      tier: 'free',
      price: '$0',
      period: 'forever',
      description: 'Perfect for trying out SeedGPT',
      features: [
        '100 AI operations per month',
        '1 active project',
        'Community support',
        'Basic features',
        'GitHub integration'
      ],
      cta: 'Current Plan',
      highlighted: false
    },
    {
      name: 'Pro',
      tier: 'pro',
      price: '$49',
      period: 'per month',
      description: 'For serious developers and small teams',
      features: [
        '1,000 AI operations per month',
        'Up to 10 active projects',
        'Priority support',
        'Advanced features',
        'Analytics dashboard',
        'Custom workflows',
        'API access'
      ],
      cta: 'Upgrade to Pro',
      highlighted: true
    },
    {
      name: 'Enterprise',
      tier: 'enterprise',
      price: 'Custom',
      period: 'pricing',
      description: 'For organizations with advanced needs',
      features: [
        'Unlimited AI operations',
        'Unlimited projects',
        'Dedicated support team',
        'Custom integrations',
        'SLA guarantee',
        'Custom workflows',
        'On-premise deployment',
        'Advanced security'
      ],
      cta: 'Contact Sales',
      highlighted: false
    }
  ];

  const tierOrder = { free: 0, pro: 1, enterprise: 2 };
  const currentTierLevel = tierOrder[currentTier] || 0;

  return (
    <div className="py-12">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold text-gray-900 mb-4">Choose Your Plan</h2>
        <p className="text-lg text-gray-600">
          Scale your AI-powered development with flexible pricing
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto">
        {plans.map((plan) => {
          const isCurrentPlan = plan.tier === currentTier;
          const canUpgrade = tierOrder[plan.tier] > currentTierLevel;
          const isDowngrade = tierOrder[plan.tier] < currentTierLevel;

          return (
            <div
              key={plan.tier}
              className={`relative rounded-2xl p-8 ${
                plan.highlighted
                  ? 'bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-500 shadow-xl scale-105'
                  : 'bg-white border border-gray-200 shadow-md'
              }`}
            >
              {plan.highlighted && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white text-xs font-bold px-4 py-1 rounded-full">
                    MOST POPULAR
                  </span>
                </div>
              )}

              {/* Plan header */}
              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                <div className="mb-2">
                  <span className="text-4xl font-bold text-gray-900">{plan.price}</span>
                  {plan.tier !== 'enterprise' && (
                    <span className="text-gray-600 ml-2">/ {plan.period}</span>
                  )}
                </div>
                <p className="text-sm text-gray-600">{plan.description}</p>
              </div>

              {/* Features list */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA button */}
              <button
                onClick={() => onSelectPlan(plan.tier)}
                disabled={isCurrentPlan || isDowngrade}
                className={`w-full py-3 rounded-lg font-semibold transition-all ${
                  isCurrentPlan
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : isDowngrade
                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                    : plan.highlighted
                    ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg hover:shadow-xl'
                    : 'bg-gray-900 hover:bg-gray-800 text-white shadow-md hover:shadow-lg'
                }`}
              >
                {isCurrentPlan
                  ? 'Current Plan'
                  : isDowngrade
                  ? 'Not Available'
                  : plan.cta}
              </button>

              {isCurrentPlan && (
                <p className="text-center text-xs text-gray-600 mt-2">
                  You're currently on this plan
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* FAQ or additional info */}
      <div className="text-center mt-12 text-sm text-gray-600">
        <p>All plans include GitHub integration and automatic deployments</p>
        <p className="mt-2">Need help choosing? Contact us at support@seedgpt.com</p>
      </div>
    </div>
  );
}
