"""Hostel Domain Models and Configuration Schemas for GridMind Digital Twin."""

from typing import Dict, List, Optional, Any, Literal
import json
from pathlib import Path
from pydantic import BaseModel, Field, model_validator, field_validator


class FacilityConfig(BaseModel):
    """Facility physical infrastructure and transformer specifications."""

    total_students: int = Field(500, description="Total resident student population", gt=0)
    total_rooms: int = Field(250, description="Total dormitory rooms in facility", gt=0)
    transformer_capacity_kw: float = Field(500.0, description="Max physical rated transformer capacity in kW", gt=0.0)
    operating_ceiling_kw: float = Field(450.0, description="Safe operating threshold in kW (typically 90% of capacity)", gt=0.0)
    baseline_power_kw: float = Field(25.0, description="Constant unshiftable baseline power (pumps, network, security) in kW", ge=0.0)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "FacilityConfig":
        """Ensure operating ceiling does not exceed physical transformer capacity."""
        if self.operating_ceiling_kw > self.transformer_capacity_kw:
            raise ValueError(
                f"Operating ceiling ({self.operating_ceiling_kw} kW) cannot exceed "
                f"transformer capacity ({self.transformer_capacity_kw} kW)."
            )
        if self.baseline_power_kw >= self.operating_ceiling_kw:
            raise ValueError(
                f"Baseload ({self.baseline_power_kw} kW) must be strictly below "
                f"operating ceiling ({self.operating_ceiling_kw} kW)."
            )
        return self


class TariffConfig(BaseModel):
    """Time-of-Use (ToU) electricity billing rates."""

    currency: str = Field("INR", description="Tariff currency denomination")
    unit: str = Field("kWh", description="Energy billing unit")
    off_peak_rate: float = Field(5.5, description="Tariff rate during off-peak hours (per kWh)", ge=0.0)
    standard_rate: float = Field(8.0, description="Tariff rate during standard hours (per kWh)", ge=0.0)
    peak_rate: float = Field(12.0, description="Tariff rate during peak demand hours (per kWh)", ge=0.0)
    peak_hours: List[int] = Field(default_factory=lambda: [18, 19, 20, 21, 22], description="Hours of the day classified as peak")

    @field_validator("peak_hours")
    @classmethod
    def validate_peak_hours(cls, hours: List[int]) -> List[int]:
        for h in hours:
            if not 0 <= h <= 23:
                raise ValueError(f"Peak hour {h} is invalid; must be between 0 and 23.")
        return sorted(list(set(hours)))


class InflexibleLoadProfile(BaseModel):
    """Non-shiftable background load (corridor lights, study rooms, refrigeration)."""

    load_type: str = Field(..., description="Unique identifier for the inflexible load")
    display_name: str = Field(..., description="Human-readable load name")
    power_kw: float = Field(..., description="Total aggregate power draw in kW", gt=0.0)
    active_hours: List[int] = Field(..., description="Hours of the day when this load is active")
    priority: str = Field("critical", description="Priority level")

    @field_validator("active_hours")
    @classmethod
    def validate_hours(cls, hours: List[int]) -> List[int]:
        for h in hours:
            if not 0 <= h <= 23:
                raise ValueError(f"Hour {h} must be between 0 and 23.")
        return sorted(list(set(hours)))


