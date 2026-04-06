#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

TARGET_COMPONENTS = {"PM10", "PM2.5"}


def detect_sep(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", errors="ignore") as f:
        line = f.readline()
    return ";" if line.count(";") > line.count(",") else ","


def normalize_component(x: str) -> str:
    x = str(x).strip().upper().replace(" ", "")
    if x == "PM25":
        return "PM2.5"
    return x


def normalize_city(x: str) -> str:
    return str(x).strip().replace(" ", "_")


def pick_column(df: pd.DataFrame, candidates: list[str], label: str) -> str:
    matches = [c for c in candidates if c in df.columns]
    if not matches:
        raise ValueError(f"No encuentro columna para {label}: {candidates}")
    if len(matches) > 1:
        print(f"AVISO - múltiples candidatos para {label}: {matches}; usando '{matches[0]}'")
    return matches[0]


def filter_pm_only(df: pd.DataFrame) -> pd.DataFrame:
    comp_col = pick_column(
        df,
        ["component", "pollutant", "variable", "species"],
        label="contaminante",
    )
    out = df.copy()
    out[comp_col] = out[comp_col].map(normalize_component)
    out = out[out[comp_col].isin(TARGET_COMPONENTS)].copy()
    out = out.rename(columns={comp_col: "component"})
    return out


def standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    city_col = pick_column(df, ["city", "municipality", "town"], label="city")
    station_col = pick_column(
        df,
        ["station_id", "station", "station_code", "airqualitystation"],
        label="station_id",
    )
    datetime_col = pick_column(
        df,
        ["datetime", "date", "timestamp", "Fecha"],
        label="datetime",
    )
    value_col = pick_column(
        df,
        ["value", "concentration", "measurement", "valor"],
        label="value",
    )

    out = df.rename(
        columns={
            city_col: "city",
            station_col: "station_id",
            datetime_col: "datetime",
            value_col: "value",
        }
    )
    out["city"] = out["city"].map(normalize_city)
    out["station_id"] = out["station_id"].astype(str).str.strip()
    out["datetime"] = pd.to_datetime(out["datetime"], errors="coerce")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["datetime", "value"])
    return out[["city", "station_id", "component", "datetime", "value"]]


def safe_component_tag(component: str) -> str:
    return component.replace(".", "")


def export_station_series(df: pd.DataFrame, out_dir: str = "data_pm") -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    needed = {"city", "station_id", "component", "datetime", "value"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")

    for (city, station_id, component), g in df.groupby(
        ["city", "station_id", "component"], dropna=False
    ):
        comp_tag = safe_component_tag(str(component))
        fname = f"{comp_tag}_{city}_{station_id}_hourly.csv"
        (
            g[["datetime", "value"]]
            .sort_values("datetime")
            .drop_duplicates(subset=["datetime"], keep="last")
            .to_csv(out_path / fname, index=False)
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consulta/carga y exporta solo PM10/PM2.5 por ciudad-estacion."
    )
    parser.add_argument("--input", required=True, help="CSV crudo de entrada.")
    parser.add_argument("--output-dir", default="data_pm", help="Directorio de salida.")
    parser.add_argument("--sep", default="auto", help="Separador CSV: auto, ; o ,")
    args = parser.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    sep = detect_sep(in_path) if args.sep == "auto" else args.sep
    df_raw = pd.read_csv(in_path, sep=sep, encoding="utf-8-sig")
    df_raw.columns = [c.replace("\ufeff", "").strip() for c in df_raw.columns]
    if len(df_raw.columns) <= 1:
        raise ValueError(
            f"Separador '{sep}' produce solo 1 columna en {in_path.name}. "
            "Usa --sep para especificarlo manualmente."
        )

    df_pm = filter_pm_only(df_raw)
    df_pm = standardize_schema(df_pm)
    export_station_series(df_pm, out_dir=args.output_dir)
    print(f"OK -> {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()
