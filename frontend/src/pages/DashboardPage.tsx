/**
 * Executive Overview Page
 * Main dashboard with platform-wide reliability status
 */

import React from 'react';
import { useExecutiveOverview, useAISummary, useAllBurnRates, useHeatmap, useAlertFeed } from '../hooks/useApi';
import StatCard from '../components/common/StatCard';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import RiskHeatmap from '../components/charts/RiskHeatmap';
import BudgetGauge from '../components/charts/BudgetGauge';
import AIInsightsPanel from '../components/panels/AIInsightsPanel';
import AlertFeedPanel from '../components/panels/AlertFeedPanel';
import ReleaseDecisionPanel from '../components/panels/ReleaseDecisionPanel';
import { formatDuration, formatPercentage, formatBurnRate, RISK_COLORS } from '../utils/helpers';
import { RiskLevel, BurnRateComputation } from '../types';

const DashboardPage: React.FC = () => {
  const { data: overview, isLoading: overviewLoading } = useExecutiveOverview();
  const { data: summary, isLoading: summaryLoading } = useAISummary();
  const { data: burnRates, isLoading: burnLoading } = useAllBurnRates();
  const { data: heatmap, isLoading: heatmapLoading } = useHeatmap();
  const { data: alertFeed, isLoading: alertsLoading } = useAlertFeed();

  if (overviewLoading || summaryLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="lg" message="Loading dashboard..." />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Reliability Dashboard</h1>
          <p className="text-gray-400">Platform-wide SLO and error budget status</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            Last updated: {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Key Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          label="Total Services"
          value={overview?.total_services || 0}
          color="default"
        />
        <StatCard
          label="Meeting SLO"
          value={overview?.services_meeting_slo || 0}
          subtitle={`of ${overview?.total_services || 0}`}
          color="success"
        />
        <StatCard
          label="At Risk"
          value={overview?.services_at_risk || 0}
          color={overview?.services_at_risk ? 'danger' : 'default'}
        />
        <StatCard
          label="Global Compliance"
          value={`${overview?.global_compliance_score?.toFixed(1) || 100}%`}
          color={
            (overview?.global_compliance_score || 100) >= 99 ? 'success' :
            (overview?.global_compliance_score || 100) >= 95 ? 'warning' : 'danger'
          }
        />
        <StatCard
          label="Active Alerts"
          value={overview?.active_alerts || 0}
          subtitle={`${overview?.critical_alerts || 0} critical`}
          color={overview?.critical_alerts ? 'danger' : 'default'}
        />
        <StatCard
          label="Avg Budget"
          value={formatPercentage(overview?.average_budget_remaining || 100)}
          color={
            (overview?.average_budget_remaining || 100) >= 70 ? 'success' :
            (overview?.average_budget_remaining || 100) >= 40 ? 'warning' : 'danger'
          }
        />
      </div>

      {/* Nearest Exhaustion Warning */}
      {overview?.nearest_exhaustion && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <span className="font-semibold text-orange-400">Budget Exhaustion Warning</span>
              <p className="text-sm text-gray-300">
                <span className="font-semibold">{overview.nearest_exhaustion.service_name}</span>
                {' '}will exhaust error budget in{' '}
                <span className="font-semibold text-orange-400">
                  {formatDuration(overview.nearest_exhaustion.time_to_exhaustion_hours)}
                </span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Services Status */}
        <div className="lg:col-span-2 space-y-6">
          {/* Risk Distribution */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Risk Distribution</h2>
            <div className="grid grid-cols-4 gap-4">
              {(['safe', 'observe', 'danger', 'freeze'] as RiskLevel[]).map((risk) => (
                <div
                  key={risk}
                  className="text-center p-4 rounded-lg"
                  style={{ backgroundColor: `${RISK_COLORS[risk]}20` }}
                >
                  <div
                    className="text-3xl font-bold"
                    style={{ color: RISK_COLORS[risk] }}
                  >
                    {overview?.risk_distribution?.[risk] || 0}
                  </div>
                  <div className="text-sm text-gray-400 uppercase mt-1">{risk}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Services Table */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Service Status</h2>
            {burnLoading ? (
              <LoadingSpinner message="Loading services..." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-gray-400 text-sm border-b border-gray-700">
                      <th className="pb-3">Service</th>
                      <th className="pb-3">Risk</th>
                      <th className="pb-3">Burn Rate</th>
                      <th className="pb-3">Budget</th>
                    </tr>
                  </thead>
                  <tbody>
                    {burnRates?.map((burn: BurnRateComputation) => (
                      <tr
                        key={burn.service_id}
                        className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors cursor-pointer"
                      >
                        <td className="py-3">
                          <span className="font-medium">{burn.service_name}</span>
                        </td>
                        <td className="py-3">
                          <RiskBadge risk={burn.risk_level} size="sm" />
                        </td>
                        <td className="py-3">
                          <span className={
                            burn.burn_rate > 2 ? 'text-red-400' :
                            burn.burn_rate > 1.5 ? 'text-orange-400' :
                            burn.burn_rate > 1 ? 'text-yellow-400' :
                            'text-green-400'
                          }>
                            {formatBurnRate(burn.burn_rate)}
                          </span>
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${burn.error_budget_remaining}%`,
                                  backgroundColor:
                                    burn.error_budget_remaining > 70 ? RISK_COLORS.safe :
                                    burn.error_budget_remaining > 40 ? RISK_COLORS.observe :
                                    burn.error_budget_remaining > 15 ? RISK_COLORS.danger :
                                    RISK_COLORS.freeze
                                }}
                              />
                            </div>
                            <span className="text-sm text-gray-400">
                              {formatPercentage(burn.error_budget_remaining, 0)}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Heatmap */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Risk Heatmap (24h)</h2>
            {heatmapLoading ? (
              <LoadingSpinner message="Loading heatmap..." />
            ) : heatmap ? (
              <RiskHeatmap data={heatmap} />
            ) : (
              <p className="text-gray-500">No heatmap data available</p>
            )}
          </div>
        </div>

        {/* Right Column - Panels */}
        <div className="space-y-6">
          {/* AI Insights */}
          <div className="bg-gray-800 rounded-lg p-6">
            {summary && <AIInsightsPanel summary={summary} />}
          </div>

          {/* Release Gate */}
          <div className="bg-gray-800 rounded-lg p-6">
            <ReleaseDecisionPanel />
          </div>

          {/* Alert Feed */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">
              Recent Alerts
              {alertFeed?.unacknowledged ? (
                <span className="ml-2 px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full text-sm">
                  {alertFeed.unacknowledged} new
                </span>
              ) : null}
            </h2>
            <AlertFeedPanel
              alerts={alertFeed?.alerts || []}
              loading={alertsLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
