        /**
 * API Service - Handles all backend communication
 */

import axios, { AxiosInstance } from 'axios';
import {
  Service,
  ServiceListResponse,
  SLOComputation,
  BurnRateComputation,
  BurnHistory,
  Forecast,
  ReleaseCheckRequest,
  ReleaseCheckResponse,
  AlertFeed,
  AISummary,
  DashboardOverview,
  HeatmapData,
} from '../types';

const API_BASE_URL = '/api/v1';

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============ Services API ============

export const servicesApi = {
  list: async (activeOnly = true): Promise<ServiceListResponse> => {
    const response = await api.get('/services', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  get: async (serviceId: number): Promise<Service> => {
    const response = await api.get(`/services/${serviceId}`);
    return response.data;
  },

  create: async (service: Partial<Service>): Promise<Service> => {
    const response = await api.post('/services', service);
    return response.data;
  },

  update: async (serviceId: number, update: Partial<Service>): Promise<Service> => {
    const response = await api.patch(`/services/${serviceId}`, update);
    return response.data;
  },

  delete: async (serviceId: number): Promise<void> => {
    await api.delete(`/services/${serviceId}`);
  },
};

// ============ SLO API ============

export const sloApi = {
  getForService: async (serviceName: string): Promise<SLOComputation[]> => {
    const response = await api.get(`/slo/${serviceName}`);
    return response.data.computations || [];
  },

  getAll: async (): Promise<{services: SLOComputation[]}> => {
    const response = await api.get('/slo');
    return response.data;
  },
};

// ============ Burn Rate API ============

export const burnApi = {
  getForService: async (
    serviceName: string,
    windowMinutes = 60,
    historyHours = 24
  ): Promise<BurnHistory> => {
    const response = await api.get(`/burn/${serviceName}`, {
      params: { window_minutes: windowMinutes, history_hours: historyHours },
    });
    return response.data;
  },

  getCurrent: async (serviceName: string, windowMinutes = 60): Promise<BurnRateComputation> => {
    const response = await api.get(`/burn/${serviceName}/current`, {
      params: { window_minutes: windowMinutes },
    });
    return response.data;
  },

  getAllWindows: async (serviceName: string): Promise<BurnRateComputation[]> => {
    const response = await api.get(`/burn/${serviceName}/windows`);
    return response.data;
  },

  getAll: async (windowMinutes = 60): Promise<BurnRateComputation[]> => {
    const response = await api.get('/burn', {
      params: { window_minutes: windowMinutes },
    });
    return response.data;
  },
};

// ============ Forecast API ============

export const forecastApi = {
  getForService: async (serviceName: string, useTrend = true): Promise<Forecast> => {
    const response = await api.get(`/forecast/${serviceName}`, {
      params: { use_trend: useTrend },
    });
    return response.data;
  },

  getAll: async (): Promise<Forecast[]> => {
    const response = await api.get('/forecast');
    return response.data;
  },

  getNearest: async (): Promise<{ service_name: string; time_to_exhaustion_hours: number } | null> => {
    const response = await api.get('/forecast/critical/nearest');
    return response.data;
  },
};

// ============ Release Gate API ============

export const releaseApi = {
  check: async (request: ReleaseCheckRequest): Promise<ReleaseCheckResponse> => {
    const response = await api.post('/release/check', request);
    return response.data;
  },

  getHistory: async (serviceName?: string, limit = 50): Promise<unknown[]> => {
    const response = await api.get('/release/history', {
      params: { service_name: serviceName, limit },
    });
    return response.data;
  },

  getStatistics: async (days = 7): Promise<unknown> => {
    const response = await api.get('/release/statistics', {
      params: { days },
    });
    return response.data;
  },
};

// ============ Summary API ============

export const summaryApi = {
  getAISummary: async (): Promise<AISummary> => {
    const response = await api.get('/summary');
    return response.data;
  },

  getExecutiveOverview: async (): Promise<DashboardOverview> => {
    const response = await api.get('/summary/executive');
    return response.data;
  },

  getHeatmap: async (hours = 24, intervalHours = 1): Promise<HeatmapData> => {
    const response = await api.get('/summary/heatmap', {
      params: { hours, interval_hours: intervalHours },
    });
    return response.data;
  },

  getServiceNarrative: async (serviceName: string): Promise<{ narrative: string }> => {
    const response = await api.get(`/summary/narrative/${serviceName}`);
    return response.data;
  },
};

// ============ Alerts API ============

export const alertsApi = {
  getAll: async (
    serviceName?: string,
    severity?: string,
    acknowledged?: boolean,
    hours = 24,
    limit = 100
  ): Promise<AlertFeed> => {
    const response = await api.get('/alerts', {
      params: {
        service_name: serviceName,
        severity,
        acknowledged,
        hours,
        limit,
      },
    });
    return response.data;
  },

  getFeed: async (hours = 24, limit = 50): Promise<AlertFeed> => {
    const response = await api.get('/alerts/feed', {
      params: { hours, limit },
    });
    return response.data;
  },

  acknowledge: async (alertId: number, acknowledgedBy: string): Promise<void> => {
    await api.post(`/alerts/${alertId}/acknowledge`, null, {
      params: { acknowledged_by: acknowledgedBy },
    });
  },

  bulkAcknowledge: async (alertIds: number[], acknowledgedBy: string): Promise<void> => {
    await api.post('/alerts/acknowledge-bulk', alertIds, {
      params: { acknowledged_by: acknowledgedBy },
    });
  },

  getStatistics: async (days = 7): Promise<unknown> => {
    const response = await api.get('/alerts/statistics', {
      params: { days },
    });
    return response.data;
  },
};

// ============ Metrics API ============

export const metricsApi = {
  getForService: async (serviceName: string, hours = 24): Promise<unknown[]> => {
    const response = await api.get(`/metrics/${serviceName}`, {
      params: { hours },
    });
    return response.data;
  },

  simulate: async (hours = 24, chaosLevel = 0.2): Promise<unknown> => {
    const response = await api.post('/metrics/simulate', null, {
      params: { hours, chaos_level: chaosLevel },
    });
    return response.data;
  },

  simulateSnapshot: async (chaosLevel = 0.2): Promise<unknown> => {
    const response = await api.post('/metrics/simulate/snapshot', null, {
      params: { chaos_level: chaosLevel },
    });
    return response.data;
  },
};

export default api;
