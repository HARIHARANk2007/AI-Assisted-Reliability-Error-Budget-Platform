/**
 * TypeScript type definitions for the SRE Reliability Platform
 */

// Risk levels
export type RiskLevel = 'safe' | 'observe' | 'danger' | 'freeze';

// Alert types
export type AlertSeverity = 'info' | 'warning' | 'critical' | 'emergency';
export type AlertChannel = 'email' | 'slack' | 'ui' | 'pagerduty';

// Service
export interface Service {
  id: number;
  name: string;
  description: string | null;
  team: string | null;
  tier: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// SLO
export interface SLOTarget {
  id: number;
  service_id: number;
  name: string;
  target_value: number;
  window_days: number;
  error_budget_policy: number;
  burn_rate_threshold: number;
  critical_burn_rate: number;
  is_active: boolean;
}

export interface SLOComputation {
  service_id: number;
  service_name: string;
  slo_name: string;
  target_value: number;
  current_value: number;
  is_meeting_slo: boolean;
  total_budget: number;
  consumed_budget: number;
  consumed_percentage: number;
  remaining_percentage: number;
  availability_5m: number | null;
  availability_1h: number | null;
  availability_24h: number | null;
  window_start: string;
  window_end: string;
  computed_at: string;
}

// Burn Rate
export interface BurnRateComputation {
  service_id: number;
  service_name: string;
  timestamp: string;
  window_minutes: number;
  current_error_rate: number;
  allowed_error_rate: number;
  burn_rate: number;
  error_budget_consumed: number;
  error_budget_remaining: number;
  risk_level: RiskLevel;
  risk_color: string;
  risk_action: string;
}

export interface BurnHistory {
  service_id: number;
  service_name: string;
  history: BurnRateComputation[];
  current_burn_rate: number;
  average_burn_rate_24h: number;
  peak_burn_rate_24h: number;
}

// Forecast
export interface Forecast {
  service_id: number;
  service_name: string;
  computed_at: string;
  current_burn_rate: number;
  error_budget_remaining: number;
  time_to_exhaustion_hours: number | null;
  projected_exhaustion_time: string | null;
  confidence_level: string;
  burn_rate_trend: string;
  trend_slope: number;
  forecast_message: string;
}

// Release Gate
export interface ReleaseCheckRequest {
  service_name: string;
  deployment_id: string;
  version?: string;
  requested_by?: string;
  override?: boolean;
  override_reason?: string;
}

export interface ReleaseCheckResponse {
  allowed: boolean;
  reason: string;
  service_name: string;
  deployment_id: string;
  current_risk_level: RiskLevel;
  current_burn_rate: number;
  error_budget_remaining: number;
  time_to_exhaustion_hours: number | null;
  recommendations: string[];
  checked_at: string;
  checked_by: string;
}

// Alerts
export interface Alert {
  id: number;
  service_id: number;
  service_name: string;
  timestamp: string;
  severity: AlertSeverity;
  channel: AlertChannel;
  title: string;
  message: string;
  metadata: Record<string, unknown>;
  sent: boolean;
  acknowledged: boolean;
  acknowledged_by: string | null;
}

export interface AlertFeed {
  alerts: Alert[];
  total: number;
  unacknowledged: number;
}

// AI Summary
export interface AIInsight {
  service_name: string;
  insight_type: string;
  message: string;
  severity: string;
  data: Record<string, unknown> | null;
}

export interface AISummary {
  generated_at: string;
  overall_health: string;
  overall_score: number;
  executive_summary: string;
  insights: AIInsight[];
  action_items: string[];
  services_at_risk: string[];
  nearest_budget_exhaustion: {
    service_name: string;
    time_to_exhaustion_hours: number;
    projected_exhaustion_time: string;
    current_burn_rate: number;
    budget_remaining: number;
  } | null;
}

// Dashboard
export interface DashboardOverview {
  total_services: number;
  services_meeting_slo: number;
  services_at_risk: number;
  global_compliance_score: number;
  risk_distribution: Record<RiskLevel, number>;
  average_budget_remaining: number;
  lowest_budget_service: string | null;
  lowest_budget_percentage: number | null;
  nearest_exhaustion: {
    service_name: string;
    time_to_exhaustion_hours: number;
  } | null;
  active_alerts: number;
  critical_alerts: number;
  compliance_trend_24h: string;
}

// Heatmap
export interface HeatmapData {
  services: string[];
  timestamps: string[];
  risk_matrix: RiskLevel[][];
}

// Service List Response
export interface ServiceListResponse {
  services: Service[];
  total: number;
}
