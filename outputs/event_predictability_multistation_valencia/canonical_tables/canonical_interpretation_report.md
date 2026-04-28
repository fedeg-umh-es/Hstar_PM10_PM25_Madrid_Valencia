# Canonical interpretation report

Inputs are the existing sensitivity-support outputs. No models were retrained and no thresholds were recalculated here.

## 1. Which variant is empirically most stable?

By support alone, `B_p85_all_seasons` and `C_p90_grouped_cold_warm` are stable in all cells. `B_p85_all_seasons` has the broadest stable seasonal coverage because all four seasons and all horizons have at least 30 positive events. `C_p90_grouped_cold_warm` is also stable, but at the cost of replacing seasons with two broader regimes.

```text
                variant  n_cells  n_stable  min_positive  mean_bss_clim  max_bss_clim
   A_p90_exclude_summer       12         9            29      -1.478276     -0.108253
      B_p85_all_seasons       16        16            30      -0.904224      0.114120
C_p90_grouped_cold_warm        8         8            41      -1.688615     -0.460825
```

## 2. Does p85 solve support?

Yes, under the current support rule. Every `B_p85_all_seasons` season-horizon cell has at least 30 positives, including summer.

## 3. Does p90 remain viable only under cold/warm grouping?

For stable support across all retained cells, p90 is more viable under cold/warm grouping than under four target seasons. The p90 excluding-summer variant still has autumn h7, h14, and h21 below 30 positives, while cold/warm grouping is stable in every horizon.

## 4. Where does the model beat seasonal/regime climatology?

Only these cells exceed `BSS > 0.05` versus seasonal/regime climatology:

```text
          variant season_or_regime  horizon  n_positive_total  bss_vs_seasonal_or_regime_climatology_weighted
B_p85_all_seasons           winter        7               128                                         0.11412
```

Cells close to zero are:

```text
          variant season_or_regime  horizon  n_positive_total  bss_vs_seasonal_or_regime_climatology_weighted
B_p85_all_seasons           winter       14               119                                        0.012302
B_p85_all_seasons           winter       21               112                                       -0.038294
B_p85_all_seasons           winter       28               110                                       -0.048205
```

## 5. At what horizon does winter p85 skill disappear?

Winter p85 is positive at h7 and barely positive at h14, then becomes marginally negative at h21 and h28. Under the categorical rule, skill disappears after h14.

```text
 horizon  n_positive_total  bss_vs_seasonal_or_regime_climatology_weighted
       7               128                                        0.114120
      14               119                                        0.012302
      21               112                                       -0.038294
      28               110                                       -0.048205
```

## 6. Is persistence too weak as a decisive baseline?

Yes. Several cells show better performance versus persistence than versus seasonal/regime climatology. For this event task, persistence is useful as a reference but too weak to be decisive; the climatology baseline is the stricter comparator.

## 7. Safest current interpretation

The cautious interpretation is that support can be stabilized by p85 or by cold/warm grouping, but the minimal logistic model generally does not add robust incremental skill over seasonal/regime climatology. The only clear positive signal is winter under p85 at short horizons, especially h7, with h14 only weakly positive and h21-h28 marginally negative. No horizon-dependent predictability claim should be made from persistence-relative skill alone.

Canonical tables created:
- `table1_event_support_canonical.csv`
- `table2_bss_vs_climatology_canonical.csv`
- `table3_baseline_comparison_canonical.csv`
- `table4_fold_robustness.csv`