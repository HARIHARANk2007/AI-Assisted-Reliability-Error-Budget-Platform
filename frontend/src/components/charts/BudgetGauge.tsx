/**
 * Budget Gauge Component
 * Circular gauge showing error budget remaining
 */

import React from 'react';

interface BudgetGaugeProps {
  remaining: number; // 0-100
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const SIZE_CONFIG = {
  sm: { width: 80, stroke: 6, fontSize: 'text-lg' },
  md: { width: 120, stroke: 8, fontSize: 'text-2xl' },
  lg: { width: 160, stroke: 10, fontSize: 'text-3xl' },
};

export const BudgetGauge: React.FC<BudgetGaugeProps> = ({
  remaining,
  size = 'md',
  showLabel = true,
}) => {
  const config = SIZE_CONFIG[size];
  const radius = (config.width - config.stroke) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (remaining / 100) * circumference;

  // Color based on remaining budget
  const getColor = () => {
    if (remaining >= 70) return '#22c55e'; // Green
    if (remaining >= 50) return '#eab308'; // Yellow
    if (remaining >= 25) return '#f97316'; // Orange
    return '#ef4444'; // Red
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: config.width, height: config.width }}>
        <svg
          width={config.width}
          height={config.width}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke="#374151"
            strokeWidth={config.stroke}
          />
          
          {/* Progress circle */}
          <circle
            cx={config.width / 2}
            cy={config.width / 2}
            r={radius}
            fill="none"
            stroke={getColor()}
            strokeWidth={config.stroke}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-bold ${config.fontSize}`} style={{ color: getColor() }}>
            {remaining.toFixed(0)}%
          </span>
        </div>
      </div>
      
      {showLabel && (
        <span className="text-gray-400 text-sm mt-2">Budget Remaining</span>
      )}
    </div>
  );
};

export default BudgetGauge;
