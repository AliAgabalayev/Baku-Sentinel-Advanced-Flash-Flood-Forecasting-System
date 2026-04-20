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
