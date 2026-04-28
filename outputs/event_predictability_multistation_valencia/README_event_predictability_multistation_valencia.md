# Event predictability audit: PM10 Valencia multistation

Dataset used: `data/modeling/pm10_daily_regular.parquet`.

Station inclusion criteria:
- `{"max_missing_pct": 50.0, "max_origins": 260, "min_station_days": 730, "min_train_days": 365, "min_valid_pm10": 365, "origin_stride_days": 7}`
- Included stations: Avda. Francia, Bulevard Sud, Moli del Sol, Pista Silla, Politecnico, Puerto Moll Trans. Ponent, Puerto Valencia, Valencia Centro, Viveros

Event definition:
- For every fold and station, `event_t = 1 if PM10_t > p90_train_station`.
- `p90_train_station` is computed inside the expanding training window and separately for each station.
- No global full-series p90 and no pooled-station threshold is used.

Horizon definition:
- Horizons are `h = 7, 14, 21, 28` days.
- For origin day `t`, the evaluated target is `event_(t+h)`.

Season diagnostics:
- `origin_season`: season of origin day `t`.
- `target_season`: season of target day `t+h`; preferred for event-regime interpretation.

Validation protocol:
- Expanding-window rolling-origin validation.
- Origin stride is 7 days.
- Fold-level and station-level predictions are preserved in the metric table.

Baselines:
- `persistence_event`: `p_hat(t+h) = event_t`, using the fold-specific station-specific threshold.
- Station-specific seasonal climatology estimated from training origins only.
- Station-specific global climatology estimated from training origins only.

Minimal model:
- `logistic_lag_roll_season_station` pooled across included stations.
- Features: PM10 lags 1-7, shifted rolling means 7 and 30 days, month, day-of-year sine/cosine, season, station encoding.
- Numeric imputation and scaling are fitted train-only inside each fold.

Leakage safeguards:
- No random split.
- No full-series threshold, scaling, imputation, or climatology.
- Training labels for climatology and logistic model use only origins whose target date is within the fold training window.
- Target dates are not used to construct origin-time features.

Support diagnostics:
- Season-horizon cells are unstable if total positive events < 30 or fewer than 3 folds contain positive events.
- ROC-AUC and PR-AUC are left undefined when class support is insufficient; fold-station rows also contain single samples, so AUC fields are not interpreted.

Design status: **Salvageable**.

Unstable cells:
- origin_season spring h7: 23 positives, 15 folds with positives.
- origin_season spring h14: 20 positives, 13 folds with positives.
- origin_season spring h21: 21 positives, 13 folds with positives.
- origin_season spring h28: 18 positives, 13 folds with positives.
- origin_season summer h7: 12 positives, 9 folds with positives.
- origin_season summer h14: 12 positives, 9 folds with positives.
- origin_season summer h21: 12 positives, 9 folds with positives.
- origin_season summer h28: 13 positives, 10 folds with positives.
- target_season summer h7: 11 positives, 8 folds with positives.
- target_season summer h14: 11 positives, 8 folds with positives.
- target_season summer h21: 11 positives, 8 folds with positives.
- target_season summer h28: 11 positives, 8 folds with positives.

Station coverage summary:

```text
               station_id start_date   end_date  n_days  n_valid_pm10  missing_pct  included_for_evaluation
            Avda. Francia 2009-11-12 2022-12-31    4798          3451    28.074198                     True
             Bulevard Sud 2011-05-04 2022-12-29    4258          2475    41.874119                     True
             Moli del Sol 2010-01-01 2022-12-31    4748          4348     8.424600                     True
              Pista Silla 2010-01-01 2022-12-31    4748          4592     3.285594                     True
              Politecnico 2008-04-08 2022-12-31    5381          5091     5.389333                     True
Puerto Moll Trans. Ponent 2021-01-01 2022-12-31     730           707     3.150685                     True
          Puerto Valencia 2017-01-01 2018-12-31     730           694     4.931507                     True
  Puerto llit antic Turia 2021-07-15 2022-12-31     535           529     1.121495                    False
          Valencia Centro 2018-10-16 2022-12-31    1538          1462     4.941482                     True
                  Viveros 2004-01-01 2022-12-29    6938          5108    26.376477                     True
```
