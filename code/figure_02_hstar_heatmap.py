#!/usr/bin/env python3
"""
figure_02_hstar_heatmap.py  — versión 2
Mejoras: etiquetas eje Y legibles, separación PM10/PM25, tamaño ajustado
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

RESULTS = {
    "Madrid":   (Path("results"),          "Madrid"),
    "Valencia": (Path("results_valencia"), "Valencia"),
}
MODELS_PLOT  = ["sarima", "boosting"]
MODEL_LABELS = {"sarima": "SARIMA", "boosting": "XGBoost"}
POLL_ORDER   = ["PM10", "PM25"]
POLL_LABELS  = {"PM10": r"PM$_{10}$", "PM25": r"PM$_{2.5}$"}

cmap = plt.cm.RdYlGn
norm = mcolors.BoundaryNorm(boundaries=range(0, 9), ncolors=256)

fig, axes = plt.subplots(1, 2, figsize=(14, 7))
fig.subplots_adjust(wspace=0.55)

for ax, (city_key, (res_dir, city_name)) in zip(axes, RESULTS.items()):

    rows = []
    for f in sorted(res_dir.glob("hstar_summary_*.csv")):
        df = pd.read_csv(f)
        if df.empty:
            continue
        stem = f.stem.replace("hstar_summary_", "")
        # Extraer poll y nombre de estación
        if stem.startswith("PM10_"):
            poll = "PM10"
            rest = stem[5:]
        elif stem.startswith("PM25_"):
            poll = "PM25"
            rest = stem[5:]
        else:
            continue
        city_prefix = city_name.replace(" ", "_") + "_"
        if not rest.startswith(city_prefix):
            continue
        station = rest[len(city_prefix):].replace("_", " ").strip()

        for _, row in df[df["model"].isin(MODELS_PLOT)].iterrows():
            rows.append({
                "poll":    poll,
                "station": station,
                "model":   row["model"],
                "strict":  int(row["H_star_strict"])
            })

    if not rows:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes)
        continue

    df_plot = pd.DataFrame(rows)

    # Construir etiquetas con separación visual PM10 / PM2.5
    df_plot["label"] = df_plot["poll"].map(POLL_LABELS) \
                       + " · " + df_plot["station"]

    # Ordenar: primero PM10, luego PM25
    df_plot["sort_key"] = df_plot["poll"].map({"PM10": 0, "PM25": 1})
    df_plot = df_plot.sort_values(["sort_key", "station"])

    pivot = df_plot.pivot_table(
        index="label", columns="model",
        values="strict", aggfunc="first"
    )[MODELS_PLOT]

    n_rows = len(pivot)
    im = ax.imshow(pivot.values, cmap=cmap, norm=norm,
                   aspect="auto")

    ax.set_xticks(range(len(MODELS_PLOT)))
    ax.set_xticklabels([MODEL_LABELS[m] for m in MODELS_PLOT],
                       fontsize=10, fontweight="bold")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_title(city_name, fontsize=12, fontweight="bold", pad=10)

    # Línea separadora PM10 / PM25
    n_pm10 = df_plot[df_plot["poll"] == "PM10"]["label"].nunique()
    if 0 < n_pm10 < n_rows:
        ax.axhline(n_pm10 - 0.5, color="black", linewidth=1.5, linestyle="--")

    # Valores numéricos en celdas
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                txt_color = "white" if int(val) <= 2 else "black"
                ax.text(j, i, str(int(val)),
                        ha="center", va="center",
                        fontsize=9, color=txt_color, fontweight="bold")

# Colorbar global
cbar = fig.colorbar(im, ax=axes, orientation="vertical",
                    label=r"$H^*_{\mathrm{strict}}$ (days)",
                    shrink=0.7, ticks=range(0, 8),
                    pad=0.02)
cbar.ax.tick_params(labelsize=9)

fig.suptitle(
    r"$H^*_{\mathrm{strict}}$: longest contiguous block of positive skill",
    fontsize=12, y=1.01)

Path("figures").mkdir(exist_ok=True)
plt.savefig("figures/fig02_hstar_heatmap.pdf", bbox_inches="tight", dpi=300)
plt.savefig("figures/fig02_hstar_heatmap.png", bbox_inches="tight", dpi=300)
print("OK → figures/fig02_hstar_heatmap.pdf")
