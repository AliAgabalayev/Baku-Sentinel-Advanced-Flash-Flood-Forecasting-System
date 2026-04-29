# BAKU SENTINEL
## Flash Flood Forecasting System

**Daily Project Briefs — Days 1 through 11**
Team GALE · April 18 – April 28, 2026

| Team Member | Role |
|---|---|
| Ali Agabalazade | Lead ML / Data Engineer |
| Nigar Rustamova | Data Analyst / Geospatial |
| Nazrin Mammadzadeh | Project Manager / Documentation |
| Isgandar Panahov | Presentation / Documentation |

---

## DAY 1 · April 18, 2026 (Saturday)
### Project Kickoff, Problem Scoping & Data Discovery

| Sprint Goal | Align on the problem domain, identify viable data sources, define the ground-truth labeling strategy, and begin Open-Meteo API exploration |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova, Nazrin Mammadzadeh, Isgandar Panahov |

#### Executive Summary

Day 1 marked the official launch of the Baku Sentinel project. The entire team convened to align on a central question that differentiates this project from a standard rainfall forecast: Baku's flash flooding is not merely a weather event — it is a compound urban-hydrological failure driven by the city's outdated drainage infrastructure, high surface impermeability, and dramatic elevation gradients across its micro-zones. The most consequential decision of the day was to frame the problem as a deterministic binary classification task (flood / no-flood) rather than a regression-based precipitation forecast, which would have required external validation labels unavailable in structured form for Baku. Each team member independently explored the Open-Meteo API ecosystem to understand data availability and response structure, setting the foundation for the ingestion pipeline.

#### Detailed Activity Log

**▸ Labeling Strategy Design**

- The team deliberated on how to define a reproducible, quantitatively traceable ground-truth flood label without access to official government flood records, which do not exist in machine-readable format for Baku.
- Three candidate approaches were evaluated: (1) scraping local Telegram channels and news portals for flood mentions, (2) using EM-DAT global disaster database entries, and (3) deriving a proxy label from the Open-Meteo Flood API `river_discharge` field.
- The `river_discharge` approach was selected as the primary strategy for its reproducibility and objectivity. A discharge threshold of 1.0 m³/s was established as the empirical exceedance point at which Baku's drainage systems become overwhelmed.
- The compound label condition was locked: `is_flood = 1` if and only if `river_discharge > 1.0` AND (`precipitation > 1.0 mm` OR `relative_humidity > 85%`). This compound gate prevents falsely labeling humid dry spells as flood events.
- A critical temporal design decision was made: river discharge from day D−1 is used to label 6-hour slots on day D, preventing same-day lookahead leakage — a subtle but consequential point identified early in the design phase.

**▸ Dataset Discovery & Evaluation**

- A systematic review of candidate flood datasets was conducted: GloFAS (Global Flood Awareness System), Copernicus Emergency Management Service, EM-DAT, and several Kaggle-hosted flood CSV datasets.
- GloFAS was evaluated for river discharge coverage over Azerbaijan but found to have insufficient sub-daily resolution for Baku's micro-zone analysis.
- Copernicus EMS provides satellite-derived flood extent polygons but operates on an event-triggered basis, making it unsuitable for continuous historical training data.
- Open-Meteo was selected as the primary data source: free API access, hourly granularity, integrated flood discharge endpoint, clean JSON responses, and no authentication required.
- Final variable shortlist documented: `temperature_2m`, `precipitation`, `relative_humidity_2m`, `soil_moisture_0_to_7cm`, `soil_moisture_7_to_28cm`, `river_discharge`, `windspeed_10m`.

**▸ Baku Flood News Scraper (parallel track)**

- A supplementary news scraper was built using Telethon to access Telegram channels known for Baku city reporting, as a potential labeling validation layer.
- Oxu.az (a major Azerbaijani news portal) was scraped with keyword filtering on 'sel' (flood) and 'daşqın' (overflow/inundation), extracting timestamps and district-level location mentions.
- Scraped data was deduplicated and structured using a locally-run Gemma 4 (9B) language model for entity normalization — specifically to resolve inconsistent district naming conventions across articles.
- The scraper output was retained as a supplementary validation layer rather than the primary label source, due to inconsistent temporal coverage and location ambiguity inherent in news text.

**▸ Open-Meteo API Exploration**

- Each team member independently queried the Open-Meteo Archive, Forecast, and Flood APIs with Baku coordinates to understand response schemas, available fields, and practical rate limits.
- Lag feature time windows were provisionally debated and set at 24h and 72h lookback periods for the baseline feature set.
- API response structures documented: hourly weather returns flat JSON with arrays per variable; flood API returns daily discharge values; forecast API mirrors the weather structure with a 16-day horizon.
- The decision to use a 6-hourly resampling cadence was made: this balances temporal resolution (flash floods develop over hours) against data volume and model complexity.

#### Day Outcomes & Deliverables

