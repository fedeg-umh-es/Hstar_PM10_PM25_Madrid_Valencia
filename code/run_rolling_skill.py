#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
from xgboost import XGBRegressor


@dataclass
class FoldForecast:
    origin_date: pd.Timestamp
    horizon: int
    actual: float
    persist_simple: float
    persist_seasonal: float
    sarima: float
    boosting: float


ALLOWED_POLLUTANTS = {"PM10", "PM2.5"}
BATCH_PATTERN = re.compile(r"^(PM10|PM25|PM2\.5)_(.+)_(.+)_daily\.csv$")


def normalize_pollutant(x: str) -> str:
    x = str(x).strip().upper().replace(" ", "")
    if x == "PM25":
        return "PM2.5"
    return x


def validate_pollutant(x: str) -> str:
    norm = normalize_pollutant(x)
    if norm not in ALLOWED_POLLUTANTS:
        raise ValueError(f"Contaminante fuera de alcance: {x}. Solo PM10/PM2.5.")
    return norm


def safe_pollutant_tag(pollutant: str) -> str:
    return normalize_pollutant(pollutant).replace(".", "")


def parse_meta_from_daily_filename(path: Path) -> dict[str, str] | None:
    m = BATCH_PATTERN.match(path.name)
    if not m:
        return None
    pollutant, city, station_id = m.groups()
    return {
        "pollutant": validate_pollutant(pollutant),
        "city": city,
        "station_id": station_id,
    }


def prepare_series(path_csv: Path, date_col: str = "date", value_col: str = "value") -> pd.Series:
    df = pd.read_csv(path_csv, parse_dates=[date_col])
    df = df[[date_col, value_col]].copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.sort_values(date_col).drop_duplicates(subset=[date_col], keep="last")

    full_idx = pd.date_range(df[date_col].min(), df[date_col].max(), freq="D")
    y = df.set_index(date_col)[value_col].reindex(full_idx)
    y.index.name = "date"
    return y


def impute_train_only(y_train: pd.Series) -> pd.Series:
    out = y_train.copy()
    out = out.ffill()
    fill_value = float(out.median()) if out.notna().any() else 0.0
    out = out.fillna(fill_value)
    return out


def build_lagged_features(
    y: pd.Series, lags: Iterable[int], add_calendar: bool = True
) -> tuple[pd.DataFrame, pd.Series]:
    X = pd.DataFrame(index=y.index)
    for lag in lags:
        X[f"lag_{lag}"] = y.shift(lag)
    if add_calendar:
        X["dow"] = y.index.dayofweek
        X["month"] = y.index.month
    target = y.copy()
    mask = X.notna().all(axis=1) & target.notna()
    return X.loc[mask], target.loc[mask]


def predict_boosting_recursive(
    y_train_imp: pd.Series,
    origin_date: pd.Timestamp,
    hmax: int,
    lags: list[int],
) -> list[float]:
    X_train, y_train = build_lagged_features(y_train_imp, lags=lags, add_calendar=True)
    if len(X_train) < max(80, 4 * len(lags)):
        return [np.nan] * hmax

    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=1,
    )
    model.fit(X_train, y_train)

    history = y_train_imp.copy()
    preds: list[float] = []
    for step in range(1, hmax + 1):
        ts = origin_date + pd.Timedelta(days=step)
        row = {f"lag_{lag}": float(history.loc[ts - pd.Timedelta(days=lag)]) for lag in lags}
        row["dow"] = ts.dayofweek
        row["month"] = ts.month
        x = pd.DataFrame([row])
        pred = float(model.predict(x)[0])
        preds.append(pred)
        history.loc[ts] = pred
    return preds


def predict_sarima(
    y_train_imp: pd.Series,
    hmax: int,
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
) -> list[float]:
    try:
        model = SARIMAX(
            y_train_imp,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
            simple_differencing=False,
        )
        res = model.fit(disp=False, maxiter=120)
        fcst = res.get_forecast(steps=hmax).predicted_mean
        return [float(v) for v in fcst.values]
    except Exception as e:
        print(f"SARIMA fit failed: {e}")
        return [np.nan] * hmax


