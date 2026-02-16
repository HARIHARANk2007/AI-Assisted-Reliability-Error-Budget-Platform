/**
 * Utility functions
 */

import { RiskLevel, AlertSeverity } from '../types';

// Risk level colors
export const RISK_COLORS: Record<RiskLevel, string> = {
  safe: '#22c55e',
  observe: '#eab308',
  danger: '#f97316',
  freeze: '#ef4444',
};

export const RISK_BG_COLORS: Record<RiskLevel, string> = {
  safe: 'rgba(34, 197, 94, 0.2)',
  observe: 'rgba(234, 179, 8, 0.2)',
  danger: 'rgba(249, 115, 22, 0.2)',
  freeze: 'rgba(239, 68, 68, 0.2)',
};

// Alert severity colors
export const SEVERITY_COLORS: Record<AlertSeverity, string> = {
  info: '#3b82f6',
  warning: '#eab308',
  critical: '#f97316',
  emergency: '#ef4444',
};

// Format time duration
export function formatDuration(hours: number | null): string {
  if (hours === null || hours === undefined) return 'N/A';
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  if (hours < 24) return `${hours.toFixed(1)}h`;
  if (hours < 168) return `${(hours / 24).toFixed(1)}d`;
  return `${Math.round(hours / 168)}w`;
}

// Format percentage
export function formatPercentage(value: number | null, decimals = 1): string {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(decimals)}%`;
}

// Format burn rate
export function formatBurnRate(value: number | null): string {
  if (value === null || value === undefined) return 'N/A';
  return `${value.toFixed(2)}×`;
}

// Format timestamp
export function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

// Format relative time
export function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

// Get risk level class
export function getRiskClass(risk: RiskLevel): string {
  return `risk-${risk}`;
}

// Get severity class
export function getSeverityClass(severity: AlertSeverity): string {
  const classes: Record<AlertSeverity, string> = {
    info: 'bg-blue-500/20 text-blue-400',
    warning: 'bg-yellow-500/20 text-yellow-400',
    critical: 'bg-orange-500/20 text-orange-400',
    emergency: 'bg-red-500/20 text-red-400',
  };
  return classes[severity];
}

// Generate unique ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Clamp value
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