- ✓ Flood labeling logic fully defined: binary `is_flood` with compound condition and D−1 discharge lag
- ✓ Open-Meteo confirmed as primary data source across all three APIs (archive, flood, forecast)
- ✓ Baseline variable list finalized: 7 raw meteorological and hydrological fields
- ✓ 6-hourly temporal grain selected as canonical analytical unit
- ✓ News scraper prototype completed as supplementary validation layer

**Blockers & Resolutions:** No critical blockers. The team aligned quickly on the labeling philosophy, which prevented the most common early-stage ambiguity in ML projects.

---

## DAY 2 · April 19, 2026 (Sunday)
### Zone Architecture, README Foundation & Feature Schema Lock

| Sprint Goal | Define Baku's geographic micro-zones, produce the project README foundation, and lock the final baseline feature schema for Silver layer ingestion |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova, Nazrin Mammadzadeh, Isgandar Panahov |

#### Executive Summary

Day 2 converted the conceptual decisions from Day 1 into structured project artifacts. The most technically significant work was the geospatial zone definition: since Baku's flood risk is highly non-uniform across its terrain, the team needed zones that would each receive independent feature engineering, model predictions, and risk alert outputs. The High / Moderate / Low Relief classification was derived from real elevation data and known municipal flood risk patterns. In parallel, Nazrin produced the project README foundation — a living reference document that would anchor all subsequent technical decisions and team communication throughout the sprint.

#### Detailed Activity Log

**▸ Geospatial Zone Architecture**

- The GADM Level 2 administrative boundary shapefile for Azerbaijan was loaded, filtering for the Absheron economic region and Baku city (`NAME_2 = 'Bakı'`) districts specifically.
- A 50×50 sampling grid was overlaid on the Baku boundary polygon to capture elevation variation across the full city extent rather than just administrative centroids.
- Three terrain-based micro-zones were defined:
  - **High Relief Zone:** elevation > 100m a.s.l., coordinates 40.4093°N / 49.8671°E. Acts as the upland cascade origin; historically lowest flood incidence (~0.6%) but drives gravitational runoff toward lower zones.
  - **Low Relief Zone:** elevation 0–30m a.s.l., coordinates 40.3777°N / 49.8920°E. Coastal core; highest inundation risk (~1.6%); receives concentrated gravitational runoff.
  - **Moderate Relief Zone:** elevation 30–100m a.s.l., coordinates 40.4200°N / 49.9500°E. Transition zone with complex bidirectional drainage; flood rate ~1.1%.
- Each zone was assigned a representative coordinate chosen for elevation class representativeness, not administrative boundary centroids.

**▸ Project README v0.1**

- The README was structured from scratch covering: Problem Statement, Why It Matters, Target Variable definition, Dataset properties, Zone descriptions, Feature Engineering schema, Pipeline Architecture, Model description, Risk Thresholds, Usage, and Key Definitions.
- The Problem Statement was written to capture the real-world stakes: flooding causes logistical paralysis, specifically documenting the Sabunçu tunnel and city underpasses as known danger points during flood events.
- The Target Variable section was formalized with explicit documentation of the compound label condition, temporal design (D−1 lag), granularity, and rationale — written to be immediately reproducible by an external reviewer.
- The Bronze → Silver → Gold medallion architecture was outlined with DuckDB as the storage layer, chosen for its zero-infrastructure SQL analytics capability in a local Python environment.
- Success criteria were defined: AUC-PR > 0.30, F2-score > 0.50 on the held-out test set, and all three zones producing calibrated probability outputs.

**▸ Feature Schema Finalization**

- The full feature schema was locked for Gold layer engineering: 37 features organized across 5 thematic groups.
- **Group 1 — Precipitation:** rolling sums at 6h, 12h, 24h, 48h, 72h; max within window; API-7D exponential decay index.
- **Group 2 — Soil Memory:** volumetric soil moisture at 0–7cm and 7–28cm depth; Soil Saturation Index (SSI) composite.
- **Group 3 — Thermal / Humidity:** `temperature_2m` mean and range; `relative_humidity_2m` mean.
- **Group 4 — Wind:** `windspeed_10m` mean and max.
- **Group 5 — Temporal:** sin/cos encodings of hour-of-day and day-of-year; zone integer encoding.
- The Antecedent Precipitation Index (API-7D) decay formula was agreed: exponential decay with factor 0.85 per day over a 7-day lookback window.

#### Day Outcomes & Deliverables

- ✓ Three Baku terrain micro-zones defined with coordinates, elevation ranges, and flood rate benchmarks
- ✓ Project README v0.1 written covering full scope from problem statement through methodology
- ✓ 37-feature Gold layer schema locked across 5 thematic groups
- ✓ API-7D formula and all lag window configurations finalized
- ✓ DuckDB medallion architecture (Bronze / Silver / Gold) confirmed as storage strategy

**Blockers & Resolutions:** Shapefile loading required the GADM dataset to be available locally; the team used the publicly available `gadm41_AZE_shp` package. Minor debate over zone coordinate selection was resolved by consensus on the representative-point approach.

