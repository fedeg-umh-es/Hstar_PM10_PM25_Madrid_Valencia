#!/usr/bin/env python3
"""
figure_01_skill_curves.py
Figura 1 — Curvas Skill(h) por modelo, ciudad y contaminante
Genera: figures/fig01_skill_curves.pdf
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

# ── Configuración ────────────────────────────────────────────────
RESULTS = {
    "Madrid":   Path("results"),
    "Valencia": Path("results_valencia"),
}
MODELS   = ["sarima", "boosting", "persist_seasonal"]
LABELS   = {"sarima": "SARIMA", "boosting": "XGBoost",
            "persist_seasonal": "Seasonal persistence"}
COLORS   = {"sarima": "#2166ac", "boosting": "#d6604d",
            "persist_seasonal": "#4dac26"}
LINESTY  = {"sarima": "-", "boosting": "--", "persist_seasonal": ":"}
POLLS    = ["PM10", "PM25"]
POLL_LABELS = {"PM10": r"PM$_{10}$", "PM25": r"PM$_{2.5}$"}

fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharey=True, sharex=True)
fig.subplots_adjust(hspace=0.35, wspace=0.12)

for ci, (city, res_dir) in enumerate(RESULTS.items()):
    for pi, poll in enumerate(POLLS):
        ax = axes[pi, ci]
        ax.axhline(0, color="black", linewidth=0.8, linestyle="-")
        ax.set_title(f"{city} — {POLL_LABELS[poll]}", fontsize=10)

        files = list(res_dir.glob(f"rolling_origin_metrics_{poll}_{city}_*.csv"))
        if not files:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, color="grey")
            continue

        # Media de skill(h) por modelo sobre todas las estaciones
        all_data = []
        for f in files:
            df = pd.read_csv(f)
            df["file"] = f.stem
            all_data.append(df)
        df_all = pd.concat(all_data)

        for model in MODELS:
            sub = df_all[df_all["model"] == model]
            if sub.empty:
                continue
            mean_skill = sub.groupby("horizon")["skill_rmse_vs_persist"].mean()
            ax.plot(mean_skill.index, mean_skill.values,
                    label=LABELS[model],
                    color=COLORS[model],
                    linestyle=LINESTY[model],
                    linewidth=1.8, marker="o", markersize=4)

        ax.set_xlim(0.8, 7.2)
        ax.set_xticks(range(1, 8))
        ax.set_ylim(-0.5, 0.7)
        ax.axhspan(-0.5, 0, alpha=0.04, color="red")
        ax.axhspan(0, 0.7, alpha=0.04, color="green")

        if ci == 0:
            ax.set_ylabel("Skill$(h)$", fontsize=9)
        if pi == 1:
            ax.set_xlabel("Forecast horizon $h$ (days)", fontsize=9)

# Leyenda global
handles, labels = axes[0, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=3,
           fontsize=9, frameon=True,
           bbox_to_anchor=(0.5, -0.02))

fig.suptitle(
    r"Mean Skill$(h)$ relative to simple persistence "
    r"($\hat{y}_{t+h}=y_t$)",
    fontsize=11, y=1.01)

Path("figures").mkdir(exist_ok=True)
plt.savefig("figures/fig01_skill_curves.pdf", bbox_inches="tight", dpi=300)
plt.savefig("figures/fig01_skill_curves.png", bbox_inches="tight", dpi=300)
print("OK → figures/fig01_skill_curves.pdf")
