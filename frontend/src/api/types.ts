/**
 * GridMind API Type Contracts
 * Synchronized with FastAPI schemas.
 */

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  model_loaded: boolean;
}

export interface ForecastPoint {
  timestamp: string;
  predicted_load_mw: number;
}

export interface ForecastResponse {
  horizon_hours: number;
  unit: string;
  model: string;
  forecast: ForecastPoint[];
}

export interface ModelMetricsResponse {
  model: string;
  mae_mw: number;
  rmse_mw: number;
  mape_percent: number;
  test_samples: number;
}

export interface PeriodInfo {
  start: string;
  end: string;
}

export interface ModelInfoResponse {
  model_name: string;
  model_type: string;
  feature_count: number;
  feature_names: string[];
  training_period: PeriodInfo;
  test_period: PeriodInfo;
  training_sample_count: number;
  test_sample_count: number;
  data_source: string;
  weather_data_provenance: string;
}

export interface OptimizationRequest {
  start_time?: string | null;
  enforce_operating_ceiling?: boolean;
  time_limit_seconds?: number;
}

export interface OptimizationResponse {
  status: string;
  horizon_hours: number;
  time_step_minutes: number;
  baseline_peak_kw: number;
  optimized_peak_kw: number;
  peak_reduction_kw: number;
  peak_reduction_percent: number;
  baseline_total_energy_kwh: number;
  optimized_total_energy_kwh: number;
  hourly_load_before_kw: number[];
  hourly_load_after_kw: number[];
  slot_load_before_kw?: number[] | null;
  slot_load_after_kw?: number[] | null;
  appliance_schedule: {
    geyser?: number[];
    washing_machine?: number[];
    device_charging?: number[];
    [key: string]: number[] | undefined;
  };
  transformer_capacity_kw: number;
  operating_ceiling_kw: number;
  maximum_headroom_kw: number;
  minimum_headroom_kw: number;
  solver_runtime_seconds: number;
  details?: string | null;
}

export interface SimulationRequest {
  total_students?: number;
  transformer_capacity_kw?: number;
  operating_ceiling_kw?: number;
  baseline_power_kw?: number;
  min_baseline_kw?: number;
  max_baseline_kw?: number;
  geyser_quantity?: number;
  geyser_power_kw?: number;
  geyser_max_simultaneous?: number;
  washing_machine_quantity?: number;
  washing_machine_power_kw?: number;
  washing_machine_max_simultaneous?: number;
  device_charging_quantity?: number;
  device_charging_power_kw?: number;
  device_charging_max_simultaneous?: number;
  start_time?: string | null;
  time_limit_seconds?: number;
}

export interface ScenarioMetrics {
  unoptimized_peak_kw: number;
  optimized_peak_kw: number;
  peak_reduction_kw: number;
  peak_reduction_percent: number;
  total_energy_kwh: number;
}

export interface ScenarioComparison {
  baseline_peak_kw: number;
  simulated_peak_kw: number;
  peak_difference_kw: number;
  peak_difference_percent: number;
  baseline_energy_kwh: number;
  simulated_energy_kwh: number;
  energy_difference_kwh: number;
  is_feasible: boolean;
  solver_status: string;
}

export interface SimulationResponse {
  status: string;
  is_feasible: boolean;
  baseline_scenario: ScenarioMetrics;
  simulated_scenario: ScenarioMetrics;
  comparison: ScenarioComparison;
  forecasted_demand_mw: number[];
  hourly_baseline_load_kw: number[];
  hourly_load_before_kw: number[];
  hourly_load_after_kw: number[];
  slot_load_before_kw?: number[] | null;
  slot_load_after_kw?: number[] | null;
  appliance_schedule: {
    geyser?: number[];
    washing_machine?: number[];
    device_charging?: number[];
    [key: string]: number[] | undefined;
  };
  transformer_capacity_kw: number;
  operating_ceiling_kw: number;
  maximum_headroom_kw: number;
  minimum_headroom_kw: number;
  solver_runtime_seconds: number;
  scenario_parameters_applied: Record<string, any>;
  details?: string | null;
}