---

## DAY 3 · April 20, 2026 (Monday)
### Repository Initialization, Full Ingestion Pipeline & First Baseline Model

| Sprint Goal | Initialize the GitHub repository with production-grade structure, execute and validate the full data ingestion pipeline, and train the first baseline classification model |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova, Nazrin Mammadzadeh, Isgandar Panahov |

#### Executive Summary

Day 3 was the first day of active engineering. The team transitioned from planning artifacts to a functioning codebase. Ali initialized the GitHub repository with the full modular `src/` package structure. The ingestion pipeline was executed and fully validated: 55,248 rows of hourly weather data per zone (2020–2026) and 2,302 rows of daily flood discharge per zone were confirmed with zero nulls and zero temporal gaps across all six datasets. The Silver and Gold ETL layers were brought up in DuckDB, and the first baseline Random Forest model was trained — establishing the performance floor against which all subsequent optimization work would be measured.

#### Detailed Activity Log

**▸ Repository Initialization**

- GitHub repository `Weather-Prediction` was initialized with the full production folder structure: `notebooks/`, `src/`, `data/`, `reports/`, `models/`, `logs/`.
- The `src/` package was structured with explicit module separation: `config.py` (zone definitions, constants, API endpoints, risk thresholds), `ingestion.py` (Open-Meteo fetch layer with retry logic), `pipeline.py` (Silver/Gold SQL ETL), `model.py` (training + evaluation), `predict.py` (30-day forecast runner), `main.py` (CLI orchestrator).
- `.gitignore` configured to exclude `data/raw/` (ephemeral Bronze CSVs), the DuckDB binary, trained model artifacts, Python cache, and GADM shapefiles.
- `requirements.txt` finalized with all project dependencies: `openmeteo-requests`, `pandas`, `numpy`, `duckdb`, `scikit-learn`, `xgboost`, `imbalanced-learn`, `optuna`, `shap`, `geopandas`, `matplotlib`, `seaborn`, `joblib`.
- Initial commit was pushed and a PR was opened for Day 1 deliverables review.

**▸ Ingestion Pipeline Execution & Validation**

- `ingestion.py` was executed for the full `2020-01-01` to `2026-04-20` historical window across all three zones.
- Historical weather: 55,248 rows × 3 zones — hourly temperature, precipitation, humidity, soil moisture, windspeed. Zero gaps, zero nulls confirmed.
- Historical flood: 2,302 rows × 3 zones — daily `river_discharge` values. Zero gaps, zero nulls confirmed.
- 15-day forecast fetch also executed: 360 hourly records per zone saved to CSV for downstream pipeline testing.
- An inline data audit function was written to verify temporal continuity, null counts, and expected row counts — the audit table confirmed clean data across all 6 datasets before any Silver processing began.

**▸ Silver / Gold ETL & Baseline Model**

- Silver ETL executed in DuckDB using `time_bucket(INTERVAL '6 hours', time)` to resample hourly data into 6-hourly aggregates, joined with the daily flood discharge table, and the `is_flood` binary label was computed using the D−1 temporal shift.
- All 37 Gold layer features were engineered: precipitation rolling windows, API-7D index, SSI composite, thermal features, windspeed aggregates, and temporal cyclical encodings.
- Class distribution analysis confirmed extreme imbalance: ~1% flood rate, 1:93 positive-to-negative ratio — validating the need for imbalanced learning techniques in subsequent model work.
- A Random Forest baseline classifier was trained on a stratified 80/20 split of the Gold layer data. Performance metrics were shared across the team to establish the AUC-ROC and F2-score baseline floor.
- Correlation heatmap computed: `humidity_precip_product`, `soil_temperature_0_to_7cm`, and `precip_roll_max_24h` identified as high-correlation (>0.90) twin features flagged for future removal.

#### Day Outcomes & Deliverables

- ✓ GitHub repository fully initialized with modular `src/` package and initial commit
- ✓ Full ingestion pipeline validated: 55,248 rows weather + 2,302 rows flood per zone, zero nulls, zero gaps
- ✓ Silver and Gold ETL layers operating in DuckDB
- ✓ Baseline Random Forest model trained; performance floor established for all future comparisons
- ✓ Class imbalance confirmed at ~1% (1:93 ratio); imbalanced learning locked as a required pipeline component

**Blockers & Resolutions:** DuckDB's `time_bucket` function required a specific `INTERVAL` syntax for 6-hourly resampling; resolved by referencing the DuckDB documentation. The GADM shapefile was too large for version control and added to `.gitignore` with a documentation note for new contributors.

---

## DAY 4 · April 21, 2026 (Tuesday)
### Production Pipeline, XGBoost Integration & 30-Day Forecast System

| Sprint Goal | Build the end-to-end Baku Sentinel production pipeline, replace the baseline model with XGBoost, and deliver the first 30-day probabilistic flood forecast |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova, Nazrin Mammadzadeh, Isgandar Panahov |

