/**
 * Stat Card Component
 * Displays a metric value with label and optional trend indicator
 */

import React from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: string;
  color?: 'default' | 'success' | 'warning' | 'danger';
  icon?: React.ReactNode;
  onClick?: () => void;
}

const COLOR_CLASSES = {
  default: 'text-white',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  danger: 'text-red-400',
};

const TREND_ICONS = {
  up: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
    </svg>
  ),
  down: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
    </svg>
  ),
  stable: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14" />
    </svg>
  ),
};

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtitle,
  trend,
  trendValue,
  color = 'default',
  icon,
  onClick,
}) => {
  return (
    <div
      className={`
        bg-gray-800 rounded-lg p-4 flex flex-col
        ${onClick ? 'cursor-pointer hover:bg-gray-700 transition-colors' : ''}
      `}
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400 text-sm">{label}</span>
        {icon && <span className="text-gray-500">{icon}</span>}
      </div>
      
      <div className="flex items-end gap-2">
        <span className={`text-3xl font-bold ${COLOR_CLASSES[color]}`}>
          {value}
        </span>
        
        {trend && (
          <div
            className={`flex items-center gap-1 text-sm ${
              trend === 'up' ? 'text-red-400' :
              trend === 'down' ? 'text-green-400' :
              'text-gray-400'
            }`}
          >
            {TREND_ICONS[trend]}
            {trendValue && <span>{trendValue}</span>}
          </div>
        )}
      </div>
      
      {subtitle && (
        <span className="text-gray-500 text-sm mt-1">{subtitle}</span>
      )}
    </div>
  );
};

export default StatCard;
