"""Grid Forecast to Hostel Baseload Scaling Service.

Provides a mathematically grounded, deterministic mapping from utility-scale
transmission grid forecasts (Megawatts) down to a university residential hostel's
distribution-level baseload (Kilowatts).

Methodology & Assumptions:
--------------------------
1. Scale Disparity:
   Regional grid load (PJM) is 30,000–45,000 MW, serving millions of industrial,
   commercial, and residential consumers across multiple states. A university hostel
   operates at 0–500 kW capacity.

2. Diurnal Momentum Coupling:
   A student residential facility's waking, lighting, and ambient thermal patterns
   exhibit strong diurnal synchrony with the regional utility grid. Peak student activity
   (late morning study and evening social hours) coincides with regional demand peaks.

3. Configurable Formulations:
   a. 'min_max_normalized' (Default):
      Extracts the normalized diurnal shape of the grid forecast in [0, 1] and scales
      it across the hostel's verified dormant (night) and active (day) baseline bounds:
      P_hostel(t) = min_kw + ((P_grid(t) - min_grid) / (max_grid - min_grid)) * (max_kw - min_kw)

   b. 'per_capita':
      Allocates an average non-shiftable per-student power allowance (e.g., 0.20 kW/student)
      multiplied by resident population (500 students = 100 kW mean) and modulated by
      the normalized grid index P_grid(t) / mean(P_grid).

   c. 'capacity_fraction':
      Anchors hostel baseload as a calibrated target fraction of the transformer
      operating ceiling (e.g., 25% of 450 kW = 112.5 kW mean) modulated by the grid curve.
"""

from typing import List, Optional
import numpy as np

from backend.app.models.hostel import GridScalingConfig, FacilityConfig


class ScalingValidationError(Exception):
    """Raised when forecast input or scaling parameters are invalid."""
    pass


def scale_grid_forecast_to_hostel_baseline(
    grid_forecast_mw: List[float],
    scaling_config: GridScalingConfig,
    facility_config: Optional[FacilityConfig] = None,
) -> List[float]:
    """Scale a 24-hour utility grid load forecast (MW) to a hostel baseline curve (kW).

    Parameters
    ----------
    grid_forecast_mw : List[float]
        Array of utility load forecasts in Megawatts.
    scaling_config : GridScalingConfig
        Configured scaling parameters and methodology selection.
    facility_config : Optional[FacilityConfig]
        Hostel facility specs used for per-capita or ceiling-based methods.

    Returns
    -------
    List[float]
        Deterministic 24-hour hostel base demand series in Kilowatts (kW).
    """
    if not grid_forecast_mw:
        raise ScalingValidationError("Grid forecast series cannot be empty.")

    grid_arr = np.asarray(grid_forecast_mw, dtype=float)
    if (grid_arr <= 0.0).any():
        raise ScalingValidationError("All grid forecast values must be strictly positive (> 0 MW).")

    method = scaling_config.method

    if method == "min_max_normalized":
        min_g = float(np.min(grid_arr))
        max_g = float(np.max(grid_arr))
        spread = max_g - min_g

        if spread < 1e-5:
            # Flat forecast fallback: center at median baseline
            normalized = np.full_like(grid_arr, 0.5)
        else:
            normalized = (grid_arr - min_g) / spread

        scaled_kw = scaling_config.min_baseline_kw + normalized * (
            scaling_config.max_baseline_kw - scaling_config.min_baseline_kw
        )

    elif method == "per_capita":
        students = facility_config.total_students if facility_config else 500
        mean_g = float(np.mean(grid_arr))
        grid_index = grid_arr / max(mean_g, 1e-5)
        base_total = students * scaling_config.per_capita_base_kw
        scaled_kw = base_total * grid_index

    elif method == "capacity_fraction":
        ceiling = facility_config.operating_ceiling_kw if facility_config else 450.0
        mean_g = float(np.mean(grid_arr))
        grid_index = grid_arr / max(mean_g, 1e-5)
        target_mean = ceiling * scaling_config.capacity_fraction
        scaled_kw = target_mean * grid_index

    else:
        raise ScalingValidationError(f"Unknown scaling method: '{method}'")

    # Physical safety clamping: non-negative and capped below transformer ceiling if provided
    ceiling_limit = facility_config.operating_ceiling_kw if facility_config else 450.0
    scaled_clamped = np.clip(scaled_kw, scaling_config.min_baseline_kw, ceiling_limit * 0.95)

    return [round(float(val), 2) for val in scaled_clamped]