#### Executive Summary

Day 4 was the most technically dense day of the sprint. Three major parallel workstreams converged: XGBoost was integrated into the data pipeline with production-grade error handling and quality checks; the full 30-day forecast system was designed and built using a `WeatherClimatologyModel` to extend beyond Open-Meteo's 15-day live horizon; and the team produced the Mermaid pipeline architecture diagram for the README. The day culminated in the first complete end-to-end run of the Baku Sentinel system — from raw API fetch through Bronze, Silver, and Gold layers to a live 30-day per-zone probabilistic risk output.

#### Detailed Activity Log

**▸ XGBoost Integration & Pipeline Hardening**

- The Random Forest baseline was replaced with XGBoost (`XGBClassifier`) in `model.py`. The key architectural decision was to use `scale_pos_weight` to address the 1:93 class imbalance natively at the objective level.
- A chronological 80/20 train/test split replaced the earlier stratified random split — essential for time-series classification to prevent future data contaminating the training set.
- `TimeSeriesSplit` cross-validation (`n_splits=5`) was added for robust model evaluation, ensuring all folds respect temporal ordering.
- F1-score threshold tuning was implemented: the classification threshold is optimized on the training set's precision-recall curve rather than defaulting to the standard 0.5.
- Isotonic calibration (`CalibratedClassifierCV`, `method='isotonic'`) was applied post-training to convert raw XGBoost scores into well-calibrated probabilities — necessary for the alert tier thresholds to carry meaningful probabilistic interpretation.
- Production error handling added: null checks on incoming Silver data, Gold layer schema validation, and `try/except` wrappers on all DuckDB write operations.

**▸ 30-Day Forecast Pipeline**

- Core challenge: Open-Meteo's live operational forecast extends only 15 days. A principled strategy was needed to generate days 16–30 without simply extrapolating the last known forecast values.
- `WeatherClimatologyModel` designed and implemented in `weather_model.py`: trains on the full Silver historical dataset grouped by `zone × day-of-year × hour-of-day`, producing climatological mean values for every variable at every hour of the year.
- For days 16–30, the climatological model generates synthetic weather inputs representing expected historical-average conditions for those future dates — a defensible extension strategy that makes the uncertainty explicit.
- `predict.py` written to orchestrate the full inference flow: fetch 15-day live weather → append 15-day climatological extension → run Gold feature engineering on combined input → apply trained XGBoost + calibration → generate per-zone alert tiers.
- Three alert tiers defined: **LOW** (P(flood) < 0.30), **MEDIUM** (0.30 ≤ P < 0.60), **HIGH** (P(flood) ≥ 0.60). Full 30-day forecast saved to `reports/forecast_30day.csv`.

**▸ Pipeline Architecture & CLI Orchestrator**

- A Mermaid flowchart diagram was created documenting the full Bronze → Silver → Gold medallion architecture with all data flow connections annotated and added to the README.
- `main.py` CLI orchestrator finalized with 5 execution modes: `--mode ingest`, `--mode etl`, `--mode train`, `--mode forecast`, `--mode full`.
- Structured logging integrated across all pipeline stages, writing timestamped entries to `logs/baku_sentinel.log`.

**▸ Leakage Audit (Identified on Day 4)**

- During XGBoost integration, a subtle leakage risk was identified: `river_discharge` is both the source of the `is_flood` label AND a potential raw input feature candidate.
- Fix implemented in `pipeline.py`: `river_discharge` is consumed only at the base CTE where the `is_flood` label is computed. It is explicitly excluded from all lag, rolling, and saturation feature computations flowing into the model.
- A formal drop list of redundant twin features (>0.90 pairwise correlation) was added to `model.py`: `humidity_precip_product`, `soil_temperature_0_to_7cm`, `precip_roll_max_24h`.

#### Day Outcomes & Deliverables

- ✓ XGBoost model with chronological split, TimeSeriesSplit CV, `scale_pos_weight`, isotonic calibration, and F1-threshold tuning fully operational
- ✓ Full 30-day forecast system live: 15-day Open-Meteo + 15-day climatological extension
- ✓ Leakage fix implemented: `river_discharge` isolated to label CTE only
- ✓ `main.py` CLI orchestrator complete with 5 modes
- ✓ Mermaid architecture diagram added to README
- ✓ First full end-to-end Baku Sentinel pipeline run completed successfully

**Blockers & Resolutions:** `WeatherClimatologyModel`'s day-of-year grouping required leap year handling (day 366 fallback to day 365 values). Isotonic calibration requires sufficient positive samples per CV fold — fold class distributions were validated before running to confirm viability.

---

## DAY 5 · April 22, 2026 (Wednesday)
### README Regularization & First Teacher Feedback Response

| Sprint Goal | Address all first-round teacher feedback on the README: remove stray content, add the Features Summary Table, expand Key Definitions, and restructure Daily Activities |
|---|---|
| Active Members | Ali Agabalazade, Nazrin Mammadzadeh |