def evaluate_models(
    y: pd.Series,
    hmax: int,
    min_train_days: int,
    origin_stride: int,
    max_origins: int | None,
    sarima_order: tuple[int, int, int],
    sarima_seasonal_order: tuple[int, int, int, int],
    lags_boosting: list[int],
) -> pd.DataFrame:
    n = len(y)
    origin_positions = list(range(min_train_days - 1, n - hmax, origin_stride))
    origin_positions = [p for p in origin_positions if pd.notna(y.iloc[p])]
    if max_origins is not None and len(origin_positions) > max_origins:
        origin_positions = origin_positions[-max_origins:]

    rows: list[FoldForecast] = []
    for pos in origin_positions:
        origin_date = y.index[pos]
        y_train_raw = y.iloc[: pos + 1]
        y_train_imp = impute_train_only(y_train_raw)

        ps_val = float(y_train_raw.iloc[-1]) if pd.notna(y_train_raw.iloc[-1]) else np.nan
        sarima_preds = predict_sarima(
            y_train_imp=y_train_imp,
            hmax=hmax,
            order=sarima_order,
            seasonal_order=sarima_seasonal_order,
        )
        boost_preds = predict_boosting_recursive(
            y_train_imp=y_train_imp,
            origin_date=origin_date,
            hmax=hmax,
            lags=lags_boosting,
        )

        for h in range(1, hmax + 1):
            target = y.iloc[pos + h]
            if pd.isna(target):
                continue

            # Persistencia estacional: y_{t+h-7} (solo si el índice está en rango train)
            seasonal_idx = pos + h - 7
            if 0 <= seasonal_idx <= pos:
                pss = y_train_raw.iloc[seasonal_idx]
                pss = float(pss) if pd.notna(pss) else np.nan
            else:
                pss = np.nan

            rows.append(
                FoldForecast(
                    origin_date=origin_date,
                    horizon=h,
                    actual=float(target),
                    persist_simple=ps_val,
                    persist_seasonal=pss,
                    sarima=float(sarima_preds[h - 1]),
                    boosting=float(boost_preds[h - 1]),
                )
            )

    return pd.DataFrame([r.__dict__ for r in rows])


def compute_metrics_and_skill(df_preds: pd.DataFrame, hmax: int) -> pd.DataFrame:
    if df_preds.empty or "horizon" not in df_preds.columns:
        return pd.DataFrame(
            columns=[
                "horizon",
                "model",
                "n_eval",
                "mae",
                "rmse",
                "mae_baseline_persist",
                "rmse_baseline_persist",
                "skill_mae_vs_persist",
                "skill_rmse_vs_persist",
            ]
        )

    models = ["persist_simple", "persist_seasonal", "sarima", "boosting"]
    records: list[dict] = []

    for h in range(1, hmax + 1):
        dh = df_preds[df_preds["horizon"] == h]
        base = dh["persist_simple"]
        valid_base = dh["actual"].notna() & base.notna()
        if valid_base.sum() == 0:
            continue
        for m in models:
            valid = dh["actual"].notna() & dh[m].notna()
            if valid.sum() == 0:
                mae = np.nan
                rmse = np.nan
            else:
                mae = mean_absolute_error(dh.loc[valid, "actual"], dh.loc[valid, m])
                rmse = np.sqrt(mean_squared_error(dh.loc[valid, "actual"], dh.loc[valid, m]))

            # Skill computed on the intersection of valid_base and valid so that
            # numerator and denominator always use the same set of observations.
            skill_sample = valid_base & valid
            skill_mae = np.nan
            skill_rmse = np.nan
            b_mae: float = np.nan
            b_rmse: float = np.nan
            if skill_sample.sum() > 0:
                b_mae = mean_absolute_error(
                    dh.loc[skill_sample, "actual"], base.loc[skill_sample]
                )
                b_rmse = np.sqrt(
                    mean_squared_error(
                        dh.loc[skill_sample, "actual"], base.loc[skill_sample]
                    )
                )
                m_mae = mean_absolute_error(
                    dh.loc[skill_sample, "actual"], dh.loc[skill_sample, m]
                )
                m_rmse = np.sqrt(
                    mean_squared_error(
                        dh.loc[skill_sample, "actual"], dh.loc[skill_sample, m]
                    )
                )
                if b_mae > 0:
                    skill_mae = 1.0 - (m_mae / b_mae)
                if b_rmse > 0:
                    skill_rmse = 1.0 - (m_rmse / b_rmse)

            records.append(
                {
                    "horizon": h,
                    "model": m,
                    "n_eval": int(valid.sum()),
                    "mae": float(mae) if pd.notna(mae) else np.nan,
                    "rmse": float(rmse) if pd.notna(rmse) else np.nan,
                    "mae_baseline_persist": float(b_mae) if pd.notna(b_mae) else np.nan,
                    "rmse_baseline_persist": float(b_rmse) if pd.notna(b_rmse) else np.nan,
                    "skill_mae_vs_persist": float(skill_mae)
                    if pd.notna(skill_mae)
                    else np.nan,
                    "skill_rmse_vs_persist": float(skill_rmse)
                    if pd.notna(skill_rmse)
                    else np.nan,
                }
            )

    return pd.DataFrame(records).sort_values(["model", "horizon"]).reset_index(drop=True)


