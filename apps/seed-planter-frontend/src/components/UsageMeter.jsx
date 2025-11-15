import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * UsageMeter component displays the user's current usage against their quota
 * Shows a warning at 80% and error state when quota is exceeded
 */
export function UsageMeter({ usage, limits, tier, usagePercentage, quotaWarning, quotaExceeded }) {
  // Determine bar color based on usage
  const getBarColor = () => {
    if (quotaExceeded) return 'bg-red-500';
    if (quotaWarning) return 'bg-yellow-500';
    return 'bg-blue-500';
  };

  // Determine text color based on usage
  const getTextColor = () => {
    if (quotaExceeded) return 'text-red-700';
    if (quotaWarning) return 'text-yellow-700';
    return 'text-gray-700';
  };

  const isUnlimited = limits.is_unlimited;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Usage This Month</h3>
        <span className="text-sm font-medium text-gray-500 uppercase">{tier} Plan</span>
      </div>

      {!isUnlimited ? (
        <>
          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className={`text-sm font-medium ${getTextColor()}`}>
                {usage.ai_operations} / {limits.monthly_ai_ops_limit} AI Operations
              </span>
              <span className={`text-sm font-medium ${getTextColor()}`}>
                {Math.round(usagePercentage)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${getBarColor()}`}
                style={{ width: `${Math.min(usagePercentage, 100)}%` }}
              />
            </div>
          </div>

          {/* Warning messages */}
          {quotaExceeded && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Quota Exceeded</p>
                <p className="text-sm text-red-700 mt-1">
                  You've reached your {tier} plan limit. Upgrade to continue using SeedGPT.
                </p>
              </div>
            </div>
          )}

          {quotaWarning && !quotaExceeded && (
            <div className="flex items-start gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-yellow-800">Usage Warning</p>
                <p className="text-sm text-yellow-700 mt-1">
                  You've used {Math.round(usagePercentage)}% of your monthly quota. Consider upgrading to avoid interruptions.
                </p>
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-6">
          <p className="text-lg font-semibold text-gray-900">Unlimited Usage</p>
          <p className="text-sm text-gray-600 mt-2">
            Your Enterprise plan includes unlimited AI operations
          </p>
          <div className="mt-4 text-sm text-gray-500">
            <p>{usage.ai_operations} operations this month</p>
          </div>
        </div>
      )}

      {/* Detailed usage breakdown */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Usage Breakdown</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-gray-500">Projects Created</p>
            <p className="text-lg font-semibold text-gray-900">{usage.projects_created}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Issues Generated</p>
            <p className="text-lg font-semibold text-gray-900">{usage.issues_generated}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">PRs Created</p>
            <p className="text-lg font-semibold text-gray-900">{usage.prs_created}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">API Calls</p>
            <p className="text-lg font-semibold text-gray-900">{usage.api_calls}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
