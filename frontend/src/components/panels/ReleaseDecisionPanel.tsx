/**
 * Release Decision Panel Component
 * Allows users to check deployment eligibility and view gate decision
 */

import React, { useState } from 'react';
import { useReleaseCheck } from '../../hooks/useApi';
import { ReleaseCheckResponse, RiskLevel } from '../../types';
import RiskBadge from '../common/RiskBadge';
import { formatBurnRate, formatDuration, formatPercentage } from '../../utils/helpers';

interface ReleaseDecisionPanelProps {
  defaultService?: string;
}

export const ReleaseDecisionPanel: React.FC<ReleaseDecisionPanelProps> = ({
  defaultService = '',
}) => {
  const [serviceName, setServiceName] = useState(defaultService);
  const [version, setVersion] = useState('');
  const [override, setOverride] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const [result, setResult] = useState<ReleaseCheckResponse | null>(null);

  const releaseCheck = useReleaseCheck();

  const handleCheck = async () => {
    if (!serviceName.trim()) return;

    try {
      const response = await releaseCheck.mutateAsync({
        service_name: serviceName.trim(),
        deployment_id: `deploy-${Date.now()}`,
        version: version.trim() || undefined,
        requested_by: 'user@example.com',
        override,
        override_reason: override ? overrideReason : undefined,
      });
      setResult(response);
    } catch (error) {
      console.error('Release check failed:', error);
    }
  };

  const handleReset = () => {
    setResult(null);
    setOverride(false);
    setOverrideReason('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-600 to-blue-600 flex items-center justify-center">
          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold">Release Gate</h3>
          <p className="text-sm text-gray-400">Check deployment eligibility</p>
        </div>
      </div>

      {!result ? (
        /* Input Form */
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Service Name</label>
            <input
              type="text"
              value={serviceName}
              onChange={(e) => setServiceName(e.target.value)}
              placeholder="e.g., api-gateway"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">Version (optional)</label>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="e.g., v2.1.0"
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Override toggle */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setOverride(!override)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                override ? 'bg-orange-500' : 'bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  override ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className="text-sm text-gray-400">Override (force deployment)</span>
          </div>

          {override && (
            <div>
              <label className="block text-sm text-orange-400 mb-1">Override Reason (required)</label>
              <textarea
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Explain why you're overriding the gate..."
                className="w-full px-3 py-2 bg-gray-700 border border-orange-500/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-orange-500"
                rows={2}
              />
            </div>
          )}

          <button
            onClick={handleCheck}
            disabled={!serviceName.trim() || releaseCheck.isLoading || (override && !overrideReason.trim())}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {releaseCheck.isLoading ? (
              <>
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Checking...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Start Deployment Check
              </>
            )}
          </button>
        </div>
      ) : (
        /* Result Display */
        <div className="space-y-4">
          {/* Decision Banner */}
          <div
            className={`p-4 rounded-lg border-2 ${
              result.allowed
                ? 'bg-green-500/10 border-green-500'
                : 'bg-red-500/10 border-red-500'
            }`}
          >
            <div className="flex items-center gap-3">
              {result.allowed ? (
                <svg className="w-8 h-8 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              <div>
                <h4 className={`text-lg font-bold ${result.allowed ? 'text-green-400' : 'text-red-400'}`}>
                  {result.allowed ? 'DEPLOYMENT ALLOWED' : 'DEPLOYMENT BLOCKED'}
                </h4>
                <p className="text-sm text-gray-300">{result.reason}</p>
              </div>
            </div>
          </div>

          {/* Context Info */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-700/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Risk Level</span>
              <div className="mt-1">
                <RiskBadge risk={result.current_risk_level} />
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Burn Rate</span>
              <div className="text-xl font-bold text-white mt-1">
                {formatBurnRate(result.current_burn_rate)}
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Budget Remaining</span>
              <div className="text-xl font-bold text-white mt-1">
                {formatPercentage(result.error_budget_remaining)}
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-3">
              <span className="text-xs text-gray-400">Time to Exhaustion</span>
              <div className="text-xl font-bold text-white mt-1">
                {formatDuration(result.time_to_exhaustion_hours)}
              </div>
            </div>
          </div>

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <div>
              <h5 className="text-sm font-semibold text-gray-400 mb-2">Recommendations</h5>
              <ul className="space-y-1">
                {result.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-300">
                    <span className="text-blue-400">•</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Reset Button */}
          <button
            onClick={handleReset}
            className="w-full py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            Check Another Deployment
          </button>
        </div>
      )}
    </div>
  );
};

export default ReleaseDecisionPanel;