class FlexibleApplianceProfile(BaseModel):
    """Configurable shiftable appliance category (geysers, washing machines, EV chargers)."""

    appliance_type: str = Field(..., description="Appliance identifier (e.g. 'geyser')")
    display_name: str = Field(..., description="Display label (e.g. 'Water Heaters / Geysers')")
    quantity: int = Field(..., description="Total unit count in facility", gt=0)
    power_kw: float = Field(..., description="Power rating per individual unit in kW", gt=0.0)
    runtime_hours: float = Field(..., description="Operational cycle duration in hours", gt=0.0, le=24.0)
    earliest_start_hour: int = Field(0, description="Earliest permissible starting hour (0-23)", ge=0, le=23)
    latest_finish_hour: int = Field(24, description="Latest mandatory completion hour (1-24)", ge=1, le=24)
    maximum_simultaneous_units: int = Field(..., description="Max units permitted to run concurrently", gt=0)
    shift_penalty_per_hour: float = Field(1.0, description="User inconvenience cost per hour shifted from preferred start", ge=0.0)
    preferred_start_hour: Optional[int] = Field(None, description="Default unshifted user start hour", ge=0, le=23)
    priority: str = Field("medium", description="Priority classification ('high', 'medium', 'low')")
    flexible: bool = Field(True, description="Whether appliance can be shifted by scheduler")

    @model_validator(mode="after")
    def validate_appliance_constraints(self) -> "FlexibleApplianceProfile":
        """Validate operational window, runtime feasibility, and concurrency limits."""
        # 1. Operating window bounds
        if self.earliest_start_hour >= self.latest_finish_hour:
            raise ValueError(
                f"Earliest start ({self.earliest_start_hour}:00) must be strictly earlier than "
                f"latest finish ({self.latest_finish_hour}:00)."
            )

        # 2. Window width vs runtime
        window_duration = float(self.latest_finish_hour - self.earliest_start_hour)
        if self.runtime_hours > window_duration:
            raise ValueError(
                f"Runtime duration ({self.runtime_hours}h) exceeds available operating window "
                f"({window_duration}h between {self.earliest_start_hour}:00 and {self.latest_finish_hour}:00)."
            )

        # 3. Simultaneous units limit
        if self.maximum_simultaneous_units > self.quantity:
            raise ValueError(
                f"Maximum simultaneous units ({self.maximum_simultaneous_units}) cannot exceed "
                f"total appliance quantity ({self.quantity})."
            )

        # 4. Preferred start hour within window
        if self.preferred_start_hour is not None:
            if not (self.earliest_start_hour <= self.preferred_start_hour <= (self.latest_finish_hour - self.runtime_hours)):
                raise ValueError(
                    f"Preferred start hour ({self.preferred_start_hour}:00) must allow completion "
                    f"before latest finish ({self.latest_finish_hour}:00) given runtime {self.runtime_hours}h."
                )

        return self

    @property
    def max_concurrent_power_kw(self) -> float:
        """Maximum possible instantaneous load when capped by simultaneous unit limit."""
        return round(self.maximum_simultaneous_units * self.power_kw, 3)

    @property
    def total_energy_requirement_kwh(self) -> float:
        """Total aggregate daily electrical work required for this appliance fleet."""
        return round(self.quantity * self.power_kw * self.runtime_hours, 3)


