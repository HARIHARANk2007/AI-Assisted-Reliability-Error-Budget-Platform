/**
 * Burn Rate Chart Component
 * Line chart showing burn rate over time with risk level zones
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  ComposedChart,
} from 'recharts';
import { BurnRateComputation } from '../../types';
import { formatBurnRate, RISK_COLORS } from '../../utils/helpers';

interface BurnRateChartProps {
  data: BurnRateComputation[];
  height?: number;
  showThresholds?: boolean;
}

export const BurnRateChart: React.FC<BurnRateChartProps> = ({
  data,
  height = 300,
  showThresholds = true,
}) => {
  // Transform data for chart
  const chartData = data.map((d) => ({
    time: new Date(d.timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    }),
    burnRate: d.burn_rate,
    risk: d.risk_level,
  })).reverse();

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-gray-400 text-sm">{label}</p>
          <p className="text-white font-semibold">
            Burn Rate: {formatBurnRate(data.burnRate)}
          </p>
          <p className={`text-sm ${
            data.risk === 'safe' ? 'text-green-400' :
            data.risk === 'observe' ? 'text-yellow-400' :
            data.risk === 'danger' ? 'text-orange-400' :
            'text-red-400'
          }`}>
            Risk: {data.risk.toUpperCase()}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="burnGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
          </linearGradient>
        </defs>
        
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        
        <XAxis 
          dataKey="time" 
          stroke="#6b7280"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
        />
        
        <YAxis 
          stroke="#6b7280"
          tick={{ fill: '#9ca3af', fontSize: 12 }}
          domain={[0, 'auto']}
          tickFormatter={(value) => `${value}×`}
        />
        
        <Tooltip content={<CustomTooltip />} />
        
        {/* Threshold lines */}
        {showThresholds && (
          <>
            <ReferenceLine 
              y={1} 
              stroke={RISK_COLORS.safe} 
              strokeDasharray="5 5"
              label={{ value: 'Normal', fill: RISK_COLORS.safe, fontSize: 10 }}
            />
            <ReferenceLine 
              y={1.5} 
              stroke={RISK_COLORS.observe} 
              strokeDasharray="5 5"
            />
            <ReferenceLine 
              y={2} 
              stroke={RISK_COLORS.danger} 
              strokeDasharray="5 5"
            />
            <ReferenceLine 
              y={3} 
              stroke={RISK_COLORS.freeze} 
              strokeDasharray="5 5"
              label={{ value: 'Freeze', fill: RISK_COLORS.freeze, fontSize: 10 }}
            />
          </>
        )}
        
        <Area
          type="monotone"
          dataKey="burnRate"
          stroke="#3b82f6"
          fill="url(#burnGradient)"
        />
        
        <Line
          type="monotone"
          dataKey="burnRate"
          stroke="#3b82f6"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 6, fill: '#3b82f6' }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
};

export default BurnRateChart;
