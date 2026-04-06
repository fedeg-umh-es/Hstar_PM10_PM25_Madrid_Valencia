#!/usr/bin/env python3
"""
figure_03_city_comparison.py
Figura 3 — Boxplot H*_strict Valencia vs Madrid por contaminante y modelo
Genera: figures/fig03_city_comparison.pdf
"""
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

RESULTS = {
    "Madrid":   Path("results"),
    "Valencia": Path("results_valencia"),
}
MODELS_PLOT  = ["sarima", "boosting"]
MODEL_LABELS = {"sarima": "SARIMA", "boosting": "XGBoost"}
POLLS        = ["PM10", "PM25"]
POLL_LABELS  = {"PM10": r"PM$_{10}$", "PM25": r"PM$_{2.5}$"}
COLORS       = {"Madrid": "#d6604d", "Valencia": "#2166ac"}

rows = []
for city, res_dir in RESULTS.items():
    for f in res_dir.glob("hstar_summary_*.csv"):
        df = pd.read_csv(f).rename(
            columns={"H_star_relax": "relax", "H_star_strict": "strict"}
        )
        if df.empty:
            continue
        name = f.stem.replace("hstar_summary_", "")
        poll = "PM10" if "PM10" in name else "PM25" if "PM25" in name else None
        if poll is None:
            continue
        for _, row in df[df["model"].isin(MODELS_PLOT)].iterrows():
            if pd.isna(row["strict"]):
                continue
            rows.append({
                "city":    city,
                "poll":    poll,
                "model":   row["model"],
                "strict":  int(row["strict"])
            })

df_all = pd.DataFrame(rows)

fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
fig.subplots_adjust(wspace=0.15)

for ax, poll in zip(axes, POLLS):
    sub = df_all[df_all["poll"] == poll]
    tick_pos  = []
    tick_lab  = []
    offset    = 0

    for mi, model in enumerate(MODELS_PLOT):
        for ci, city in enumerate(["Madrid", "Valencia"]):
            vals = sub[(sub["model"] == model) &
                       (sub["city"]  == city)]["strict"].values
            pos = offset + ci * 0.8
            bp = ax.boxplot(vals, positions=[pos], widths=0.6,
                            patch_artist=True,
                            medianprops=dict(color="black", linewidth=2),
                            boxprops=dict(facecolor=COLORS[city], alpha=0.7))
        tick_pos.append(offset + 0.4)
        tick_lab.append(MODEL_LABELS[model])
        offset += 2.5

    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_lab, fontsize=10)
    ax.set_yticks(range(0, 8))
    ax.set_ylim(-0.3, 7.5)
    ax.set_title(POLL_LABELS[poll], fontsize=11)
    ax.axhline(0, color="grey", linewidth=0.7, linestyle="--")
    if poll == "PM10":
        ax.set_ylabel(r"$H^*_{\mathrm{strict}}$ (days)", fontsize=10)

# Leyenda ciudades
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=COLORS[c], alpha=0.7, label=c)
                   for c in ["Madrid", "Valencia"]]
fig.legend(handles=legend_elements, loc="lower center", ncol=2,
           fontsize=10, bbox_to_anchor=(0.5, -0.04))

fig.suptitle(
    r"Distribution of $H^*_{\mathrm{strict}}$ by city, pollutant and model",
    fontsize=11, y=1.02)

Path("figures").mkdir(exist_ok=True)
plt.savefig("figures/fig03_city_comparison.pdf", bbox_inches="tight", dpi=300)
plt.savefig("figures/fig03_city_comparison.png", bbox_inches="tight", dpi=300)
print("OK → figures/fig03_city_comparison.pdf")
