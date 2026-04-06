#!/usr/bin/env python3
"""
Convierte rvvcca.csv (formato wide) a formato long
con ciudad correcta por estacion.
"""
import argparse
from pathlib import Path

import pandas as pd

PM_COLS = ["PM2.5", "PM10"]

# Mapeo manual estacion -> ciudad
# Nota: en este CSV todas las estaciones conocidas son de Valencia.
CITY_MAP = {
    "Viveros": "Valencia",
    "Politecnico": "Valencia",
    "Valencia Centro": "Valencia",
    "Valencia Olivereta": "Valencia",
    "Avda. Francia": "Valencia",
    "Moli del Sol": "Valencia",
    "Pista Silla": "Valencia",
    "Bulevard Sud": "Valencia",
    "Nazaret Meteo": "Valencia",
    "Conselleria Meteo": "Valencia",
    "Puerto Valencia": "Valencia",
    "Puerto Moll Trans. Ponent": "Valencia",
    "Puerto llit antic Turia": "Valencia",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convierte rvvcca.csv (wide) a formato long por estación."
    )
    parser.add_argument("--input", required=True, help="CSV de entrada (formato wide).")
    parser.add_argument("--output", required=True, help="CSV de salida (formato long).")
    args = parser.parse_args()

    df = pd.read_csv(args.input, sep=";", encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]

    for c in PM_COLS:
        if c not in df.columns:
            raise ValueError(f"No existe la columna requerida: {c}")

    df["station_id"] = df["Estacion"].astype(str).str.strip()
    df["city"] = df["station_id"].map(CITY_MAP)
    df["datetime"] = pd.to_datetime(df["Fecha"], errors="coerce")

    sin_ciudad = sorted(df.loc[df["city"].isna(), "station_id"].dropna().unique().tolist())
    if sin_ciudad:
        print(f"AVISO - estaciones sin ciudad asignada (se excluyen): {sin_ciudad}")

    df_long = (
        df.dropna(subset=["city"])
        .melt(
            id_vars=["city", "station_id", "datetime"],
            value_vars=PM_COLS,
            var_name="component",
            value_name="value",
        )
        .assign(value=lambda x: pd.to_numeric(x["value"], errors="coerce"))
        .dropna(subset=["datetime", "value"])
        .sort_values(["city", "station_id", "component", "datetime"])
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_long.to_csv(out_path, index=False)
    print(f"OK -> {out_path} ({len(df_long):,} filas)")


if __name__ == "__main__":
    main()
