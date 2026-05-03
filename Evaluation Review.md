# Baku Sentinel (Gale) - Evaluation Review

---

## Executive Summary

You’ve delivered an advanced flash flood forecasting system for Baku with sophisticated terrain-aware risk modeling. Your project stands out for its integration of terrain topology (0-200m elevation gradient), subsurface soil saturation tracking, and quantitative river discharge data. The 6-hourly granularity and compound flood definition, which combines river discharge with meteorological conditions, demonstrate production-grade hydrological modeling. You have successfully addressed Baku's unique risk factors: lowland coastal geography, impermeable urban surfaces, and the highly variable terrain that creates gravity-driven flood cascades.

---

## Detailed Assessment

### 1. Pipeline Completeness

**What's Implemented:**
- 9 src modules including specialized weather model
- API for data access (`api.py`)
- Database setup script (`setup_db.py`)
- Shell script for startup (`start.sh`)
- Frontend with 19 items including React components
- Models folder with saved artifacts
- Hybrid 30-day forecast (15-day live + 15-day climatological extension)

**Strengths:**
- **API endpoint** for programmatic access
- **Frontend** with React components (19 items)
- **Database setup** script for easy initialization
- **Shell script** for one-command startup
- **Hybrid forecast**: Live API + climatological extension
- 6-hourly granularity (resampled from hourly)

**Areas for Consideration:**
- Is the API documented (OpenAPI/Swagger)?
- How is the pipeline scheduled to refresh forecasts?

---

### 2. Data Quality Analysis

**What's Implemented:**
- Open-Meteo Flood API integration for river discharge
- Soil saturation tracking ("soil memory")
- Compound condition filtering (discharge + precipitation/humidity)
- Historical range validation

**Strengths:**
- **Soil saturation tracking** for "tipping point" prediction
- **Compound conditions** filter meteorological coincidence from genuine floods
- **River discharge threshold** (1.0 m³/s) empirically derived
- **Discharge from D-1 labels D** - prevents same-day lookahead leakage

**Areas for Consideration:**
- Are there automated quality checks with pass/warn/fail?
- How are missing discharge values handled?
- Is there gap detection for the 6-hourly data?

---

### 3. Statistical Reasoning

**What's Implemented:**
- Empirical threshold derivation (1.0 m³/s discharge)
- Compound condition logic (discharge + precip > 1mm OR humidity > 85%)
- Zone-specific analysis for Baku's topographic micro-zones
- Climate trend analysis

**Strengths:**
- **Empirical threshold** (1.0 m³/s) based on local drainage capacity
- **Compound conditions** statistically separate true floods from meteorological coincidence
- **Leakage prevention**: D-1 discharge labels D slots
- **Micro-zone forecasting** acknowledges Baku's terrain variability

**Areas for Consideration:**
- Were hypothesis tests performed on flood-day vs non-flood-day weather patterns?
- What statistical validation was performed on the 1.0 m³/s threshold?
- Were confidence intervals computed for predictions?

---

### 4. Prediction Model

**What's Implemented:**
- **Target**: `is_flood` (binary) - river_discharge > 1.0 m³/s + (precip > 1mm OR humidity > 85%)
- **Granularity**: 6-hourly (resampled from hourly)
- **Features**:
  - River discharge (Flood API)
  - Terrain topology (0-200m elevation)
  - Soil saturation (subsurface tracking)
  - Standard weather variables
- **Forecast Horizon**: 30 days (15-day live + 15-day climatological extension)
- **Zone-Specific**: Micro-zone forecasting for Baku's varied terrain

**Strengths:**
- **Terrain integration**: Elevation gradient creates "gravity-driven flood cascades"
- **Soil memory**: Tracks consecutive rainy days leading to saturation "tipping point"
- **Compound definition**: Discharge + meteorological conditions
- **6-hourly granularity**: Sub-daily prediction for flash flood timing
- **Zone-aware**: Different risk for different Baku districts
- **Leakage prevention**: Proper temporal labeling (D-1 → D)

**Areas for Consideration:**
- What ML models were used (Random Forest, XGBoost, etc.)?
- What are the model performance metrics (precision, recall, F1)?
- How many models were compared?
- Were confidence intervals provided?

---

### 5. Presentation Quality

**What's Implemented:**
- Comprehensive README (27KB) with detailed problem statement
- Frontend with React components (19 items)
- API for programmatic access
- Table of Contents with 17 sections
- Clear target variable definition table
- Stakeholder-focused explanation

