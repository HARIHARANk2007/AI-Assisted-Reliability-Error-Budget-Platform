/**
 * Service Detail Page
 * Detailed view for a single service's reliability status
 */

import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useServiceBurn, useServiceForecast, useServiceSLO } from '../hooks/useApi';
import StatCard from '../components/common/StatCard';
import RiskBadge from '../components/common/RiskBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import BurnRateChart from '../components/charts/BurnRateChart';
import BudgetGauge from '../components/charts/BudgetGauge';
import { formatBurnRate, formatDuration, formatPercentage, formatTimestamp } from '../utils/helpers';

const ServiceDetailPage: React.FC = () => {
  const { serviceName } = useParams<{ serviceName: string }>();
  const navigate = useNavigate();

  const { data: burnData, isLoading: burnLoading } = useServiceBurn(serviceName || '');
  const { data: forecast, isLoading: forecastLoading } = useServiceForecast(serviceName || '');
  const { data: sloData, isLoading: sloLoading } = useServiceSLO(serviceName || '');

  if (!serviceName) {
    navigate('/');
    return null;
  }

  if (burnLoading || forecastLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="lg" message={`Loading ${serviceName}...`} />
      </div>
    );
  }

  // Get current burn rate from history or compute
  const currentBurn = burnData?.history?.[0];
  const burnRate = burnData?.current_burn_rate || 0;
  const budgetRemaining = currentBurn?.error_budget_remaining || 100;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h1 className="text-2xl font-bold">{serviceName}</h1>
            <p className="text-gray-400">Service reliability details</p>
          </div>
        </div>
        {currentBurn && (
          <RiskBadge risk={currentBurn.risk_level} size="lg" />
        )}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          label="Burn Rate"
          value={formatBurnRate(burnRate)}
          color={
            burnRate < 1 ? 'success' :
            burnRate < 1.5 ? 'warning' :
            burnRate < 2 ? 'danger' : 'danger'
          }
        />
        <StatCard
          label="Budget Remaining"
          value={formatPercentage(budgetRemaining)}
          color={
            budgetRemaining > 70 ? 'success' :
            budgetRemaining > 40 ? 'warning' : 'danger'
          }
        />
        <StatCard
          label="Time to Exhaustion"
          value={formatDuration(forecast?.time_to_exhaustion_hours || null)}
          color={
            !forecast?.time_to_exhaustion_hours ? 'success' :
            forecast.time_to_exhaustion_hours > 168 ? 'success' :
            forecast.time_to_exhaustion_hours > 24 ? 'warning' : 'danger'
          }
        />
        <StatCard
          label="Trend"
          value={forecast?.burn_rate_trend || 'stable'}
          trend={
            forecast?.burn_rate_trend === 'increasing' ? 'up' :
            forecast?.burn_rate_trend === 'decreasing' ? 'down' : 'stable'
          }
        />
        <StatCard
          label="Avg Burn (24h)"
          value={formatBurnRate(burnData?.average_burn_rate_24h || 0)}
        />
        <StatCard
          label="Peak Burn (24h)"
          value={formatBurnRate(burnData?.peak_burn_rate_24h || 0)}
          color={
            (burnData?.peak_burn_rate_24h || 0) > 2 ? 'danger' :
            (burnData?.peak_burn_rate_24h || 0) > 1.5 ? 'warning' : 'default'
          }
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left - Charts */}
        <div className="lg:col-span-2 space-y-6">
          {/* Burn Rate Chart */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Burn Rate History (24h)</h2>
            {burnData?.history && burnData.history.length > 0 ? (
              <BurnRateChart data={burnData.history} height={350} />
            ) : (
              <div className="flex items-center justify-center h-64 text-gray-500">
                No burn rate history available
              </div>
            )}
          </div>

          {/* SLO Targets */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">SLO Targets</h2>
            {sloLoading ? (
              <LoadingSpinner />
            ) : sloData && sloData.length > 0 ? (
              <div className="space-y-4">
                {sloData.map((slo, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg"
                  >
                    <div>
                      <h3 className="font-medium">{slo.slo_name}</h3>
                      <p className="text-sm text-gray-400">
                        Target: {slo.target_value}% | Window: {30} days
                      </p>
                    </div>
                    <div className="text-right">
                      <div className={`text-2xl font-bold ${
                        slo.is_meeting_slo ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {slo.current_value.toFixed(3)}%
                      </div>
                      <div className={`text-sm ${
                        slo.is_meeting_slo ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {slo.is_meeting_slo ? '✓ Meeting SLO' : '✗ Below SLO'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No SLO targets configured</p>
            )}
          </div>
        </div>

        {/* Right - Details */}
        <div className="space-y-6">
          {/* Budget Gauge */}
          <div className="bg-gray-800 rounded-lg p-6 flex flex-col items-center">
            <h2 className="text-lg font-semibold mb-4">Error Budget</h2>
            <BudgetGauge remaining={budgetRemaining} size="lg" />
            {currentBurn && (
              <div className="mt-4 text-center">
                <p className="text-sm text-gray-400">
                  Consumed: {formatPercentage(currentBurn.error_budget_consumed)}
                </p>
              </div>
            )}
          </div>

          {/* Forecast */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Forecast</h2>
            {forecast ? (
              <div className="space-y-4">
                <div className="p-4 bg-gray-700/50 rounded-lg">
                  <p className="text-sm text-gray-300">{forecast.forecast_message}</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="text-center p-3 bg-gray-700/30 rounded-lg">
                    <div className="text-sm text-gray-400">Confidence</div>
                    <div className="font-semibold capitalize">{forecast.confidence_level}</div>
                  </div>
                  <div className="text-center p-3 bg-gray-700/30 rounded-lg">
                    <div className="text-sm text-gray-400">Trend</div>
                    <div className="font-semibold capitalize">{forecast.burn_rate_trend}</div>
                  </div>
                </div>

                {forecast.projected_exhaustion_time && (
                  <div className="text-center p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <div className="text-sm text-red-400">Projected Exhaustion</div>
                    <div className="font-semibold text-red-300">
                      {formatTimestamp(forecast.projected_exhaustion_time)}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">No forecast available</p>
            )}
          </div>

          {/* Rolling Windows */}
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Availability Windows</h2>
            {sloData && sloData.length > 0 ? (
              <div className="space-y-3">
                {sloData[0].availability_5m !== null && (
                  <div className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                    <span className="text-gray-400">5 minute</span>
                    <span className={`font-semibold ${
                      (sloData[0].availability_5m || 0) >= 99.9 ? 'text-green-400' :
                      (sloData[0].availability_5m || 0) >= 99 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {sloData[0].availability_5m?.toFixed(3)}%
                    </span>
                  </div>
                )}
                {sloData[0].availability_1h !== null && (
                  <div className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                    <span className="text-gray-400">1 hour</span>
                    <span className={`font-semibold ${
                      (sloData[0].availability_1h || 0) >= 99.9 ? 'text-green-400' :
                      (sloData[0].availability_1h || 0) >= 99 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {sloData[0].availability_1h?.toFixed(3)}%
                    </span>
                  </div>
                )}
                {sloData[0].availability_24h !== null && (
                  <div className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                    <span className="text-gray-400">24 hour</span>
                    <span className={`font-semibold ${
                      (sloData[0].availability_24h || 0) >= 99.9 ? 'text-green-400' :
                      (sloData[0].availability_24h || 0) >= 99 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {sloData[0].availability_24h?.toFixed(3)}%
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-500">No availability data</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServiceDetailPage;
