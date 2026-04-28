# Baseline audit: event predictability multistation Valencia

Inputs:
- `outputs/event_predictability_multistation_valencia/event_skill_fold_station_level.csv`
- `code/event_predictability_multistation_valencia.py`

## Diagnosis

The conflict is mainly statistical plus an aggregation artifact, not evidence of a detected leakage bug. The logistic model has positive row-level BSS against persistence, but row-level BSS against seasonal climatology can become extremely negative whenever the climatology Brier denominator is near zero for a single non-event case.

In `event_skill_fold_station_level.csv`, each metric row has `n_samples = 1`. The previously reported matrices average per-row BSS values. For BSS vs seasonal climatology this is unstable because `1 - model_brier / climatology_brier` explodes negatively when `climatology_brier` is tiny.

## Absolute Brier Score check

Seasonal climatology has low absolute Brier Score in several season-horizon cells and is especially low in summer, where events are rare. Lowest seasonal-climatology Brier cells:

```text
season  horizon           model_name  n_samples_total  n_positive_total  mean_brier_macro  mean_brier_weighted
summer        7 seasonal_climatology              418                11          0.026860             0.026860
summer       14 seasonal_climatology              418                11          0.026873             0.026873
summer       21 seasonal_climatology              418                11          0.026900             0.026900
summer       28 seasonal_climatology              418                11          0.026946             0.026946
spring        7 seasonal_climatology              462                33          0.065703             0.065703
spring       21 seasonal_climatology              462                34          0.068576             0.068576
spring       28 seasonal_climatology              462                34          0.069004             0.069004
spring       14 seasonal_climatology              462                33          0.069459             0.069459
```

Target-season support:

```text
season  horizon  total_samples  total_positive_events  folds_with_positive_events  support_ok
autumn        7            401                     33                          18        True
autumn       14            400                     32                          17        True
autumn       21            399                     32                          17        True
autumn       28            398                     33                          18        True
spring        7            462                     33                          18        True
spring       14            462                     33                          18        True
spring       21            462                     34                          18        True
spring       28            462                     34                          18        True
summer        7            418                     11                           8       False
summer       14            418                     11                           8       False
summer       21            418                     11                           8       False
summer       28            418                     11                           8       False
winter        7            420                    107                          33        True
winter       14            419                    100                          32        True
winter       21            418                    100                          32        True
winter       28            419                    101                          32        True
```

This points to rare events, strong seasonal concentration, small denominators in row-level BSS, and summer low support. It does not by itself indicate that the seasonal probability was applied to the wrong season.

## Sensitivity: BSS vs seasonal climatology

Macro row-level BSS, all included cells:

```text
 scenario  average_type       season         h7       h14        h21       h28
all_cells macro_row_bss ALL_INCLUDED -48.730964 -56.57724 -59.185987 -56.22958
```

Weighted/aggregate BSS, all included cells:

```text
 scenario           average_type       season        h7       h14       h21       h28
all_cells weighted_aggregate_bss ALL_INCLUDED -1.134867 -1.267892 -1.313805 -1.278394
```

Weighted/aggregate BSS excluding summer:

```text
      scenario           average_type       season        h7       h14       h21       h28
exclude_summer weighted_aggregate_bss ALL_INCLUDED -0.946291 -1.080851 -1.093643 -1.076522
```

Weighted/aggregate BSS excluding low-support cells:

```text
                 scenario           average_type       season        h7       h14       h21       h28
exclude_low_support_cells weighted_aggregate_bss ALL_INCLUDED -0.946291 -1.080851 -1.093643 -1.076522
```

Excluding summer reduces the most extreme denominator problem but does not remove negative aggregate BSS against seasonal climatology. Excluding low-support cells has the same practical effect here because only summer is below the positive-event threshold.

## Current average type

The current summary is macro over fold-station rows. Since exported fold-station rows have `n_samples = 1`, macro and sample-weighted Brier means are effectively the same after rows with missing Brier are excluded. However, weighted/aggregate BSS must be computed from aggregated Brier Scores, not by averaging row-level BSS ratios.

## Outliers

Rows with `bss_vs_seasonal_climatology < -10`: 4611. See `bss_outliers_vs_climatology.csv`.

## Implementation review

