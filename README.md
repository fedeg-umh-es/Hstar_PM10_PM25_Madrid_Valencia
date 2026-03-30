# Hstar_PM10_PM25_Madrid_Valencia

Reproducible pipeline for estimating the operational predictability
limit **H\*** for daily PM10 and PM2.5 forecasting across urban
monitoring networks in **Madrid** and **Valencia** (Spain).

## Associated publication

> García Crespí, F. (2026). *Operational predictability limits for
> PM10 and PM2.5 forecasting in Valencia and Madrid: a rolling-origin
> skill assessment*. Submitted to Air Quality, Atmosphere & Health.

**Related preprint:**
García Crespí, F., Yubero Funes, E., Alfosea Simón, M. (2026).
*Rolling-Origin Validation Reverses Model Rankings in Multi-Step
PM10 Forecasting: XGBoost, SARIMA, and Persistence.*
arXiv:2603.20315. https://doi.org/10.48550/arXiv.2603.20315

---

## What this repository does

1. Converts raw RVVCCA (Valencia) and Ayuntamiento de Madrid CSV
   files to a unified long format filtered to PM10 and PM2.5.
2. Aggregates hourly records to daily mean concentrations with
   explicit hourly coverage thresholds.
3. Runs a strict **rolling-origin, expanding-window** evaluation
   protocol with **train-only preprocessing** for all models.
4. Computes horizon-by-horizon **Skill(h)** relative to simple
   persistence and extracts H\*\_relax and H\*\_strict.
5. Generates publication-quality figures and summary tables.

---

## Repository structure

```
code/
  convert_wide_to_long.py      # Valencia RVVCCA wide → long
  convert_madrid_to_long.py    # Madrid AQI wide → long
  query_eea_stations_v2.py     # Filter PM10/PM2.5, export by station
  build_daily_pm_series.py     # Hourly → daily aggregation
  run_rolling_skill.py         # Rolling-origin evaluation + H* extraction
  figure_01_skill_curves.py    # Fig 1: mean Skill(h) curves
  figure_02_hstar_heatmap.py   # Fig 2: H*_strict heatmap by station
  figure_03_city_comparison.py # Fig 3: Valencia vs Madrid boxplot

data_pm/                       # Hourly PM series by station (gitignored)
data_pm_daily/                 # Daily PM series by station (gitignored)
results/                       # Madrid rolling-origin metrics + H* summaries
results_valencia/              # Valencia rolling-origin metrics + H* summaries
figures/                       # Publication-ready figures (PDF + PNG)
references.bib                 # BibTeX references for the manuscript
```

---

## Execution sequence

```bash
# Step 0: convert raw CSVs to long format
python3 code/convert_wide_to_long.py        # Valencia
python3 code/convert_madrid_to_long.py      # Madrid

# Step 1: filter PM10/PM2.5 and export hourly series
python3 code/query_eea_stations_v2.py \
  --input /path/to/rvvcca_long.csv \
  --output-dir data_pm

# Step 2: aggregate to daily
python3 code/build_daily_pm_series.py \
  --input-dir data_pm \
  --output-dir data_pm_daily \
  --agg mean

# Step 3: rolling-origin evaluation
python3 code/run_rolling_skill.py \
  --batch \
  --input-dir data_pm_daily \
  --output-dir results

# Step 4: generate figures
python3 code/figure_01_skill_curves.py
python3 code/figure_02_hstar_heatmap.py
python3 code/figure_03_city_comparison.py
```

---

## Locked experimental protocol

- **Validation**: rolling-origin, expanding window, no random splits
- **Preprocessing**: train-only at each fold
- **Baseline**: simple persistence ŷ_{t+h} = y_t
- **Models**: simple persistence, seasonal persistence, SARIMA, XGBoost
- **Horizon**: h = 1, …, 7 days
- **Frequency**: daily

---

## License

Code: MIT. Data: subject to original source terms
(RVVCCA open data, Ayuntamiento de Madrid open data).
