/**
 * Risk Badge Component
 * Displays color-coded risk level indicator
 */

import React from 'react';
import { RiskLevel } from '../../types';

interface RiskBadgeProps {
  risk: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const RISK_CONFIG: Record<RiskLevel, { label: string; className: string }> = {
  safe: {
    label: 'SAFE',
    className: 'bg-green-500/20 text-green-400 border-green-500/30',
  },
  observe: {
    label: 'OBSERVE',
    className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  },
  danger: {
    label: 'DANGER',
    className: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  },
  freeze: {
    label: 'FREEZE',
    className: 'bg-red-500/20 text-red-400 border-red-500/30',
  },
};

const SIZE_CLASSES = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-base',
};

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  risk,
  size = 'md',
  showLabel = true,
}) => {
  const config = RISK_CONFIG[risk];
  
  return (
    <span
      className={`
        inline-flex items-center justify-center
        font-semibold uppercase rounded-full border
        ${config.className}
        ${SIZE_CLASSES[size]}
      `}
    >
      {showLabel ? config.label : ''}
      {!showLabel && (
        <span
          className={`w-2 h-2 rounded-full ${
            risk === 'safe' ? 'bg-green-500' :
            risk === 'observe' ? 'bg-yellow-500' :
            risk === 'danger' ? 'bg-orange-500' :
            'bg-red-500'
          }`}
        />
      )}
    </span>
  );
};

export default RiskBadge;