#### Executive Summary

Day 5 was a documentation consolidation day, focused entirely on responding to the first round of teacher feedback. The two items flagged were: a stray Azerbaijani-language sentence left in the README from an earlier drafting session, and the absence of a structured Features Summary Table. The README pass converted the feature documentation from loose prose into a formal source → name → unit → aggregation format, and the Key Definitions glossary was expanded with all terms introduced during the pipeline architecture work.

#### Detailed Activity Log

**▸ README Regularization**

- A stray Azerbaijani-language sentence was identified and removed from the Problem Statement section — a residue from an early collaborative drafting session.
- A structured Features Summary Table was added in the format: Source API → Variable Name → Unit → Aggregation Method, covering all 37 Gold layer features across the 5 thematic groups.
- The Key Definitions glossary was reviewed and expanded with new entries: `WeatherClimatologyModel`, Exceedance Probability, F2-score, Terrain Cascade Risk, Silver Grain, Bronze Layer, and Gold Layer.
- The Daily Activities section was restructured from a flat prose list into a dated table format for easier reviewer navigation.
- All inline acronyms (API-7D, SSI, AUC-PR, etc.) were cross-referenced against the glossary for consistency.

**▸ Day 1–3 Deliverables Formal Commit**

- All Day 1–3 notebooks were reviewed, cleaned of debug output, and formally committed.
- `requirements.txt` was re-verified for completeness and correct version pinning.
- PR for the Day 1 deliverables review was merged following team sign-off.

#### Day Outcomes & Deliverables

- ✓ Azerbaijani residue removed from README
- ✓ 37-feature summary table added in structured format
- ✓ Key Definitions expanded with 7 new entries
- ✓ Daily Activities restructured into dated table
- ✓ Day 1–3 deliverables formally committed and PR merged

**Blockers & Resolutions:** No blockers. Purely a documentation day with no external dependencies.

---

## DAY 6 · April 23, 2026 (Thursday)
### Sampling Strategy Benchmarking & Optuna Hyperparameter Optimization

| Sprint Goal | Systematically compare 7 class imbalance strategies and run a 60-trial Optuna TPE search to find the optimal XGBoost configuration by F2-score |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova |

#### Executive Summary

Day 6 was the primary model quality improvement day. Rather than defaulting to SMOTE as a conventional imbalanced learning approach, the team ran a controlled comparison of 7 distinct resampling strategies under identical TimeSeriesSplit cross-validation conditions. This systematic benchmarking revealed that Random Over-Sampling (ROS) achieves the best F2-score stability for this specific dataset structure — a result that would not have been apparent without the controlled comparison. Following strategy selection, a 60-trial Optuna TPE search was executed to find the optimal XGBoost hyperparameter configuration, with the best-performing model saved as a production artifact.

#### Detailed Activity Log

**▸ Sampling Strategy Comparison**

Seven class imbalance handling strategies were benchmarked against a no-resampling baseline using `TimeSeriesSplit(n_splits=5)` CV and F2-score as the selection metric:

1. Baseline (no resampling) — performance floor
2. Random Over-Sampling (ROS) — minority class duplication
3. SMOTE — synthetic minority interpolation via k-nearest neighbors
4. ADASYN — adaptive density-based synthetic sampling
5. Random Under-Sampling (RUS) — majority class reduction
6. TomekLinks — borderline majority sample removal
7. Edited Nearest Neighbours (ENN) — noise-filtered under-sampling
8. SMOTE + ENN combined pipeline

F2-score (β=2) was chosen as the evaluation metric because missing a true flood event carries far greater real-world cost than a false alarm — this metric weights recall 4× over precision.

**Result:** Random Over-Sampling (ROS) achieved the highest mean F2-score across all CV folds with the lowest variance, and was selected as the resampling strategy for the Optuna optimization stage.

**▸ Optuna Hyperparameter Optimization**

- A 60-trial Tree-structured Parzen Estimator (TPE) search was run using Optuna, with `TimeSeriesSplit(n_splits=5)` inner cross-validation for each trial.
- Search space: `n_estimators` (100–1000), `max_depth` (3–12), `learning_rate` (0.01–0.3 log-scale), `subsample` (0.6–1.0), `colsample_bytree` (0.5–1.0), `min_child_weight` (1–10), `gamma` (0–5).
- Each trial trains a ROS-augmented XGBoost model and reports the mean CV F2-score as the Optuna objective value.
- The optimized model artifact was saved as `models/day05_ros_optuna.joblib` with an accompanying metrics JSON recording all 60 trial results and the winning hyperparameter configuration.
- The optimization confirmed a significant improvement over the baseline Random Forest on this imbalanced time-series task, with notably improved recall on the minority flood class.

#### Day Outcomes & Deliverables