class GridScalingConfig(BaseModel):
    """Methodology parameters for scaling utility-scale grid forecasts down to hostel baseline."""

    method: Literal["min_max_normalized", "per_capita", "capacity_fraction"] = Field(
        "min_max_normalized",
        description="Scaling formulation: min-max normalization, per-capita residential demand, or capacity fraction",
    )
    min_baseline_kw: float = Field(25.0, description="Minimum hostel base load during dormant night hours (kW)", ge=0.0)
    max_baseline_kw: float = Field(125.0, description="Maximum hostel base load during peak wake hours (kW)", gt=0.0)
    per_capita_base_kw: float = Field(0.20, description="Average unshiftable demand per resident student (kW/student)", gt=0.0)
    capacity_fraction: float = Field(0.25, description="Target mean baseline load as a fraction of operating ceiling", gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_scaling_bounds(self) -> "GridScalingConfig":
        if self.min_baseline_kw >= self.max_baseline_kw:
            raise ValueError(
                f"min_baseline_kw ({self.min_baseline_kw} kW) must be strictly less than "
                f"max_baseline_kw ({self.max_baseline_kw} kW)."
            )
        return self


class HostelConfig(BaseModel):
    """Root configuration container for the GridMind Hostel Digital Twin."""

    metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "description": "GridMind 500-Student Hostel Digital Twin Configuration",
            "is_synthetic_assumption": True,
            "version": "1.0.0",
        }
    )
    facility: FacilityConfig = Field(default_factory=FacilityConfig)
    tariff: TariffConfig = Field(default_factory=TariffConfig)
    scaling: GridScalingConfig = Field(default_factory=GridScalingConfig)
    inflexible_loads: Dict[str, InflexibleLoadProfile] = Field(default_factory=dict)
    flexible_appliances: Dict[str, FlexibleApplianceProfile] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_total_facility_headroom(self) -> "HostelConfig":
        """Verify that constant baseload plus maximum scaling fits within operating ceiling."""
        if self.scaling.max_baseline_kw >= self.facility.operating_ceiling_kw:
            raise ValueError(
                f"Max baseline load ({self.scaling.max_baseline_kw} kW) reaches or exceeds "
                f"facility operating ceiling ({self.facility.operating_ceiling_kw} kW), leaving zero room for appliances."
            )
        return self

    @classmethod
    def load_from_file(cls, path: Path | str) -> "HostelConfig":
        """Load and validate hostel configuration from JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Hostel configuration file not found at: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    def save_to_file(self, path: Path | str) -> None:
        """Serialize configuration to formatted JSON."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def create_default_500_student_hostel(cls) -> "HostelConfig":
        """Factory for standardized 500-student university hostel benchmark."""
        facility = FacilityConfig(
            total_students=500,
            total_rooms=250,
            transformer_capacity_kw=500.0,
            operating_ceiling_kw=450.0,
            baseline_power_kw=25.0,
        )

        tariff = TariffConfig(
            currency="INR",
            unit="kWh",
            off_peak_rate=5.5,
            standard_rate=8.0,
            peak_rate=12.0,
            peak_hours=[18, 19, 20, 21, 22],
        )

        scaling = GridScalingConfig(
            method="min_max_normalized",
            min_baseline_kw=25.0,
            max_baseline_kw=125.0,
            per_capita_base_kw=0.20,
        )

        inflexible = {
            "corridor_lighting": InflexibleLoadProfile(
                load_type="corridor_lighting",
                display_name="Corridor & Security Lighting",
                power_kw=20.0,
                active_hours=[17, 18, 19, 20, 21, 22, 23, 0],
                priority="critical",
            ),
            "dormitory_ventilation": InflexibleLoadProfile(
                load_type="dormitory_ventilation",
                display_name="Study Rooms & Ventilation",
                power_kw=15.0,
                active_hours=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
                priority="high",
            ),
        }

        flexible = {
            "geyser": FlexibleApplianceProfile(
                appliance_type="geyser",
                display_name="Water Heaters / Geysers",
                quantity=120,
                power_kw=2.0,
                runtime_hours=0.5,  # 30 minutes
                earliest_start_hour=5,
                latest_finish_hour=22,
                maximum_simultaneous_units=60,
                shift_penalty_per_hour=2.0,
                preferred_start_hour=6,
                priority="high",
                flexible=True,
            ),
            "washing_machine": FlexibleApplianceProfile(
                appliance_type="washing_machine",
                display_name="Common Laundry Machines",
                quantity=20,
                power_kw=0.7,
                runtime_hours=1.0,  # 60 minutes
                earliest_start_hour=8,
                latest_finish_hour=23,
                maximum_simultaneous_units=10,
                shift_penalty_per_hour=1.0,
                preferred_start_hour=10,
                priority="medium",
                flexible=True,
            ),
            "device_charging": FlexibleApplianceProfile(
                appliance_type="device_charging",
                display_name="Laptops / Phones / EV Scooters",
                quantity=300,
                power_kw=0.1,
                runtime_hours=2.0,  # 120 minutes
                earliest_start_hour=0,
                latest_finish_hour=24,
                maximum_simultaneous_units=150,
                shift_penalty_per_hour=0.5,
                preferred_start_hour=20,
                priority="medium",
                flexible=True,
            ),
        }

        return cls(
            facility=facility,
            tariff=tariff,
            scaling=scaling,
            inflexible_loads=inflexible,
            flexible_appliances=flexible,
        )
