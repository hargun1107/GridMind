# GridMind: Data Provenance & Synthetic Data Governance Specification

> **Governance Directive:**  
> For the GridMind Hackathon submission and production roadmap, all data assets must explicitly distinguish between **real external utility measurements** and **synthetic / simulated assumptions**. Synthetic data must **never** be presented or documented as physical ground-truth sensor readings.

---

## 1. Data Asset Taxonomy Summary

| Asset | File Path | Nature | Origin / Ground Truth Status |
| :--- | :--- | :--- | :--- |
| **Grid Electricity Demand** | [`data/raw/electricity_real_hourly.csv`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/raw/electricity_real_hourly.csv) | **Real External Data** | PJM Interconnection Regional Transmission Organization (PJME Zone). Real physical utility grid hourly load. |
| **Ambient Weather Series** | [`data/raw/weather_hourly.csv`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/raw/weather_hourly.csv) | **Synthetic Development Data** | Deterministic meteorological model aligned to PJM timestamps for feature pipeline development. **Not** physical sensor data. |
| **Hostel Facility & Load Config** | [`data/sample/hostel_config_default.json`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/sample/hostel_config_default.json) | **Synthetic Configurable Model** | Engineering model representing a 500-student university hostel with realistic appliance ratings and flexibility windows. |
| **Engineered Feature Matrix** | In-memory / `data/processed/` | **Derived / Engineered** | Deterministic transformations (cyclical trigonometric, historical lags, rolling statistics, degree days) derived from the above. |

---

## 2. Real External Data: PJM Hourly Electricity Load