def compute_skill_curve(rmse_model: np.ndarray, rmse_baseline: np.ndarray) -> np.ndarray:
    rmse_model = np.asarray(rmse_model, dtype=float)
    rmse_baseline = np.asarray(rmse_baseline, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        skill = 1.0 - (rmse_model / rmse_baseline)
    skill[~np.isfinite(skill)] = np.nan
    return skill


def extract_H_descriptors(skill: np.ndarray) -> tuple[int, int, int]:
    H = len(skill)

    pos_idx = np.where(skill > 0)[0]
    H_star_relax = int(pos_idx.max() + 1) if len(pos_idx) > 0 else 0

    best_len = 0
    current_len = 0
    for val in skill:
        if pd.notna(val) and val > 0:
            current_len += 1
            best_len = max(best_len, current_len)
        else:
            current_len = 0
    H_star_strict = int(best_len)

    return int(H), int(H_star_relax), int(H_star_strict)


def summarize_models(rmse_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for model, g in rmse_df.groupby("model"):
        g = g.sort_values("h")
        skill = compute_skill_curve(
            g["rmse_model"].to_numpy(),
            g["rmse_baseline"].to_numpy(),
        )
        H, H_star_relax, H_star_strict = extract_H_descriptors(skill)
        rows.append(
            {
                "model": model,
                "H": H,
                "H_star_relax": H_star_relax,
                "H_star_strict": H_star_strict,
            }
        )
    return pd.DataFrame(rows).sort_values("model").reset_index(drop=True)


def derive_hstar(metrics: pd.DataFrame, hmax: int) -> pd.DataFrame:
    if metrics.empty:
        return pd.DataFrame(columns=["model", "H", "H_star_relax", "H_star_strict"])

    rows: list[pd.DataFrame] = []
    for model, g in metrics.groupby("model"):
        gm = g.set_index("horizon").reindex(range(1, hmax + 1))
        rows.append(
            pd.DataFrame(
                {
                    "model": model,
                    "h": range(1, hmax + 1),
                    "rmse_model": gm["rmse"].to_numpy(),
                    "rmse_baseline": gm["rmse_baseline_persist"].to_numpy(),
                }
            )
        )
    rmse_df = pd.concat(rows, ignore_index=True)
    return summarize_models(rmse_df)


def parse_tuple_arg(text: str) -> tuple[int, ...]:
    return tuple(int(x.strip()) for x in text.split(","))


def run_one_series(
    *,
    input_path: Path,
    date_col: str,
    value_col: str,
    city: str,
    station_id: str,
    pollutant: str,
    hmax: int,
    min_train_days: int,
    origin_stride: int,
    max_origins: int | None,
    sarima_order: tuple[int, int, int],
    sarima_seasonal_order: tuple[int, int, int, int],
    lags_boosting: list[int],
    output_dir: Path,
) -> None:
    pollutant = validate_pollutant(pollutant)
    y = prepare_series(input_path, date_col=date_col, value_col=value_col)
    df_preds = evaluate_models(
        y=y,
        hmax=hmax,
        min_train_days=min_train_days,
        origin_stride=origin_stride,
        max_origins=max_origins,
        sarima_order=sarima_order,
        sarima_seasonal_order=sarima_seasonal_order,
        lags_boosting=lags_boosting,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    tag = safe_pollutant_tag(pollutant)
    city_tag = str(city).replace(" ", "_")
    station_tag = str(station_id).replace(" ", "_")
    preds_path = output_dir / f"rolling_origin_predictions_{tag}_{city_tag}_{station_tag}.csv"
    metrics_path = output_dir / f"rolling_origin_metrics_{tag}_{city_tag}_{station_tag}.csv"
    hstar_path = output_dir / f"hstar_summary_{tag}_{city_tag}_{station_tag}.csv"

    if df_preds.empty:
        pd.DataFrame(
            columns=[
                "origin_date",
                "horizon",
                "actual",
                "persist_simple",
                "persist_seasonal",
                "sarima",
                "boosting",
            ]
        ).to_csv(preds_path, index=False)
        pd.DataFrame(
            columns=[
                "horizon",
                "model",
                "n_eval",
                "mae",
                "rmse",
                "mae_baseline_persist",
                "rmse_baseline_persist",
                "skill_mae_vs_persist",
                "skill_rmse_vs_persist",
            ]
        ).to_csv(metrics_path, index=False)
        pd.DataFrame(columns=["model", "H", "H_star_relax", "H_star_strict"]).to_csv(
            hstar_path, index=False
        )
        print(
            f"SKIP -> {tag} | {city_tag} | {station_tag} (sin folds evaluables: "
            f"min_train_days={min_train_days}, hmax={hmax})"
        )
        return

    metrics = compute_metrics_and_skill(df_preds, hmax=hmax)
    hstar = derive_hstar(metrics, hmax=hmax)

    df_preds.to_csv(preds_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    hstar.to_csv(hstar_path, index=False)

    print(f"OK -> {preds_path}")
    print(f"OK -> {metrics_path}")
    print(f"OK -> {hstar_path}")
    print(f"Folds evaluados: {df_preds['origin_date'].nunique()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rolling-origin + Skill(h) para series diarias univariantes (Hmax=7)."
    )
    parser.add_argument("--input", help="CSV con columnas date,value.")
    parser.add_argument("--batch", action="store_true", help="Ejecuta sobre data_pm_daily.")
    parser.add_argument("--input-dir", default="data_pm_daily", help="Dir de entrada batch.")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--value-col", default="value")
    parser.add_argument("--city", default="Valencia")
    parser.add_argument("--station-id", default="Politecnico")
    parser.add_argument("--pollutant", default="PM10")
    parser.add_argument("--hmax", type=int, default=7)
    parser.add_argument("--min-train-days", type=int, default=365)
    parser.add_argument("--origin-stride", type=int, default=7)
    parser.add_argument("--max-origins", type=int, default=120)
    parser.add_argument("--sarima-order", default="1,0,1")
    parser.add_argument("--sarima-seasonal-order", default="1,0,0,7")
    parser.add_argument("--lags-boosting", default="1,2,3,7,14,21,28")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    sarima_order = parse_tuple_arg(args.sarima_order)
    sarima_seasonal = parse_tuple_arg(args.sarima_seasonal_order)
    lags_boosting = [int(x.strip()) for x in args.lags_boosting.split(",")]
    out_dir = Path(args.output_dir).resolve()

    if args.batch:
        in_dir = Path(args.input_dir).resolve()
        files = []
        for p in sorted(in_dir.glob("*_daily.csv")):
            meta = parse_meta_from_daily_filename(p)
            if meta is not None:
                files.append((p, meta))
        if not files:
            raise ValueError(f"No se encontraron series PM válidas en {in_dir}")

        for path, meta in files:
            print(
                f"Procesando {meta['pollutant']} | {meta['city']} | {meta['station_id']}"
            )
            run_one_series(
                input_path=path,
                date_col=args.date_col,
                value_col=args.value_col,
                city=meta["city"],
                station_id=meta["station_id"],
                pollutant=meta["pollutant"],
                hmax=args.hmax,
                min_train_days=args.min_train_days,
                origin_stride=args.origin_stride,
                max_origins=args.max_origins if args.max_origins > 0 else None,
                sarima_order=(sarima_order[0], sarima_order[1], sarima_order[2]),
                sarima_seasonal_order=(
                    sarima_seasonal[0],
                    sarima_seasonal[1],
                    sarima_seasonal[2],
                    sarima_seasonal[3],
                ),
                lags_boosting=lags_boosting,
                output_dir=out_dir,
            )
    else:
        if not args.input:
            raise ValueError("Debes pasar --input o usar --batch.")
        run_one_series(
            input_path=Path(args.input).resolve(),
            date_col=args.date_col,
            value_col=args.value_col,
            city=args.city,
            station_id=args.station_id,
            pollutant=args.pollutant,
            hmax=args.hmax,
            min_train_days=args.min_train_days,
            origin_stride=args.origin_stride,
            max_origins=args.max_origins if args.max_origins > 0 else None,
            sarima_order=(sarima_order[0], sarima_order[1], sarima_order[2]),
            sarima_seasonal_order=(
                sarima_seasonal[0],
                sarima_seasonal[1],
                sarima_seasonal[2],
                sarima_seasonal[3],
            ),
            lags_boosting=lags_boosting,
            output_dir=out_dir,
        )


if __name__ == "__main__":
    main()