- ✓ 7-strategy sampling benchmark completed; ROS selected as optimal by F2-score
- ✓ 60-trial Optuna TPE search completed
- ✓ Optimized artifact saved: `models/day05_ros_optuna.joblib` + metrics JSON
- ✓ F2-score confirmed as the primary threshold-tuning objective for all downstream evaluation

**Blockers & Resolutions:** ADASYN failed on some CV folds with very few positive samples due to neighborhood size constraints; a `try/except` fallback to ROS was added. The Optuna study was seeded for reproducibility.

---

## DAY 7 · April 24, 2026 (Friday)
### Leakage Risk Audit & Temporal Cross-Validation Review

| Sprint Goal | Conduct a thorough leakage audit on all feature engineering paths, verify temporal CV correctness, and document findings in the README |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova |

#### Executive Summary

Day 7 was dedicated to a structured audit of the pipeline's statistical integrity — specifically the two most common failure modes in time-series classification projects: data leakage and temporal cross-validation violations. The leakage audit identified an indirect pathway between precipitation rolling features and the `river_discharge`-derived label that had been overlooked in initial pipeline construction. Temporal CV was verified as correctly applied. The audit findings were fully documented in the README to ensure transparency for reviewers.

#### Detailed Activity Log

**▸ Leakage Risk Audit**

- A systematic review was conducted of every feature in the Gold layer to identify any indirect pathway through which label information could contaminate model inputs.
- The primary leakage risk identified: precipitation rolling features computed over windows that include the current 6-hour slot could correlate with `river_discharge` values used to derive the `is_flood` label for that same slot.
- The fix: in `pipeline.py`, `river_discharge` is consumed only at the base CTE where the `is_flood` label is computed. All subsequent feature engineering CTEs receive a version of the dataset from which `river_discharge` has been dropped, preventing any direct or indirect leakage propagation.
- The redundant twin feature drop list in `model.py` was reviewed and confirmed complete: `humidity_precip_product`, `soil_temperature_0_to_7cm`, `precip_roll_max_24h`, and several others with >0.90 pairwise correlation to a remaining feature.
- Leakage audit findings and the specific fix implementation were documented in the README under a dedicated Pipeline Integrity section.

**▸ Temporal Cross-Validation Review**

- All CV configurations were reviewed to confirm temporal ordering is respected: `TimeSeriesSplit(n_splits=5)` verified as correctly applied — each fold's test set is strictly after its training set in time.
- The chronological 80/20 train/test split was re-verified: the split point falls at approximately early 2025, with all 2025+ data reserved for out-of-sample evaluation.
- An out-of-sample 2025 evaluation window was formally recommended as a separate held-out test to assess model generalization beyond the TimeSeriesSplit CV results.
- The Optuna inner CV loop was reviewed to confirm it also uses `TimeSeriesSplit` rather than standard `KFold` — verified as correctly configured.

#### Day Outcomes & Deliverables

- ✓ Leakage audit completed; indirect `river_discharge` pathway confirmed fixed in `pipeline.py`
- ✓ `TimeSeriesSplit` and chronological split both verified as correctly implemented
- ✓ 2025 out-of-sample evaluation window formally defined
- ✓ Audit findings documented in README

**Blockers & Resolutions:** The leakage fix required restructuring one SQL CTE in `pipeline.py` — tested thoroughly before merging to confirm Gold layer row counts and feature distributions were unaffected.

---

## DAY 8 · April 25, 2026 (Saturday)
### SHAP Feature Importance Analysis & Out-of-Sample Evaluation

| Sprint Goal | Compute SHAP-based global feature importance on the held-out validation window and evaluate the model on the 2025 out-of-sample period to confirm or rule out residual leakage |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova |

#### Executive Summary

Day 8 produced the two most important model transparency artifacts of the project: the SHAP global importance ranking and the out-of-sample 2025 evaluation results. The SHAP analysis, run with `TreeExplainer` for computational efficiency, revealed which of the 37 Gold layer features are genuinely predictive of flood events versus which are spurious correlates. The 2025 evaluation provided an independent confirmation that the model generalizes beyond its training window — the critical test for a real-world operational forecasting system.

#### Detailed Activity Log

**▸ SHAP Feature Importance Analysis**

- SHAP `TreeExplainer` was applied to the trained XGBoost model on the held-out validation window to compute global feature importance.
- `TreeExplainer` was chosen over `KernelExplainer` for computational efficiency given the XGBoost tree structure — it produces exact SHAP values rather than approximations.
- Top-10 predictive features were identified and ranked by mean absolute SHAP value: precipitation rolling windows (24h, 48h) and soil moisture indices dominated the top positions, confirming that antecedent soil saturation is the strongest flood precursor in the Baku dataset.
- Features with near-zero SHAP importance across all samples were identified as candidates for pruning in a future model iteration.
- SHAP summary plot (beeswarm) was generated and saved to `reports/figures/`, providing both feature importance ranking and the direction of each feature's effect on flood probability.
- Top-10 features and their SHAP values were documented in the model metrics JSON and the README.

