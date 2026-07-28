import axios from 'axios';
import { getAuthSession } from '../utils/auth';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

const client = axios.create({
  baseURL: API_BASE_URL,
  // Trip planning can be slow on the first run (graph build + routing),
  // so keep this high to avoid front-end "Network Error" timeouts.
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const requestPath = `${config.baseURL || ''}${config.url || ''}`;
    const isAuthRequest = /\/api\/auth\/(login|register)\/?$/.test(requestPath);
    const { accessToken } = getAuthSession();

    if (isAuthRequest) {
      if (config.headers) {
        if (typeof config.headers.delete === 'function') {
          config.headers.delete('Authorization');
        } else if ('Authorization' in config.headers) {
          delete config.headers.Authorization;
        }
      }
    } else if (accessToken) {
      if (config.headers && typeof config.headers.set === 'function') {
        config.headers.set('Authorization', `Bearer ${accessToken}`);
      } else {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${accessToken}`;
      }
    } else if (config.headers) {
      if (typeof config.headers.delete === 'function') {
        config.headers.delete('Authorization');
      } else if ('Authorization' in config.headers) {
        delete config.headers.Authorization;
      }
    }
  }
  return config;
});

// Response Interceptor for error handling
client.interceptors.response.use(
  (response) => response.data, // Strip the axios wrapper
  (error) => {
    console.error('[API Error]:', error.response?.data || error.message);

    // Handle network failure (backend down, connection refused, or genuine timeout)
    if (!error.response) {
      let message;
      if (error.code === 'ECONNABORTED' || error.message?.toLowerCase().includes('timeout')) {
        message = 'Request timed out — the server is taking too long to respond. Please try again.';
      } else if (
        error.code === 'ERR_NETWORK' ||
        error.code === 'ECONNREFUSED' ||
        error.message?.toLowerCase().includes('network error')
      ) {
        message = 'Cannot reach the server. Please check that the backend is running.';
      } else {
        message = `Network error: ${error.message || 'unknown error'}`;
      }
      const err = new Error(message);
      err.status = 503;
      return Promise.reject(err);
    }

    const message = error.response?.data?.detail || error.message || 'An unknown error occurred';

    // Create a custom error that preserves the HTTP status code
    const err = new Error(message);
    err.status = error.response?.status;
    return Promise.reject(err);
  }
);

// Dashboard APIs
export const getDashboardData = () => client.get('/api/dashboard');
export const getDashboardSummary = () => client.get('/api/dashboard/summary');
export const login = (credentials) => client.post('/api/auth/login', credentials);
export const register = (payload) => client.post('/api/auth/register', payload);
export const verifyAdmin = () => client.post('/api/verify_admin');

// Stops
export const getStops = () => client.get('/api/stops');

// Demand Prediction
export const predictDemand = (data) => client.post('/api/predict_demand', data);

// Trip Planning
export const planTrip = (data, signal) => {
  console.log('[API Client] planTrip called with:', data);
  const { accessToken } = getAuthSession();
  console.log('[API Client] Token present:', !!accessToken);
  
  return client.post('/api/plan_trip', data, { signal });
};
export const getAlternatives = (data) => client.get(`/api/navigation/alternatives?source_id=${data.source_id}&destination_id=${data.destination_id}`);

// Fleet Optimization
export const optimizeFleet = (data) => client.post('/api/fleet/optimize', data);

// Routes
export const getRoutes = (skip = 0, limit = 100) => client.get(`/api/routes?skip=${skip}&limit=${limit}`);

// Alerts
export const getAlerts = () => client.get('/api/alerts');

// Schedule Status (city-level service frequency — NOT per-user dispatch)
export const getScheduleStatus = () => client.get('/api/schedule_status');

// Passenger journey history (JWT-protected)
export const getJourneyHistory = (page = 1, limit = 20) =>
  client.get(`/api/passenger/history?page=${page}&limit=${limit}`);

export const getPredictions = (skip = 0, limit = 50) => client.get(`/api/predictions?skip=${skip}&limit=${limit}`);

// System
export const getSystemMetrics = () => client.get('/api/system/metrics');
export const getGraphDiagnostics = () => client.get('/api/graph_diagnostics');

// AI Transit Intelligence APIs
export const getDashboardUtilization = () => client.get('/api/dashboard/utilization');
export const getDashboardForecastTrend = (routeId) => client.get(`/api/dashboard/forecast_trend/${routeId}`);
export const getDashboardHeatmap = () => client.get('/api/dashboard/heatmap');

// Stop Arrivals (ETA)
export const getStopArrivals = (stopId) => client.get(`/api/stops/${stopId}/arrivals`);

// Nearby Routes
export const getNearbyRoutes = (lat, lon, radius = 5) => client.get(`/api/routes/nearby?lat=${lat}&lon=${lon}&radius=${radius}`);

// AI Assistant
export const aiAssistantChat = (message, sessionId) => client.post('/api/ai-assistant/chat', { message, session_id: sessionId });
export const clearAssistantContext = (sessionId) => client.post(`/api/ai-assistant/clear-context?session_id=${sessionId}`);

export default client;