### 2.1 Source & Lineage
* **Provider:** PJM Interconnection LLC (Regional Transmission Organization serving Delaware, Illinois, Indiana, Kentucky, Maryland, Michigan, New Jersey, North Carolina, Ohio, Pennsylvania, Tennessee, Virginia, West Virginia, and DC).
* **Dataset Identifier:** PJM East Region Hourly Load (`PJME_hourly.csv`).
* **Repository Source:** Publicly mirrored at [archd3sai/Hourly-Energy-Consumption-Prediction GitHub Repository](https://raw.githubusercontent.com/archd3sai/Hourly-Energy-Consumption-Prediction/master/PJME_hourly.csv).
* **Ingestion Script:** [`data/download_data.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/download_data.py) function `download_pjm_electricity_data`.

### 2.2 Temporal Coverage & Record Counts
* **Active Slice:** 35,000 consecutive hourly records (bounded by `max_rows=35000` to ensure rapid, lean training while retaining multi-year seasonality).
* **Observation Start:** `2014-08-05 13:00:00`
* **Observation End:** `2018-08-03 00:00:00`
* **Coverage Span:** 4.0 continuous calendar years (capturing summer heat peaks, winter heating peaks, holiday load reductions, and diurnal cycling).
* **Unit of Measure:** Megawatts (`grid_load_mw`), converted from raw `PJME_MW`.

### 2.3 Preprocessing & Transformations Performed
The raw energy time series undergoes strict validation in [`ml/preprocessing/cleaner.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/ml/preprocessing/cleaner.py):
1. **Timestamp Parsing:** String timestamps parsed to UTC-compatible ISO standard `YYYY-MM-DD HH:MM:SS`.
2. **Chronological Sorting & Deduplication:** Any daylight-saving time duplicate timestamps are resolved by retaining the first occurrence.
3. **Hourly Frequency Regularization:** Missing intervals detected and regularized using `pandas.date_range(..., freq='h')`.
4. **Missing Value Imputation:** Small gaps ($\le 3$ hours) filled using linear interpolation; remaining boundary edges imputed with backward and forward fills.
5. **Physical Sanity Enforcement:** All load values clamped to non-negative domain ($\ge 0.0\text{ MW}$).
6. **Autoregressive Alignment:** Maximum lag window is 168 hours (1 week), dropping the initial 168 rows to yield **34,832 valid feature-complete records**.
7. **Chronological Train/Test Partitioning:** Strict temporal split with no future data leakage (80% Train = 27,865 records; 20% Test = 6,967 records).

---

## 3. Synthetic Data: Ambient Weather Time Series

### 3.1 Motivation & Method
* **Current Status:** **Synthetic / Deterministic Development Data**.
* **Generation Engine:** [`data/download_data.py`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/download_data.py) function `generate_aligned_weather_data`.
* **Alignment:** Uses the exact timestamp index of the PJM electricity dataset.
* **Deterministic Formulation:**
  * Annual seasonal base: $T_{\text{annual}} = 16.0 + 12.0 \cdot \sin\left(\frac{2\pi (\text{dayofyear} - 105)}{365.25}\right)$
  * Diurnal oscillation: $T_{\text{daily}} = 5.5 \cdot \sin\left(\frac{2\pi (\text{hour} - 9)}{24}\right)$
  * Noise component: $\mathcal{N}(0, 1.8^\circ\text{C})$ with fixed random seed (`seed=42`).
  * Relative humidity: Inversely correlated with temperature, bounded between $20.0\%$ and $98.0\%$.
  * Degree Days: Cooling Degree Days ($\text{CDD} = \max(0, T - 18.0)$) and Heating Degree Days ($\text{HDD} = \max(0, 18.0 - T)$).

### 3.2 Known Limitations & Non-Claims
* **No Ground-Truth Sensor Claim:** This weather dataset does **not** represent verified historical NOAA or local airport meteorological station readings.
* **Purpose:** Built to establish the end-to-end data pipeline contract, test thermodynamic feature engineering (`thi_discomfort_index`, degree days), and validate that the ML model can exploit temperature sensitivity without requiring third-party API keys during initial hackathon judging.
* **Future Upgrade Path:** Drop-in replacement with real historical ERA5-Land reanalysis data or Open-Meteo Historical Weather API via synchronous timestamp lookup.

---

## 4. Synthetic Configurable Model: Hostel Digital Twin

### 4.1 Specification & Purpose
* **Configuration File:** [`data/sample/hostel_config_default.json`](file:///c:/Users/hargu/OneDrive/Desktop/projects/GridMind/data/sample/hostel_config_default.json)
* **Digital Twin Representation:** A standardized student residential hostel housing **500 students across 250 rooms**.
* **Grid Coupling:** Configured with a 500 kW dedicated transformer capacity and a 450 kW safe operating threshold to prevent equipment thermal overload.
* **Tariff Structure:** Time-of-Use (ToU) tariff mirroring industrial/institutional electricity billing in India:
  * Off-Peak Rate: ₹5.5 / kWh
  * Standard Rate: ₹8.0 / kWh
  * Peak Rate: ₹12.0 / kWh (Peak hours: 18:00 – 22:00)

### 4.2 Appliance Catalog & Flexibility Taxonomy

| Appliance Category | Count | Power Rating (kW) | Operational Duration | Flexibility Status | User Deadline / Operating Window | Optimization Objective |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Air Conditioners (Dormitories)** | 180 | 1.5 kW | Continuous / Dynamic | **Inflexible** | 14:00–16:00, 21:00–05:00 | Base critical cooling comfort load |
| **Water Heaters / Geysers** | 120 | 2.0 kW | 30 minutes | **Flexible** | 05:00–22:00 (preferred 06:00–09:00, 18:00–21:00) | Shift load away from 18:00–22:00 peak tariff |
| **Laundry Washing Machines** | 20 | 0.7 kW | 60 minutes | **Flexible** | 08:00–23:00 (preferred 10:00–16:00) | Schedule into afternoon solar/demand troughs |
| **Personal Devices / EV Scooters** | 300 | 0.1 kW | 120 minutes | **Flexible** | 00:00–23:59 (preferred 19:00–23:00) | Buffer charging during cheap off-peak hours |
| **Corridor & Study Room Lighting** | 1 | 20.0 kW | Continuous | **Inflexible** | 17:00–01:00 | Safety and educational lighting (non-shiftable) |

### 4.3 Provenance Note on Hostel Data
The hostel layout, appliance counts, and operational hours are **synthetic engineering assumptions** derived from standard university hostel infrastructure benchmarks. They are fully parameterized in JSON and can be customized per facility without altering the optimization algorithms.

---

## 5. Governance Checklist for Hackathon Submissions & Evaluation

When presenting or demonstrating GridMind:
1. **Always disclose:** "The demand forecaster is trained on real utility-scale electricity grid data from PJM, validated against synthetic development weather data, and applied to a synthetic 500-student hostel digital twin."
2. **Never claim:** "Our weather dataset is recorded from an on-site IoT weather station."
3. **Never claim:** "Our hostel sub-metered traces are physical smart meter sensor logs."
4. **Architectural Validation:** The ML pipeline, feature extractors, and constraint programming optimization engine operate on standard time-indexed data schemas, ensuring 100% drop-in compatibility with real physical smart meters when deployed in production.
