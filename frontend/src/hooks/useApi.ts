/**
 * React Query hooks for data fetching
 * Using TanStack Query v5 syntax
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  servicesApi,
  sloApi,
  burnApi,
  forecastApi,
  releaseApi,
  summaryApi,
  alertsApi,
  metricsApi,
} from '../services/api';
import { ReleaseCheckRequest } from '../types';

// Query keys
export const queryKeys = {
  services: ['services'] as const,
  service: (id: number) => ['services', id] as const,
  slo: (serviceName: string) => ['slo', serviceName] as const,
  sloAll: ['slo'] as const,
  burn: (serviceName: string) => ['burn', serviceName] as const,
  burnAll: ['burn'] as const,
  forecast: (serviceName: string) => ['forecast', serviceName] as const,
  forecastAll: ['forecast'] as const,
  forecastNearest: ['forecast', 'nearest'] as const,
  summary: ['summary'] as const,
  executive: ['executive'] as const,
  heatmap: ['heatmap'] as const,
  alerts: ['alerts'] as const,
  alertFeed: ['alerts', 'feed'] as const,
};

// ============ Services Hooks ============

export function useServices(activeOnly = true) {
  return useQuery({
    queryKey: queryKeys.services,
    queryFn: () => servicesApi.list(activeOnly),
    refetchInterval: 60000,
  });
}

export function useService(serviceId: number) {
  return useQuery({
    queryKey: queryKeys.service(serviceId),
    queryFn: () => servicesApi.get(serviceId),
    enabled: !!serviceId,
  });
}

// ============ SLO Hooks ============

export function useServiceSLO(serviceName: string) {
  return useQuery({
    queryKey: queryKeys.slo(serviceName),
    queryFn: () => sloApi.getForService(serviceName),
    enabled: !!serviceName,
    refetchInterval: 60000,
  });
}

// ============ Burn Rate Hooks ============

export function useServiceBurn(serviceName: string, windowMinutes = 60) {
  return useQuery({
    queryKey: queryKeys.burn(serviceName),
    queryFn: () => burnApi.getForService(serviceName, windowMinutes),
    enabled: !!serviceName,
    refetchInterval: 30000,
  });
}

export function useAllBurnRates(windowMinutes = 60) {
  return useQuery({
    queryKey: queryKeys.burnAll,
    queryFn: () => burnApi.getAll(windowMinutes),
    refetchInterval: 30000,
  });
}

// ============ Forecast Hooks ============

export function useServiceForecast(serviceName: string) {
  return useQuery({
    queryKey: queryKeys.forecast(serviceName),
    queryFn: () => forecastApi.getForService(serviceName),
    enabled: !!serviceName,
    refetchInterval: 60000,
  });
}

export function useAllForecasts() {
  return useQuery({
    queryKey: queryKeys.forecastAll,
    queryFn: () => forecastApi.getAll(),
    refetchInterval: 60000,
  });
}

export function useNearestExhaustion() {
  return useQuery({
    queryKey: queryKeys.forecastNearest,
    queryFn: () => forecastApi.getNearest(),
    refetchInterval: 60000,
  });
}

// ============ Summary Hooks ============

export function useAISummary() {
  return useQuery({
    queryKey: queryKeys.summary,
    queryFn: () => summaryApi.getAISummary(),
    refetchInterval: 60000,
  });
}

export function useExecutiveOverview() {
  return useQuery({
    queryKey: queryKeys.executive,
    queryFn: () => summaryApi.getExecutiveOverview(),
    refetchInterval: 30000,
  });
}

export function useHeatmap(hours = 24, intervalHours = 1) {
  return useQuery({
    queryKey: queryKeys.heatmap,
    queryFn: () => summaryApi.getHeatmap(hours, intervalHours),
    refetchInterval: 60000,
  });
}

// ============ Alerts Hooks ============

export function useAlertFeed(hours = 24, limit = 50) {
  return useQuery({
    queryKey: queryKeys.alertFeed,
    queryFn: () => alertsApi.getFeed(hours, limit),
    refetchInterval: 15000,
  });
}

export function useAlerts(
  serviceName?: string,
  severity?: string,
  acknowledged?: boolean,
  hours = 24
) {
  return useQuery({
    queryKey: queryKeys.alerts,
    queryFn: () => alertsApi.getAll(serviceName, severity, acknowledged, hours),
    refetchInterval: 15000,
  });
}

// ============ Release Gate Hooks ============

export function useReleaseCheck() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ReleaseCheckRequest) => releaseApi.check(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.burnAll });
      queryClient.invalidateQueries({ queryKey: queryKeys.summary });
    },
  });
}

// ============ Metrics Hooks ============

export function useSimulateMetrics() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ hours, chaosLevel }: { hours: number; chaosLevel: number }) =>
      metricsApi.simulate(hours, chaosLevel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.services });
      queryClient.invalidateQueries({ queryKey: queryKeys.burnAll });
      queryClient.invalidateQueries({ queryKey: queryKeys.summary });
      queryClient.invalidateQueries({ queryKey: queryKeys.alertFeed });
    },
  });
}

// ============ Alert Actions ============

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId, acknowledgedBy }: { alertId: number; acknowledgedBy: string }) =>
      alertsApi.acknowledge(alertId, acknowledgedBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.alertFeed });
      queryClient.invalidateQueries({ queryKey: queryKeys.alerts });
    },
  });
}