**▸ Out-of-Sample 2025 Evaluation**

- The trained model was applied to the 2025 held-out data (data unseen during any training or CV fold) to assess generalization.
- Evaluation metrics computed on the 2025 window: AUC-ROC, AUC-PR, F1, F2, precision, recall at the optimized threshold.
- The 2025 results were compared against the `TimeSeriesSplit` CV means to detect any degradation that might indicate residual leakage or temporal distribution shift.
- Results confirmed that model performance on 2025 data is consistent with CV estimates — providing confidence that the leakage fixes are effective and the model generalizes to unseen recent data.
- The ingestion and audit run confirmed that the Day 8 dataset (executed April 25) contained 55,248 rows per weather zone and 2,302 rows per flood zone — all with zero gaps and zero nulls — matching the original Day 3 ingestion benchmark.

#### Day Outcomes & Deliverables

- ✓ SHAP `TreeExplainer` analysis completed; top-10 predictive features identified and documented
- ✓ SHAP summary plot saved to `reports/figures/`
- ✓ 2025 out-of-sample evaluation completed; model generalization confirmed
- ✓ Performance metrics from 2025 window consistent with `TimeSeriesSplit` CV estimates
- ✓ Top-10 SHAP features added to model metrics JSON and README

**Blockers & Resolutions:** SHAP `TreeExplainer` requires the model to be unwrapped from the `CalibratedClassifierCV` wrapper to access the underlying XGBoost base estimator — this was handled by accessing the `calibrated_classifiers_[0].base_estimator` attribute.

---

## DAY 9 · April 26, 2026 (Sunday)
### Demo UI Development

| Sprint Goal | Build the HTML/CSS/JS front-end interface for the Baku Sentinel demo, integrate per-zone alert visualization, and connect the 30-day forecast output |
|---|---|
| Active Members | Isgandar Panahov, Ali Agabalazade |

#### Executive Summary

Day 9 shifted focus from model development to user-facing output. The demo UI is the artifact that makes the project tangible for reviewers and non-technical stakeholders — it transforms the 30-day forecast CSV into a visual, interactive risk dashboard showing per-zone flood probability timelines and color-coded alert tiers.

#### Detailed Activity Log

**▸ UI Skeleton & Layout**

- An HTML/CSS/JS single-page interface was built without external framework dependencies, ensuring it can run locally from the repository without a build step.
- The layout features three zone panels (High Relief, Moderate Relief, Low Relief) arranged side by side, each displaying the 30-day forecast timeline and current alert status.
- Color-coded alert badges were implemented: **GREEN** for LOW risk (P < 0.30), **AMBER** for MEDIUM (0.30–0.60), **RED** for HIGH (≥ 0.60) — consistent with the alert tier definitions in `config.py`.
- A summary header panel shows the current highest risk zone and the nearest high-risk day in the 30-day window.
- Responsive CSS layout ensures readability at both desktop and projected presentation dimensions.

**▸ Forecast Data Integration**

- The 30-day forecast output (`reports/forecast_30day.csv`) was connected to the UI via a lightweight JavaScript CSV parser, eliminating any server-side requirement.
- The forecast timeline visualization was implemented as an SVG bar chart rendered inline, showing daily flood probability per zone across the 30-day horizon.
- The Days 1–15 (live forecast) and Days 16–30 (climatological extension) are visually distinguished in the chart with a dashed separator line and a legend annotation.
- The UI correctly reads the `zone`, `date`, `flood_probability`, and `alert_tier` columns from the forecast CSV and maps them to the visual components.

#### Day Outcomes & Deliverables

- ✓ Demo UI skeleton completed: three-zone dashboard with 30-day forecast timeline
- ✓ Alert tier color coding (GREEN / AMBER / RED) integrated
- ✓ Forecast CSV connected to UI via client-side JavaScript parser
- ✓ Live vs. climatological forecast visually distinguished in the timeline chart

**Blockers & Resolutions:** SVG chart rendering required careful coordinate mapping from probability values (0–1) to pixel coordinates given the variable panel width; resolved by computing scale factors dynamically from the container dimensions.

---

## DAY 10 · April 27, 2026 (Monday)
### Full Pipeline Integration Test & Edge Case Handling

| Sprint Goal | Execute a complete end-to-end pipeline run from ingest through forecast, identify and resolve edge cases in API response handling, and review all logs for anomalies |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova |

#### Executive Summary

Day 10 was the systems integration day — the first time all five pipeline stages (ingest, etl, train, forecast, full) were tested as a single orchestrated run rather than individual notebook executions. This revealed several edge cases in the API response handling and DuckDB write layer that had not been visible in isolated testing. Each edge case was diagnosed, fixed, and re-tested to confirm end-to-end stability before the final submission preparation day.

#### Detailed Activity Log

**▸ End-to-End Pipeline Run**

