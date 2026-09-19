import {
  HealthResponse,
  ForecastResponse,
  ModelMetricsResponse,
  ModelInfoResponse,
  OptimizationRequest,
  OptimizationResponse,
  SimulationRequest,
  SimulationResponse,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      try {
        const errorJson = await response.json();
        if (typeof errorJson.detail === 'string') {
          errorDetail = errorJson.detail;
        } else if (Array.isArray(errorJson.detail)) {
          errorDetail = errorJson.detail.map((err: any) => err.msg || JSON.stringify(err)).join(', ');
        }
      } catch {
        errorDetail = response.statusText || errorDetail;
      }
      throw new ApiError(errorDetail, response.status);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network / connection error
    throw new ApiError(
      'Backend unavailable — start the GridMind FastAPI server.',
      0,
      err
    );
  }
}

export const api = {
  getHealth: (): Promise<HealthResponse> => {
    return request<HealthResponse>('/api/health');
  },

  getForecast: (startTime?: string, horizonHours: number = 24): Promise<ForecastResponse> => {
    const params = new URLSearchParams();
    if (startTime) params.append('start_time', startTime);
    params.append('horizon_hours', horizonHours.toString());
    return request<ForecastResponse>(`/api/forecast?${params.toString()}`);
  },

  getModelMetrics: (): Promise<ModelMetricsResponse> => {
    return request<ModelMetricsResponse>('/api/model/metrics');
  },

  getModelInfo: (): Promise<ModelInfoResponse> => {
    return request<ModelInfoResponse>('/api/model/info');
  },

  optimize: (payload: OptimizationRequest = {}): Promise<OptimizationResponse> => {
    return request<OptimizationResponse>('/api/optimize', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  simulate: (payload: SimulationRequest): Promise<SimulationResponse> => {
    return request<SimulationResponse>('/api/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
