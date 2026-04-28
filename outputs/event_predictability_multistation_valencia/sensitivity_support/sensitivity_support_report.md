# Sensitivity support audit

Dataset: `data/modeling/pm10_daily_regular.parquet`

Validation: expanding rolling-origin, stride 7 days, last 260 origins, station-specific train-window thresholds, no random split, no global threshold, train-only preprocessing in the logistic pipeline.

Included stations: Avda. Francia, Bulevard Sud, Moli del Sol, Pista Silla, Politecnico, Puerto Moll Trans. Ponent, Puerto Valencia, Valencia Centro, Viveros

## Support

Positive-event support by variant:

```text
              variant season_or_regime  h7  h14  h21  h28
 A_p90_exclude_summer           autumn  29   29   29   31
 A_p90_exclude_summer           spring  33   30   34   34
 A_p90_exclude_summer           winter 103   97   91   90
    B_p85_all_seasons           autumn  43   45   44   44
    B_p85_all_seasons           spring  47   46   48   51
    B_p85_all_seasons           summer  31   31   31   30
    B_p85_all_seasons           winter 128  119  112  110
C_p90_grouped_regimes             cold 132  126  120  121
C_p90_grouped_regimes             warm  43   41   45   44
```

Cells with fewer than 30 positives are unstable:

```text
             variant season_or_regime  horizon  n_samples_total  n_positive_total  positive_rate
A_p90_exclude_summer           autumn        7              363                29         0.0799
A_p90_exclude_summer           autumn       14              369                29         0.0786
A_p90_exclude_summer           autumn       21              358                29         0.0810
```

## Weighted BSS vs seasonal/regime climatology

```text
              variant season_or_regime      h7     h14     h21     h28
 A_p90_exclude_summer           autumn -1.6484 -1.8432 -1.7242 -1.6905
 A_p90_exclude_summer           spring -2.5082 -2.7080 -2.2761 -2.3613
 A_p90_exclude_summer           winter -0.1083 -0.2265 -0.3340 -0.3106
    B_p85_all_seasons           autumn -0.8549 -0.9339 -0.8940 -0.9767
    B_p85_all_seasons           spring -1.5291 -1.6207 -1.5024 -1.4145
    B_p85_all_seasons           summer -1.0779 -1.1414 -1.2536 -1.3083
    B_p85_all_seasons           winter  0.1141  0.0123 -0.0383 -0.0482
C_p90_grouped_regimes             cold -0.4608 -0.6087 -0.6790 -0.6786
C_p90_grouped_regimes             warm -2.7722 -2.9033 -2.6598 -2.7466
```

## Answers

- p85 solves the minimum support problem under the <30 positives rule for all target-season cells.
- Excluding summer does not fully stabilize p90 support.
- Cold/warm grouping is support-stable under p90.
- The logistic model beats seasonal/regime climatology in these weighted cells:

```text
          variant season_or_regime  horizon  n_positive_total  bss_vs_seasonal_or_regime_climatology_weighted
B_p85_all_seasons           winter        7               128                                          0.1141
B_p85_all_seasons           winter       14               119                                          0.0123
```
- Some cells are close to zero BSS vs climatology:

```text
          variant season_or_regime  horizon  n_positive_total  bss_vs_seasonal_or_regime_climatology_weighted
B_p85_all_seasons           winter       21               112                                         -0.0383
B_p85_all_seasons           winter       28               110                                         -0.0482
```

## Recommended next design

Stop short of horizon-dependent predictability claims for this event task because the model beats persistence but not seasonal/regime climatology. Persistence is too weak as the primary baseline for rare PM10 event predictability.

Recommended design: use p85 only as a support sensitivity, and use cold/warm regimes or p90 excluding summer only as stability diagnostics. For the current minimal logistic model, climatology dominates; do not present 4-season p90 summer as interpretable.

Decision among requested options: stop because climatology dominates.