- `python main.py --mode full` was executed for the first time, triggering all five stages sequentially: historical ingest → Silver ETL → Gold ETL → XGBoost training → 30-day forecast generation.
- The full run completed successfully, producing the trained model artifact, calibration wrapper, metrics JSON, and `forecast_30day.csv` in a single execution.
- Total pipeline runtime was measured and documented in the README Usage section to set expectations for reviewers running the system.
- Logs were reviewed in detail: all `INFO` entries confirmed expected data flow; no `ERROR` or `WARNING` entries were present in the clean run.

**▸ Edge Case Handling**

- **Edge case 1:** Open-Meteo API occasionally returns a `429` (rate limit) response during bulk historical fetches. The existing retry logic in `ingestion.py` was tested and confirmed to handle this with exponential backoff.
- **Edge case 2:** On the first run after a fresh clone, the `data/raw/` directory does not exist. A missing `os.makedirs` guard was identified and added to the ingestion entry point.
- **Edge case 3:** If the forecast API returns fewer than 360 hours (can occur at day boundaries), the climatological extension model needed to pad the remaining hours. A fill-forward strategy was implemented.
- **Edge case 4:** The DuckDB connection was left open in an error path in `pipeline.py`, causing a file lock on retry. Fixed with a proper context manager (`with duckdb.connect(...) as conn`) wrapping all write operations.
- All four edge cases were regression-tested by simulating the failure condition and confirming the new handling path resolves correctly.

#### Day Outcomes & Deliverables

- ✓ Full end-to-end pipeline run completed successfully via `python main.py --mode full`
- ✓ Four edge cases identified and resolved: rate limit retry, directory creation, forecast padding, DuckDB connection leak
- ✓ All pipeline logs reviewed; no errors in clean run
- ✓ Pipeline runtime documented in README

**Blockers & Resolutions:** The DuckDB connection leak edge case required careful testing because it only manifested on a retry after a failed first run. Simulating the failure condition required temporarily injecting an exception into the write path.

---

## DAY 11 · April 28, 2026 (Tuesday)
### Final Review, Repository Cleanup & Submission Preparation

| Sprint Goal | Clean and tag the repository for submission, draft the presentation slide deck, complete a full demo rehearsal, and verify all artifacts are present and correct |
|---|---|
| Active Members | Ali Agabalazade, Nigar Rustamova, Nazrin Mammadzadeh, Isgandar Panahov |

#### Executive Summary

Day 11 was the final sprint day, focused entirely on packaging and presentation quality. The full team participated in a repository review to confirm that every deliverable specified in the README — notebooks, model artifacts, forecast output, demo UI, logs, and documentation — was committed, correctly named, and accessible to a reviewer cloning the repository for the first time. The slide deck was drafted and a full demo rehearsal was conducted, allowing the team to identify and fix presentation flow issues before the final submission.

#### Detailed Activity Log

**▸ Repository Cleanup & Tagging**

- A final review of the repository structure was conducted against the README's Repository Structure section to confirm every listed file and directory exists and is correctly named.
- All debug outputs, temporary print statements, and commented-out code blocks were removed from notebooks and source files.
- Model artifacts verified: `baku_sentinel_rf.joblib`, `baku_sentinel_rf_metrics.json`, `day05_ros_optuna.joblib`, `day05_ros_optuna_metrics.json` all present in `models/`.
- `reports/forecast_30day.csv` verified as a current run output (not a stale cached version).
- A Git tag (`v1.0-submission`) was created on the final commit for clean version identification.

**▸ Slide Deck Drafting**

- A presentation slide deck was drafted covering: project motivation (Baku flood problem), data and zone architecture, pipeline overview (Mermaid diagram adapted for slides), model results (SHAP importance, AUC-PR, F2-score), demo UI walkthrough, and key conclusions.
- SHAP top-10 feature importance chart was adapted for the slides from the `reports/figures/` output.
- The Why It Matters section was refined for a non-technical audience, emphasizing the Sabunçu tunnel risk and pedestrian mobility impact rather than technical metrics.

**▸ Demo Rehearsal**

- A complete timed demo rehearsal was conducted: live pipeline run (`python main.py --mode forecast`), demo UI display, and slide deck walkthrough.
- Two presentation flow issues were identified and resolved: the forecast chart's zone color legend was too small at projected scale (resized), and the slide deck's model results section lacked a plain-language interpretation of the F2-score metric (added).
- All team members reviewed their respective sections to confirm accurate and consistent technical claims across the slide deck and README.

#### Day Outcomes & Deliverables

- ✓ Repository cleaned, all artifacts verified present and correctly named
- ✓ Git tag `v1.0-submission` created on final commit
- ✓ Presentation slide deck completed
- ✓ Full demo rehearsal conducted; two presentation issues identified and resolved
- ✓ All team members signed off on submission readiness

**Blockers & Resolutions:** No blockers. The integration test on Day 10 meant that Day 11 contained no surprise pipeline issues — the team could focus entirely on presentation quality.

---

*Baku Sentinel · Team GALE · Daily Briefs · April 18–28, 2026*
