#!/usr/bin/env python3
"""
Convierte el CSV horario del Ayuntamiento de Madrid
(formato wide H01-H24 / V01-V24) a formato long
compatible con query_eea_stations_v2.py

Magnitudes objetivo:
  9  = PM2.5
  10 = PM10
"""
from pathlib import Path

import pandas as pd

INPUT = Path("/Users/federicogarciacrespi/Downloads/201200-1-calidad-aire-horario-csv.csv")
OUTPUT = Path("/Users/federicogarciacrespi/Downloads/madrid_long.csv")

PM_MAGNITUDES = {9: "PM2.5", 10: "PM10"}
YEAR_MIN = 2010

df = pd.read_csv(INPUT, sep=";", encoding="latin-1")
df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]

# Filtrar solo PM10 y PM2.5
df = df[df["MAGNITUD"].isin(PM_MAGNITUDES)].copy()

# Filtrar desde YEAR_MIN
df = df[df["ANO"] >= YEAR_MIN].copy()

# Pivotar horas H01-H24 a formato long
rows = []
for _, row in df.iterrows():
    component = PM_MAGNITUDES[row["MAGNITUD"]]
    station_id = str(int(row["ESTACION"])).zfill(3)
    for h in range(1, 25):
        val_col = f"H{h:02d}"
        flag_col = f"V{h:02d}"
        if row.get(flag_col, "N") != "V":
            continue  # solo valores validos
        try:
            value = float(row[val_col])
        except (ValueError, KeyError):
            continue
        dt = pd.Timestamp(
            year=int(row["ANO"]),
            month=int(row["MES"]),
            day=int(row["DIA"]),
            hour=h % 24,
        )
        rows.append(
            {
                "city": "Madrid",
                "station_id": station_id,
                "datetime": dt,
                "component": component,
                "value": value,
            }
        )

df_long = pd.DataFrame(rows)
df_long.to_csv(OUTPUT, index=False)
print(f"OK -> {OUTPUT}  ({len(df_long):,} filas)")
print(
    df_long.groupby(["city", "station_id", "component"])
    .size()
    .reset_index(name="filas")
    .to_string(index=False)
)
