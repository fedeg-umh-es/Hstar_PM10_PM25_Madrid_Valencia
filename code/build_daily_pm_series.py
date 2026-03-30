#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

HOURLY_PATTERN = re.compile(r"^(PM10|PM25)_.+_.+_hourly\.csv$")


def hourly_to_daily(path: Path, agg: str) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["datetime"]).sort_values("datetime")
    df = df.set_index("datetime")
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="h")
    y = df["value"].reindex(full_idx)

    if agg == "mean":
        daily = y.resample("D").mean()
    elif agg == "max":
        daily = y.resample("D").max()
    else:
        raise ValueError("AGG debe ser 'mean' o 'max'")

    out = daily.dropna().rename("value").reset_index()
    out.columns = ["date", "value"]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construye series diarias PM10/PM25 desde series horarias."
    )
    parser.add_argument("--input-dir", default="data_pm")
    parser.add_argument("--output-dir", default="data_pm_daily")
    parser.add_argument("--agg", default="mean", choices=["mean", "max"])
    args = parser.parse_args()

    in_dir = Path(args.input_dir).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(in_dir.glob("*_hourly.csv")) if HOURLY_PATTERN.match(p.name)]
    if not files:
        raise ValueError(f"No hay archivos PM horarios en {in_dir}")

    for f in files:
        df_daily = hourly_to_daily(f, agg=args.agg)
        out_name = f.name.replace("_hourly.csv", "_daily.csv")
        out_path = out_dir / out_name
        df_daily.to_csv(out_path, index=False)
        print(f"OK -> {out_path}")


if __name__ == "__main__":
    main()
