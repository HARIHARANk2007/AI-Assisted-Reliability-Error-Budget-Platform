/**
 * Alert Feed Panel Component
 * Displays chronological list of alerts with actions
 */

import React from 'react';
import { Alert, AlertSeverity } from '../../types';
import { formatRelativeTime, getSeverityClass } from '../../utils/helpers';

interface AlertFeedPanelProps {
  alerts: Alert[];
  onAcknowledge?: (alertId: number) => void;
  onViewDetails?: (alert: Alert) => void;
  loading?: boolean;
}

const SEVERITY_ICONS: Record<AlertSeverity, React.ReactNode> = {
  info: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
    </svg>
  ),
  warning: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ),
  critical: (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  ),
  emergency: (
    <svg className="w-5 h-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  ),
};

export const AlertFeedPanel: React.FC<AlertFeedPanelProps> = ({
  alerts,
  onAcknowledge,
  onViewDetails,
  loading,
}) => {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-gray-700/50 rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-gray-600 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-600 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!alerts.length) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-gray-500">
        <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>No alerts</span>
      </div>
    );
  }

  return (
    <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`
            bg-gray-700/50 rounded-lg p-4 border-l-4 transition-colors
            ${alert.acknowledged ? 'opacity-60 border-gray-600' : ''}
            ${!alert.acknowledged && alert.severity === 'emergency' ? 'border-red-500' : ''}
            ${!alert.acknowledged && alert.severity === 'critical' ? 'border-orange-500' : ''}
            ${!alert.acknowledged && alert.severity === 'warning' ? 'border-yellow-500' : ''}
            ${!alert.acknowledged && alert.severity === 'info' ? 'border-blue-500' : ''}
          `}
        >
          <div className="flex items-start gap-3">
            {/* Severity icon */}
            <div className={getSeverityClass(alert.severity)}>
              {SEVERITY_ICONS[alert.severity]}
            </div>
            
            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h4 className="text-sm font-medium text-white truncate">
                  {alert.title}
                </h4>
                <span className="text-xs text-gray-500 flex-shrink-0">
                  {formatRelativeTime(alert.timestamp)}
                </span>
              </div>
              
              <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                {alert.message}
              </p>
              
              <div className="flex items-center gap-3 mt-2">
                <span className="text-xs text-gray-500">
                  {alert.service_name}
                </span>
                
                {!alert.acknowledged && onAcknowledge && (
                  <button
                    onClick={() => onAcknowledge(alert.id)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Acknowledge
                  </button>
                )}
                
                {onViewDetails && (
                  <button
                    onClick={() => onViewDetails(alert)}
                    className="text-xs text-gray-400 hover:text-gray-300"
                  >
                    Details
                  </button>
                )}
                
                {alert.acknowledged && (
                  <span className="text-xs text-green-500">
                    ✓ Acknowledged by {alert.acknowledged_by}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AlertFeedPanel;