Confirmed from the script:
- Seasonal climatology is computed from training labels only: training origins satisfy `origin + horizon <= train_end`.
- Thresholds are station-specific and fold-specific.
- Climatology is station-specific because labels are built inside the station loop.
- Climatology is horizon-specific because labels are rebuilt inside the horizon loop.
- `target_season` climatology uses `origin_date + horizon`, and target-season metric rows use `seasonal_climatology_target`.
- No test target is used in the training-origin climatology set.

Relevant code excerpts:

```python
235:         thresholds: dict[str, float] = {}
236:         for station in stations:
237:             y_train = wide.loc[:train_end, station].dropna()
238:             thresholds[station] = float(y_train.quantile(0.90)) if len(y_train) else np.nan
239: 
240:         for horizon in HORIZONS:
241:             train_rows: list[dict] = []
242:             test_rows: list[dict] = []
243:             station_payload: list[dict] = []
244:             for station in stations:
245:                 series = wide[station]
246:                 threshold = thresholds[station]
247:                 if not np.isfinite(threshold):
248:                     continue
249: 
250:                 train_origin_dates = dates[
251:                     (dates >= dates[0] + pd.Timedelta(days=30))
252:                     & (dates + pd.Timedelta(days=horizon) <= train_end)
253:                 ]
254:                 target_dates = train_origin_dates + pd.Timedelta(days=horizon)
255:                 target_values = series.reindex(target_dates).to_numpy()
256:                 valid_target = pd.notna(target_values)
257:                 valid_train_origins = train_origin_dates[valid_target]
258:                 valid_train_targets = target_values[valid_target]
259:                 train_events = (valid_train_targets.astype(float) > threshold).astype(int)
260:                 labels_for_clim = list(zip(valid_train_origins, train_events))
```

```python
275:                 origin_season = season_name(origin_date)
276:                 target_season = season_name(target_date)
277:                 labels = pd.DataFrame(labels_for_clim, columns=["origin_date", "event"])
278:                 if labels.empty:
279:                     global_clim = np.nan
280:                     seasonal_origin_clim = np.nan
281:                     seasonal_target_clim = np.nan
282:                 else:
283:                     labels["origin_season"] = labels["origin_date"].map(season_name)
284:                     labels["target_season"] = (
285:                         labels["origin_date"] + pd.Timedelta(days=horizon)
286:                     ).map(season_name)
287:                     global_clim = float(labels["event"].mean())
288:                     seasonal_origin = labels.loc[labels["origin_season"] == origin_season, "event"]
289:                     seasonal_target = labels.loc[labels["target_season"] == target_season, "event"]
290:                     seasonal_origin_clim = (
```

```python
342:         ("origin_season", "origin_season", "seasonal_climatology_origin"),
343:         ("target_season", "target_season", "seasonal_climatology_target"),
344:     ]:
345:         for row in preds.itertuples(index=False):
346:             y = np.array([int(row.actual_event)])
347:             base_persistence = np.array([row.persistence_event], dtype=float)
348:             base_seasonal = np.array([getattr(row, seasonal_col)], dtype=float)
349:             base_global = np.array([row.global_climatology], dtype=float)
350:             season = getattr(row, season_col)
351:             support_ok = flag_lookup.get((season_type, season, int(row.horizon)), False)
352:             for model_name, col in model_cols.items():
353:                 if model_name == "seasonal_climatology":
354:                     p = base_seasonal
```

## Bug assessment

No implementation bug is apparent from the exported metrics and the code review. The issue is primarily statistical and metric-aggregation related: seasonal climatology is a strong probability baseline for rare seasonal events, and row-level BSS ratios are ill-conditioned when the baseline Brier Score is very close to zero.

## Recommendation

- Keep p90 for the main audit to preserve the stated event definition.
- Add a p85 sensitivity only as a support diagnostic, not as a replacement, if more stable seasonal cells are needed.
- Do not interpret summer separately under the current p90 event definition; either exclude summer from target-season interpretation or aggregate seasons for a stability check.
- Do not fix implementation unless future checks expose a mismatch; no concrete climatology leakage or season-mapping bug was found.
- Report aggregate Brier Scores and aggregate BSS alongside macro row-level BSS to avoid denominator-driven artifacts.

Verdict: statistical / aggregation issue, not a confirmed code bug.