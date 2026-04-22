# Baku Sentinel: Advanced Flash Flood Forecasting System

## Executive Overview
Standard meteorological services typically focus on atmospheric events—predicting *if* it will rain. However, for a city like Baku, the critical question is not the rainfall itself, but the resulting inundation. Baku Sentinel integrates **terrain topology**, **subsurface saturation levels**, and **quantitative river discharge data** to predict localized flood events.

The core mission of Baku Sentinel is to answer:
> *Utilizing real-time precipitation forecasts and antecedent soil moisture data, what is the specific probability of flood-risk exceedance across Baku’s micro-zones over a 5-day horizon?*

---

## Operational Architecture
The system is designed as an end-to-end predictive pipeline that transforms raw meteorological forecasts into actionable risk intelligence.

1.  **Data Ingestion**: Simultaneous retrieval of Forecast (Open-Meteo) and Historical/Flood API data.
2.  **Sentinel Pipeline**: A unified feature engineering engine that applies identical transformations to both training and production data (e.g., lag features, rolling saturation indices).
3.  **Predictive Engine**: A binary classification model trained on engineered historical features.
4.  **Risk Output**: Generation of probabilistic scores and threshold-based alerts for each terrain zone.

**Flow:** `Forecast API` → `Data Pipeline` → `Model Prediction` → `Risk Analysis & Alerts`

### 30-Day Two-Phase Pipeline
```
┌─────────────────────────────────────────────────────────────────┐
│                  30-DAY FLOOD RISK FORECAST                      │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐           ┌──────────────────────┐
│   PHASE 1       │           │   PHASE 2             │
│   Days 1–15     │           │   Days 16–30          │
│                 │           │                       │
│ Open-Meteo      │    ──►    │ Our ML Model          │
│ Forecast API    │           │ (Weather Prediction)  │
│ (real data)     │           │ + Flood Risk Layer    │
└─────────────────┘           └──────────────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌──────────────────┐
              │  FLOOD RISK MAP  │
              │  Baku 3 Clusters │
              │  HIGH / MED / LOW│
              └──────────────────┘
```

---

## Ground Truth & Labeling Strategy
Rather than relying solely on subjective reports, Baku Sentinel employs a **quantitative proxy** for flood events. 

*   **Source**: Open-Meteo Flood API (`river_discharge`).
*   **Thresholding**: Days are labeled as `is_flood = 1` if the local river discharge exceeds a critical threshold of **1.0 m³/s**. 
*   **Target Creation**: This creates a robust ground truth dataset where hydraulic anomalies serve as the primary indicator of potential flood risk, allowing the model to learn the specific meteorological conditions that trigger these events.

---

## Geospatial Risk Stratification
The Baku metropolitan area is divided into three primary "Terrain Risk Zones" based on elevation and drainage potential.

| Zone | Designation | Elevation Profile | Risk Profile | Technical Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Zone A** | Lowland Core | 0–5 m a.s.l. | 🔴 CRITICAL | Coastal depression; primary accumulation point for regional runoff. |
| **Zone B** | Mid-Slope Belt | 20–60 m a.s.l. | 🟡 MODERATE | Transitional slope; functions as the primary runoff generation zone. |
| **Zone C** | Upland Plateau | 100–200 m a.s.l. | 🟢 STABLE | Elevated plateau; rapid runoff with minimal local standing water risk. |

### Hydrological Cascade
The model accounts for gravity-driven water transport:
**Upland Inputs (Zone C) → Slope Accumulation (Zone B) → Lowland Inundation (Zone A)**

---

## Analytical Feature Set (Feature Engineering)
The following variables are ingested from the Open-Meteo API to build the multi-dimensional feature space.

| Variable Category | Technical Field | Model Relevance |
| :--- | :--- | :--- |
| **Hydrological Input** | `precipitation_sum/hourly` | Primary driver; intensity mapping for drainage overload. |
| **Saturation State** | `soil_moisture_0_to_27cm` | Antecedent conditions; defines infiltration capacity. |
| **Surface Integrity** | `soil_temperature_0cm` | Detection of frozen ground (100% runoff scenarios). |
| **Thermal State** | `temperature_2m_max/min` | Snowmelt kinetics and evaporation rates. |
| **Water Budget** | `et0_fao_evapotranspiration` | Net daily water gain/loss tracking. |
| **Atmospheric State** | `relative_humidity_2m` | Refines ET accuracy and moisture flux. |
| **Cryospheric Risk** | `snow_depth/fall_sum` | Tracking delayed release of water from snowpack. |

---

# Flood Forecasting Models: System Specifications

## Model 1: Feature Engineering Plan & Classification Model

1. Dataset History Length
* 6 years

2. Dataset Granularity
* Daily (with hourly components aggregated for specific features like precipitation and rainfall intensity).

3. Initial Version of Features
* Raw API Inputs:
  * `precipitation_hourly` & `precipitation_daily`
  * `soil_moisture` (0_1cm, 1_3cm, 3_9cm, 9_27cm)
  * `soil_temperature_0cm`
  * Temperature (`temp_max`, `temp_min`, `temp_mean`)
  * `evapotranspiration`
  * `relative_humidity`
  * `wind_speed`
  * `snow_depth` & `snowfall_sum`
  * `surface_pressure`
* Static Terrain Features:
  * `zone_id` (A, B, or C)
  * `elevation_mean`, `slope_mean`, `impervious_ratio`, `watershed_area`
* Engineered Features: 
  * Soil Saturation Index (SSI)
  * Rainfall Intensity Factor (RIF)
  * Cumulative Rainfall Windows (3-day, 7-day, 14-day rolling)
  * Snowmelt Load (SML)
  * Net (Effective) Precipitation
  * Frozen Ground Factor (FGF)
  * Zone Cascade Signal (Cascade Risk)
  * Lag Features (e.g., `precip_lag_1d`, `SSI_lag_1d`)

4. Target Variable
* `flood_risk` (0 or 1): A rule-based binary label created by the system. A day/zone is labeled '1' (Flood risk PRESENT) only if multiple calculated conditions are met simultaneously (e.g., SSI > 0.80, net precipitation > 20mm, unfrozen ground, etc.).

5. Prediction Horizon
* 1 month (30 days total, structured as a Two-Phase Pipeline: Days 1–15 direct forecast and Days 16–30 predicted weather forecast).

---

## Model 2: Baku Sentinel 

1. Dataset History Length
* 6 years

2. Dataset Granularity
* Daily (with hourly components utilized, e.g., `precipitation_sum/hourly` and net daily water budgets).

3. Initial Version of Features
* Raw API Inputs (Open-Meteo):
  * Hydrological Input: `precipitation_sum/hourly`
  * Saturation State: `soil_moisture_0_to_27cm`
  * Surface Integrity: `soil_temperature_0cm`
  * Thermal State: `temperature_2m_max/min`
  * Water Budget: `et0_fao_evapotranspiration`
  * Atmospheric State: `relative_humidity_2m`
  * Cryospheric Risk: `snow_depth/fall_sum`
* Engineered Features:
  * Unified "Sentinel Pipeline" utilizing lag features and rolling saturation indices. 
  * Terrain Topology zones (Zone A, B, C).

4. Target Variable
* `is_flood` (0 or 1): A quantitative proxy target based on the Open-Meteo Flood API. A day is labeled '1' if the local river discharge exceeds a critical threshold of 1.0 m³/s.

5. Prediction Horizon
* 1 month (30 days total, structured as a Two-Phase Pipeline: Days 1–15 direct forecast and Days 16–30 predicted weather forecast).
