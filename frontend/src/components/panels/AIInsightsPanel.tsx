/**
 * AI Insights Panel Component
 * Displays AI-generated reliability insights and recommendations
 */

import React from 'react';
import { AISummary, AIInsight } from '../../types';

interface AIInsightsPanelProps {
  summary: AISummary;
}

const INSIGHT_ICONS: Record<string, React.ReactNode> = {
  warning: (
    <svg className="w-5 h-5 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ),
  recommendation: (
    <svg className="w-5 h-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
    </svg>
  ),
  status: (
    <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ),
};

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'border-red-500 bg-red-500/10',
  warning: 'border-orange-500 bg-orange-500/10',
  info: 'border-blue-500 bg-blue-500/10',
};

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({ summary }) => {
  const healthColor = 
    summary.overall_health === 'healthy' ? 'text-green-400' :
    summary.overall_health === 'degraded' ? 'text-yellow-400' :
    'text-red-400';

  return (
    <div className="space-y-6">
      {/* Header with overall health */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold">AI Reliability Insights</h3>
            <p className="text-sm text-gray-400">
              Generated {new Date(summary.generated_at).toLocaleTimeString()}
            </p>
          </div>
        </div>
        
        <div className="text-right">
          <div className={`text-3xl font-bold ${healthColor}`}>
            {summary.overall_score.toFixed(0)}
          </div>
          <div className={`text-sm uppercase ${healthColor}`}>
            {summary.overall_health}
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <div className="bg-gray-700/50 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-400 mb-2">Executive Summary</h4>
        <p className="text-white">{summary.executive_summary}</p>
      </div>

      {/* At Risk Services */}
      {summary.services_at_risk.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-red-400 mb-2">
            Services at Risk ({summary.services_at_risk.length})
          </h4>
          <div className="flex flex-wrap gap-2">
            {summary.services_at_risk.map((service) => (
              <span
                key={service}
                className="px-2 py-1 bg-red-500/20 rounded text-sm text-red-300"
              >
                {service}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Nearest Exhaustion Warning */}
      {summary.nearest_budget_exhaustion && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-orange-400 mb-2">
            ⚠️ Nearest Budget Exhaustion
          </h4>
          <p className="text-white">
            <span className="font-semibold">{summary.nearest_budget_exhaustion.service_name}</span>
            {' '}will exhaust its error budget in{' '}
            <span className="font-semibold text-orange-400">
              {summary.nearest_budget_exhaustion.time_to_exhaustion_hours < 24
                ? `${summary.nearest_budget_exhaustion.time_to_exhaustion_hours.toFixed(1)} hours`
                : `${(summary.nearest_budget_exhaustion.time_to_exhaustion_hours / 24).toFixed(1)} days`
              }
            </span>
          </p>
        </div>
      )}

      {/* Action Items */}
      {summary.action_items.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-400 mb-3">Recommended Actions</h4>
          <ul className="space-y-2">
            {summary.action_items.map((action, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-blue-400 mt-0.5">→</span>
                <span className="text-gray-300">{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Detailed Insights */}
      <div>
        <h4 className="text-sm font-semibold text-gray-400 mb-3">Service Insights</h4>
        <div className="space-y-2 max-h-80 overflow-y-auto pr-2">
          {summary.insights
            .filter((i) => i.severity !== 'info')
            .map((insight, idx) => (
              <div
                key={idx}
                className={`
                  rounded-lg p-3 border-l-4
                  ${SEVERITY_COLORS[insight.severity] || 'border-gray-500 bg-gray-700/50'}
                `}
              >
                <div className="flex items-start gap-2">
                  {INSIGHT_ICONS[insight.insight_type] || INSIGHT_ICONS.status}
                  <div>
                    <span className="text-xs text-gray-400 uppercase">
                      {insight.service_name}
                    </span>
                    <p className="text-sm text-white mt-0.5">{insight.message}</p>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
};

export default AIInsightsPanel;
