#!/usr/bin/env python3
"""
Convierte el CSV horario del Ayuntamiento de Madrid
(formato wide H01-H24 / V01-V24) a formato long
compatible con query_eea_stations_v2.py

Magnitudes objetivo:
  9  = PM2.5
  10 = PM10
"""
import argparse
from pathlib import Path

import pandas as pd

PM_MAGNITUDES = {9: "PM2.5", 10: "PM10"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte CSV horario Madrid (formato wide H01-H24) a formato long."
    )
    parser.add_argument("--input", required=True, help="CSV de entrada (formato Madrid wide).")
    parser.add_argument("--output", required=True, help="CSV de salida (formato long).")
    parser.add_argument("--year-min", type=int, default=2010, help="Año mínimo a incluir.")
    args = parser.parse_args()

    df = pd.read_csv(args.input, sep=";", encoding="latin-1")
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]

    # Filtrar solo PM10 y PM2.5
    df = df[df["MAGNITUD"].isin(PM_MAGNITUDES)].copy()

    # Filtrar desde year_min
    df = df[df["ANO"] >= args.year_min].copy()

    # Pivotar horas H01-H24 a formato long
    rows = []
    for _, row in df.iterrows():
        component = PM_MAGNITUDES[row["MAGNITUD"]]
        try:
            station_id = str(int(row["ESTACION"])).zfill(3)
        except (ValueError, TypeError):
            continue
        for h in range(1, 25):
            val_col = f"H{h:02d}"
            flag_col = f"V{h:02d}"
            if row.get(flag_col, "N") != "V":
                continue  # solo valores validos
            try:
                value = float(row[val_col])
            except (ValueError, KeyError):
                continue
            # H01=01:00, ..., H23=23:00, H24=00:00 día siguiente
            # (convención fin-de-intervalo: H24 cierra el día en medianoche del día+1)
            dt = pd.Timestamp(
                year=int(row["ANO"]),
                month=int(row["MES"]),
                day=int(row["DIA"]),
            ) + pd.Timedelta(hours=h)
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
    if not df_long.empty:
        df_long = (
            df_long
            .sort_values(["station_id", "component", "datetime"])
            .drop_duplicates(subset=["station_id", "component", "datetime"], keep="last")
        )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_long.to_csv(out_path, index=False)
    print(f"OK -> {out_path}  ({len(df_long):,} filas)")
    print(
        df_long.groupby(["city", "station_id", "component"])
        .size()
        .reset_index(name="filas")
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
