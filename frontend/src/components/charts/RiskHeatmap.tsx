/**
 * Risk Heatmap Component
 * Displays service risk levels over time as a color-coded matrix
 */

import React from 'react';
import { RiskLevel, HeatmapData } from '../../types';
import { RISK_COLORS } from '../../utils/helpers';

interface RiskHeatmapProps {
  data: HeatmapData;
  onCellClick?: (service: string, timestamp: string) => void;
}

export const RiskHeatmap: React.FC<RiskHeatmapProps> = ({
  data,
  onCellClick,
}) => {
  if (!data.services.length || !data.timestamps.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        No heatmap data available
      </div>
    );
  }

  // Get cell color based on risk level
  const getCellColor = (risk: RiskLevel): string => {
    return RISK_COLORS[risk] || '#374151';
  };

  // Format timestamp for header
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-max">
        {/* Header row with timestamps */}
        <div className="flex">
          <div className="w-40 flex-shrink-0"></div>
          {data.timestamps.map((ts, i) => (
            <div
              key={i}
              className="w-8 h-8 flex items-center justify-center text-xs text-gray-500"
              style={{ writingMode: 'vertical-lr' }}
            >
              {i % 4 === 0 ? formatTime(ts) : ''}
            </div>
          ))}
        </div>

        {/* Service rows */}
        {data.services.map((service, serviceIdx) => (
          <div key={service} className="flex items-center">
            {/* Service name */}
            <div className="w-40 flex-shrink-0 pr-4 py-1 text-sm text-gray-300 truncate">
              {service}
            </div>
            
            {/* Risk cells */}
            {data.risk_matrix[serviceIdx]?.map((risk, timeIdx) => (
              <div
                key={timeIdx}
                className={`
                  w-8 h-6 m-px rounded-sm transition-transform
                  ${onCellClick ? 'cursor-pointer hover:scale-110' : ''}
                `}
                style={{ backgroundColor: getCellColor(risk as RiskLevel) }}
                onClick={() => onCellClick?.(service, data.timestamps[timeIdx])}
                title={`${service} at ${formatTime(data.timestamps[timeIdx])}: ${risk}`}
              />
            ))}
          </div>
        ))}

        {/* Legend */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-gray-700">
          {(['safe', 'observe', 'danger', 'freeze'] as RiskLevel[]).map((risk) => (
            <div key={risk} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: RISK_COLORS[risk] }}
              />
              <span className="text-xs text-gray-400 uppercase">{risk}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default RiskHeatmap;