**Strengths:**
- **27KB README** with exceptional detail
- **Frontend interface** for interactive use
- **API endpoint** for integration
- **Problem articulation**: "Systemic paralysis" of Baku's infrastructure
- **Stakeholder analysis**: Port ops, cargo planners, vessel operators
- **Micro-zone rationale**: Clear explanation of why blanket warnings fail

**Areas for Consideration:**
- Is the frontend deployed or local only?
- Are there example API calls in the documentation?

---

### 6. Code Quality

**What's Implemented:**
- 9 src modules with clear roles
- Feature engineering module (4KB)
- Weather model abstraction (4KB)
- Model training module (8KB)
- Pipeline orchestration (18KB)
- Prediction module (3KB)

**Strengths:**
- **Modular architecture**: Ingestion, features, model, prediction separated
- **Weather model abstraction** for different data sources
- **API layer** for external integration
- **Database setup script** for reproducibility
- **Startup script** for one-command launch

**Areas for Consideration:**
- Could benefit from type hints
- No evidence of unit tests
- Some modules are small (3-4KB) - could be consolidated

---

## Strengths

- **Terrain-Aware Modeling**: 0-200m elevation gradient creates flood cascades
- **Soil Memory Tracking**: Saturation "tipping point" prediction
- **Compound Flood Definition**: Discharge + meteorological conditions
- **6-Hourly Granularity**: Sub-daily flash flood timing
- **Micro-Zone Forecasting**: Different risk per Baku district
- **Leakage Prevention**: D-1 discharge labels D slots
- **Hybrid Forecast**: 15-day live + 15-day climatological extension
- **Frontend + API**: Both interactive and programmatic access
- **Empirical Thresholds**: 1.0 m³/s based on local drainage capacity

## Areas for Consideration (Research Questions)

1. **Model Details**: What ML models were used, and what are the performance metrics (precision, recall, F1)?

2. **Threshold Validation**: How was the 1.0 m³/s discharge threshold validated? Is there historical flood data confirming this threshold?

3. **Class Imbalance**: Flood days are rare. How was class imbalance handled in training?

4. **Zone Definition**: How are Baku's "topographic micro-zones" defined? How many zones are there?

5. **Climatological Extension**: How is the 15-day climatological extension (days 16-30) computed? Is it simple averaging or more sophisticated?

6. **Confidence Intervals**: Are prediction uncertainties provided? How do they vary over the 30-day horizon?

7. **Soil Saturation Model**: How is subsurface soil saturation estimated? Is it modeled or measured?

---

## Notable Findings

### Duration of Analysis
- **Historical Data**: 2020-01-01 to 2026-04-20 (6+ years)
- **Forecast Horizon**: 30 days (15 live + 15 climatological)
- **Granularity**: 6-hourly (resampled from hourly)
- **Geographic**: Baku metropolitan area with micro-zones

### Interesting Methodologies
1. **Terrain-Induced Flood Cascades**: Elevation gradient modeling
2. **Soil Saturation Memory**: Consecutive rainy day tracking
3. **Compound Flood Definition**: Discharge + meteorological conditions
4. **Empirical Discharge Threshold**: 1.0 m³/s from local drainage capacity
5. **6-Hourly Prediction**: Sub-daily granularity for flash floods
6. **Micro-Zone Forecasting**: District-level risk variation
7. **Hybrid Forecast Architecture**: Live API + climatological extension
8. **Leakage Prevention**: D-1 discharge labels D slots

### Data Coverage
- **Geographic**: Baku metropolitan area with micro-zones
- **Temporal**: 2020-2026 (6+ years), 30-day forecast horizon
- **Sources**: Open-Meteo Archive + Forecast + Flood APIs
- **Variables**: Weather + river discharge + terrain
- **Output**: 6-hourly binary flood risk per zone

---

## Key Files Reviewed

| File | Purpose |
|------|---------|
| `README.md` | 27KB comprehensive documentation |
| `src/pipeline.py` | Pipeline orchestration (18KB) |
| `src/model.py` | Model training (8KB) |
| `src/feature_engineering.py` | Feature engineering (4KB) |
| `src/weather_model.py` | Weather abstraction (4KB) |
| `src/predict.py` | Prediction inference (3KB) |
| `src/ingestion.py` | Data ingestion (9KB) |
| `api.py` | API endpoint (5KB) |
| `setup_db.py` | Database initialization (1KB) |
| `frontend/` | React web interface (19 items) |
| `models/` | Saved model artifacts |

---

*Teacher Assistant: Jannat Samadov*
*Evaluation Date: May 3, 2026*
