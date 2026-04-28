#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


HORIZONS = [7, 14, 21, 28]
SEASON_ORDER = ["winter", "spring", "summer", "autumn"]


@dataclass(frozen=True)
class Config:
    input_path: Path
    output_dir: Path
    min_train_days: int = 365
    origin_stride: int = 7
    min_station_days: int = 730
    min_valid_pm10: int = 365
    max_missing_pct: float = 50.0
    max_origins: int = 260


def season_name(ts: pd.Timestamp) -> str:
    month = int(ts.month)
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def load_valencia_pm10(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    required = {"timestamp", "y", "pollutant", "city", "station_id", "is_missing"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns in {path}: {sorted(missing)}")
    df = df[(df["pollutant"] == "PM10") & (df["city"] == "Valencia")].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df["valid_pm10"] = df["y"].notna() & (df["is_missing"].astype(int) == 0)
    return df.sort_values(["station_id", "timestamp"])


def station_coverage(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    summary = (
        df.groupby("station_id", as_index=False)
        .agg(
            start_date=("timestamp", "min"),
            end_date=("timestamp", "max"),
            n_days=("timestamp", "size"),
            n_valid_pm10=("valid_pm10", "sum"),
        )
        .sort_values("station_id")
    )
    summary["missing_pct"] = 100.0 * (1.0 - summary["n_valid_pm10"] / summary["n_days"])
    summary["included_for_evaluation"] = (
        (summary["n_days"] >= cfg.min_station_days)
        & (summary["n_valid_pm10"] >= cfg.min_valid_pm10)
        & (summary["missing_pct"] <= cfg.max_missing_pct)
    )
    return summary


def wide_station_table(df: pd.DataFrame, stations: list[str]) -> pd.DataFrame:
    valid_y = df["y"].where(df["valid_pm10"], np.nan)
    tmp = df.assign(y_valid=valid_y)
    wide = tmp[tmp["station_id"].isin(stations)].pivot(
        index="timestamp", columns="station_id", values="y_valid"
    )
    full_idx = pd.date_range(wide.index.min(), wide.index.max(), freq="D")
    wide = wide.reindex(full_idx).sort_index()
    wide.index.name = "timestamp"
    return wide


def feature_row(
    series: pd.Series,
    origin_date: pd.Timestamp,
    station_id: str,
    fill_value: float,
) -> dict[str, float | str | int]:
    row: dict[str, float | str | int] = {
        "station_id": station_id,
        "month": int(origin_date.month),
        "doy_sin": float(np.sin(2.0 * np.pi * origin_date.dayofyear / 366.0)),
        "doy_cos": float(np.cos(2.0 * np.pi * origin_date.dayofyear / 366.0)),
        "season": season_name(origin_date),
    }
    for lag in range(1, 8):
        val = series.get(origin_date - pd.Timedelta(days=lag), np.nan)
        row[f"lag_{lag}"] = float(val) if pd.notna(val) else fill_value
    shifted = series.loc[: origin_date - pd.Timedelta(days=1)]
    for window in (7, 30):
        tail = shifted.tail(window)
        row[f"roll_mean_{window}"] = float(tail.mean()) if tail.notna().any() else fill_value
    return row


def feature_frame(series: pd.Series, station_id: str) -> pd.DataFrame:
    X = pd.DataFrame(index=series.index)
    X["station_id"] = station_id
    X["month"] = X.index.month.astype(int)
    X["doy_sin"] = np.sin(2.0 * np.pi * X.index.dayofyear / 366.0)
    X["doy_cos"] = np.cos(2.0 * np.pi * X.index.dayofyear / 366.0)
    X["season"] = [season_name(ts) for ts in X.index]
    for lag in range(1, 8):
        X[f"lag_{lag}"] = series.shift(lag)
    shifted = series.shift(1)
    X["roll_mean_7"] = shifted.rolling(7, min_periods=1).mean()
    X["roll_mean_30"] = shifted.rolling(30, min_periods=1).mean()
    return X


def fit_logistic_predict(
    train_rows: list[dict],
    test_rows: list[dict],
) -> tuple[np.ndarray, str]:
    y_train = np.array([r["event"] for r in train_rows], dtype=int)
    if len(y_train) < 50 or len(np.unique(y_train)) < 2 or y_train.sum() < 10:
        return np.full(len(test_rows), np.nan), "unstable_support"

    feature_cols = [
        "station_id",
        "month",
        "doy_sin",
        "doy_cos",
        "season",
        *[f"lag_{i}" for i in range(1, 8)],
        "roll_mean_7",
        "roll_mean_30",
    ]
    X_train = pd.DataFrame(train_rows)[feature_cols]
    X_test = pd.DataFrame(test_rows)[feature_cols]
    numeric = [
        "month",
        "doy_sin",
        "doy_cos",
        *[f"lag_{i}" for i in range(1, 8)],
        "roll_mean_7",
        "roll_mean_30",
    ]
    categorical = ["station_id", "season"]
    try:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
    model = Pipeline(
        steps=[
            (
                "prep",
                ColumnTransformer(
                    transformers=[
                        (
                            "num",
                            Pipeline(
                                steps=[
                                    ("imputer", SimpleImputer(strategy="median")),
                                    ("scaler", StandardScaler()),
                                ]
                            ),
                            numeric,
                        ),
                        ("cat", encoder, categorical),
                    ]
                ),
            ),
            (
                "logit",
                LogisticRegression(
                    solver="liblinear",
                    class_weight="balanced",
                    C=0.5,
                    max_iter=500,
                    random_state=42,
                ),
            ),
        ]
    )
    try:
        model.fit(X_train, y_train)
        return model.predict_proba(X_test)[:, 1], "ok"
    except Exception as exc:
        return np.full(len(test_rows), np.nan), f"fit_failed:{type(exc).__name__}"


def safe_brier(y: np.ndarray, p: np.ndarray) -> float:
    mask = np.isfinite(p)
    if mask.sum() == 0:
        return np.nan
    return float(brier_score_loss(y[mask], np.clip(p[mask], 0.0, 1.0)))


def safe_skill(model_bs: float, baseline_bs: float) -> float:
    if not np.isfinite(model_bs) or not np.isfinite(baseline_bs) or baseline_bs <= 0:
        return np.nan
    return float(1.0 - model_bs / baseline_bs)


def auc_metrics(y: np.ndarray, p: np.ndarray, support_ok: bool) -> tuple[float, float]:
    mask = np.isfinite(p)
    yy = y[mask]
    pp = p[mask]
    if not support_ok or len(yy) == 0 or len(np.unique(yy)) < 2:
        return np.nan, np.nan
    return float(roc_auc_score(yy, pp)), float(average_precision_score(yy, pp))


def build_fold_predictions(wide: pd.DataFrame, stations: list[str], cfg: Config) -> pd.DataFrame:
    max_h = max(HORIZONS)
    dates = wide.index
    origin_positions = list(range(cfg.min_train_days - 1, len(dates) - max_h, cfg.origin_stride))
    if cfg.max_origins > 0 and len(origin_positions) > cfg.max_origins:
        origin_positions = origin_positions[-cfg.max_origins :]
    rows: list[dict] = []
    feature_cache = {station: feature_frame(wide[station], station) for station in stations}

    for fold_id, pos in enumerate(origin_positions, start=1):
        origin_date = dates[pos]
        train_end = origin_date
        thresholds: dict[str, float] = {}
        for station in stations:
            y_train = wide.loc[:train_end, station].dropna()
            thresholds[station] = float(y_train.quantile(0.90)) if len(y_train) else np.nan

        for horizon in HORIZONS:
            train_rows: list[dict] = []
            test_rows: list[dict] = []
            station_payload: list[dict] = []
            for station in stations:
                series = wide[station]
                threshold = thresholds[station]
                if not np.isfinite(threshold):
                    continue

                train_origin_dates = dates[
                    (dates >= dates[0] + pd.Timedelta(days=30))
                    & (dates + pd.Timedelta(days=horizon) <= train_end)
                ]
                target_dates = train_origin_dates + pd.Timedelta(days=horizon)
                target_values = series.reindex(target_dates).to_numpy()
                valid_target = pd.notna(target_values)
                valid_train_origins = train_origin_dates[valid_target]
                valid_train_targets = target_values[valid_target]
                train_events = (valid_train_targets.astype(float) > threshold).astype(int)
                labels_for_clim = list(zip(valid_train_origins, train_events))
                if len(valid_train_origins):
                    station_train = feature_cache[station].loc[valid_train_origins].copy()
                    station_train["event"] = train_events
                    train_rows.extend(station_train.to_dict("records"))

                target_date = origin_date + pd.Timedelta(days=horizon)
                y_target = series.get(target_date, np.nan)
                y_origin = series.get(origin_date, np.nan)
                if pd.isna(y_target):
                    continue
                actual = int(float(y_target) > threshold)
                persistence = (
                    float(int(float(y_origin) > threshold)) if pd.notna(y_origin) else np.nan
                )
                origin_season = season_name(origin_date)
                target_season = season_name(target_date)
                labels = pd.DataFrame(labels_for_clim, columns=["origin_date", "event"])
                if labels.empty:
                    global_clim = np.nan
                    seasonal_origin_clim = np.nan
                    seasonal_target_clim = np.nan
                else:
                    labels["origin_season"] = labels["origin_date"].map(season_name)
                    labels["target_season"] = (
                        labels["origin_date"] + pd.Timedelta(days=horizon)
                    ).map(season_name)
                    global_clim = float(labels["event"].mean())
                    seasonal_origin = labels.loc[labels["origin_season"] == origin_season, "event"]
                    seasonal_target = labels.loc[labels["target_season"] == target_season, "event"]
                    seasonal_origin_clim = (
                        float(seasonal_origin.mean()) if len(seasonal_origin) else global_clim
                    )
                    seasonal_target_clim = (
                        float(seasonal_target.mean()) if len(seasonal_target) else global_clim
                    )

                feat = feature_cache[station].loc[origin_date].to_dict()
                test_rows.append(feat)
                station_payload.append(
                    {
                        "fold_id": fold_id,
                        "origin_date": origin_date,
                        "target_date": target_date,
                        "station_id": station,
                        "horizon": horizon,
                        "actual_event": actual,
                        "persistence_event": persistence,
                        "seasonal_climatology_origin": seasonal_origin_clim,
                        "seasonal_climatology_target": seasonal_target_clim,
                        "global_climatology": global_clim,
                        "origin_season": origin_season,
                        "target_season": target_season,
                        "p90_train_station": threshold,
                    }
                )

            if not station_payload:
                continue
            preds, status = fit_logistic_predict(train_rows, test_rows)
            for payload, pred in zip(station_payload, preds):
                payload["logistic_lag_roll_season_station"] = float(pred) if np.isfinite(pred) else np.nan
                payload["logistic_status"] = status
                rows.append(payload)

    return pd.DataFrame(rows)


def long_metric_rows(preds: pd.DataFrame, support_flags: pd.DataFrame) -> pd.DataFrame:
    model_cols = {
        "logistic_lag_roll_season_station": "logistic_lag_roll_season_station",
        "persistence_event": "persistence_event",
        "seasonal_climatology": None,
        "global_climatology": "global_climatology",
    }
    rows: list[dict] = []
    flag_lookup = {
        (r.season_type, r.season, int(r.horizon)): bool(r.support_ok)
        for r in support_flags.itertuples(index=False)
    }

    for season_type, season_col, seasonal_col in [
        ("origin_season", "origin_season", "seasonal_climatology_origin"),
        ("target_season", "target_season", "seasonal_climatology_target"),
    ]:
        for row in preds.itertuples(index=False):
            y = np.array([int(row.actual_event)])
            base_persistence = np.array([row.persistence_event], dtype=float)
            base_seasonal = np.array([getattr(row, seasonal_col)], dtype=float)
            base_global = np.array([row.global_climatology], dtype=float)
            season = getattr(row, season_col)
            support_ok = flag_lookup.get((season_type, season, int(row.horizon)), False)
            for model_name, col in model_cols.items():
                if model_name == "seasonal_climatology":
                    p = base_seasonal
                else:
                    p = np.array([getattr(row, col)], dtype=float)
                bs = safe_brier(y, p)
                brier_persistence = safe_brier(y, base_persistence)
                brier_seasonal = safe_brier(y, base_seasonal)
                brier_global = safe_brier(y, base_global)
                roc_auc, pr_auc = auc_metrics(y, p, support_ok=support_ok)
                rows.append(
                    {
                        "fold_id": int(row.fold_id),
                        "station_id": row.station_id,
                        "season_type": season_type,
                        "season": season,
                        "horizon": int(row.horizon),
                        "model_name": model_name,
                        "n_samples": 1,
                        "n_positive_events": int(row.actual_event),
                        "positive_rate": float(row.actual_event),
                        "brier_score": bs,
                        "bss_vs_persistence": safe_skill(bs, brier_persistence),
                        "bss_vs_seasonal_climatology": safe_skill(bs, brier_seasonal),
                        "bss_vs_global_climatology": safe_skill(bs, brier_global),
                        "roc_auc": roc_auc,
                        "pr_auc": pr_auc,
                    }
                )
    return pd.DataFrame(rows)


def event_support(preds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    support_rows: list[dict] = []
    fold_rows: list[dict] = []
    for season_type, season_col in [
        ("origin_season", "origin_season"),
        ("target_season", "target_season"),
    ]:
        group_cols = ["station_id", season_col, "horizon"]
        support = (
            preds.groupby(group_cols)
            .agg(
                n_samples=("actual_event", "size"),
                n_positive_events=("actual_event", "sum"),
            )
            .reset_index()
        )
        for rec in support.itertuples(index=False):
            support_rows.append(
                {
                    "station_id": rec.station_id,
                    "season_type": season_type,
                    "season": getattr(rec, season_col),
                    "horizon": int(rec.horizon),
                    "n_samples": int(rec.n_samples),
                    "n_positive_events": int(rec.n_positive_events),
                    "positive_rate": float(rec.n_positive_events / rec.n_samples)
                    if rec.n_samples
                    else np.nan,
                }
            )

        fold_support = (
            preds.groupby([season_col, "horizon", "fold_id"])["actual_event"].sum().reset_index()
        )
        total = (
            preds.groupby([season_col, "horizon"])
            .agg(total_positive_events=("actual_event", "sum"), n_samples=("actual_event", "size"))
            .reset_index()
        )
        folds_with_pos = (
            fold_support[fold_support["actual_event"] > 0]
            .groupby([season_col, "horizon"])["fold_id"]
            .nunique()
            .reset_index(name="folds_with_positive_events")
        )
        flags = total.merge(folds_with_pos, on=[season_col, "horizon"], how="left")
        flags["folds_with_positive_events"] = flags["folds_with_positive_events"].fillna(0).astype(int)
        for rec in flags.itertuples(index=False):
            positives = int(rec.total_positive_events)
            folds_pos = int(rec.folds_with_positive_events)
            fold_rows.append(
                {
                    "season_type": season_type,
                    "season": getattr(rec, season_col),
                    "horizon": int(rec.horizon),
                    "total_positive_events": positives,
                    "folds_with_positive_events": folds_pos,
                    "support_ok": positives >= 30 and folds_pos >= 3,
                }
            )
    return pd.DataFrame(support_rows), pd.DataFrame(fold_rows)


def summary_matrix(metrics: pd.DataFrame, season_type: str, skill_col: str) -> pd.DataFrame:
    sub = metrics[
        (metrics["season_type"] == season_type)
        & (metrics["model_name"] == "logistic_lag_roll_season_station")
    ].copy()
    mat = sub.pivot_table(index="season", columns="horizon", values=skill_col, aggfunc="mean")
    mat = mat.reindex(SEASON_ORDER)
    mat = mat.rename(columns={h: f"h{h}" for h in HORIZONS})
    return mat[[f"h{h}" for h in HORIZONS]]


def support_matrix(preds: pd.DataFrame) -> pd.DataFrame:
    mat = preds.pivot_table(
        index="target_season", columns="horizon", values="actual_event", aggfunc="sum"
    )
    mat = mat.reindex(SEASON_ORDER).rename(columns={h: f"h{h}" for h in HORIZONS})
    return mat[[f"h{h}" for h in HORIZONS]].fillna(0).astype(int)


def write_readme(
    cfg: Config,
    stations: list[str],
    coverage: pd.DataFrame,
    support_flags: pd.DataFrame,
    verdict: str,
) -> None:
    unstable = support_flags[~support_flags["support_ok"]].copy()
    criteria = {
        "min_station_days": cfg.min_station_days,
        "min_valid_pm10": cfg.min_valid_pm10,
        "max_missing_pct": cfg.max_missing_pct,
        "min_train_days": cfg.min_train_days,
        "origin_stride_days": cfg.origin_stride,
        "max_origins": cfg.max_origins,
    }
    lines = [
        "# Event predictability audit: PM10 Valencia multistation",
        "",
        f"Dataset used: `{cfg.input_path}`.",
        "",
        "Station inclusion criteria:",
        f"- `{json.dumps(criteria, sort_keys=True)}`",
        f"- Included stations: {', '.join(stations)}",
        "",
        "Event definition:",
        "- For every fold and station, `event_t = 1 if PM10_t > p90_train_station`.",
        "- `p90_train_station` is computed inside the expanding training window and separately for each station.",
        "- No global full-series p90 and no pooled-station threshold is used.",
        "",
        "Horizon definition:",
        "- Horizons are `h = 7, 14, 21, 28` days.",
        "- For origin day `t`, the evaluated target is `event_(t+h)`.",
        "",
        "Season diagnostics:",
        "- `origin_season`: season of origin day `t`.",
        "- `target_season`: season of target day `t+h`; preferred for event-regime interpretation.",
        "",
        "Validation protocol:",
        "- Expanding-window rolling-origin validation.",
        "- Origin stride is 7 days.",
        "- Fold-level and station-level predictions are preserved in the metric table.",
        "",
        "Baselines:",
        "- `persistence_event`: `p_hat(t+h) = event_t`, using the fold-specific station-specific threshold.",
        "- Station-specific seasonal climatology estimated from training origins only.",
        "- Station-specific global climatology estimated from training origins only.",
        "",
        "Minimal model:",
        "- `logistic_lag_roll_season_station` pooled across included stations.",
        "- Features: PM10 lags 1-7, shifted rolling means 7 and 30 days, month, day-of-year sine/cosine, season, station encoding.",
        "- Numeric imputation and scaling are fitted train-only inside each fold.",
        "",
        "Leakage safeguards:",
        "- No random split.",
        "- No full-series threshold, scaling, imputation, or climatology.",
        "- Training labels for climatology and logistic model use only origins whose target date is within the fold training window.",
        "- Target dates are not used to construct origin-time features.",
        "",
        "Support diagnostics:",
        "- Season-horizon cells are unstable if total positive events < 30 or fewer than 3 folds contain positive events.",
        "- ROC-AUC and PR-AUC are left undefined when class support is insufficient; fold-station rows also contain single samples, so AUC fields are not interpreted.",
        "",
        f"Design status: **{verdict}**.",
        "",
        "Unstable cells:",
    ]
    if unstable.empty:
        lines.append("- None.")
    else:
        for rec in unstable.sort_values(["season_type", "season", "horizon"]).itertuples(index=False):
            lines.append(
                f"- {rec.season_type} {rec.season} h{int(rec.horizon)}: "
                f"{int(rec.total_positive_events)} positives, "
                f"{int(rec.folds_with_positive_events)} folds with positives."
            )
    lines.extend(
        [
            "",
            "Station coverage summary:",
            "",
            "```text",
            coverage.to_string(index=False),
            "```",
            "",
        ]
    )
    (cfg.output_dir / "README_event_predictability_multistation_valencia.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/modeling/pm10_daily_regular.parquet",
        type=Path,
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/event_predictability_multistation_valencia",
        type=Path,
    )
    args = parser.parse_args()
    cfg = Config(input_path=args.input, output_dir=args.output_dir)
    if cfg.output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists; refusing to overwrite: {cfg.output_dir}"
        )
    cfg.output_dir.mkdir(parents=True, exist_ok=False)

    df = load_valencia_pm10(cfg.input_path)
    coverage = station_coverage(df, cfg)
    stations = coverage.loc[coverage["included_for_evaluation"], "station_id"].tolist()
    if not stations:
        raise RuntimeError("No Valencia PM10 stations satisfy the inclusion criteria.")

    wide = wide_station_table(df, stations)
    preds = build_fold_predictions(wide, stations, cfg)
    support, support_flags = event_support(preds)
    metrics = long_metric_rows(preds, support_flags)

    coverage.to_csv(cfg.output_dir / "station_coverage_summary.csv", index=False)
    support.to_csv(
        cfg.output_dir / "event_support_by_station_season_horizon.csv", index=False
    )
    metrics.to_csv(cfg.output_dir / "event_skill_fold_station_level.csv", index=False)
    summary_matrix(metrics, "origin_season", "bss_vs_persistence").to_csv(
        cfg.output_dir / "summary_matrix_bss_vs_persistence_origin_season.csv"
    )
    summary_matrix(metrics, "target_season", "bss_vs_persistence").to_csv(
        cfg.output_dir / "summary_matrix_bss_vs_persistence_target_season.csv"
    )
    summary_matrix(metrics, "target_season", "bss_vs_seasonal_climatology").to_csv(
        cfg.output_dir / "summary_matrix_bss_vs_seasonal_climatology_target_season.csv"
    )
    support_matrix(preds).to_csv(cfg.output_dir / "event_support_matrix_target_season.csv")

    target_flags = support_flags[support_flags["season_type"] == "target_season"]
    if target_flags.empty or not target_flags["support_ok"].any():
        verdict = "Data-insufficient"
    elif not target_flags["support_ok"].all():
        verdict = "Salvageable"
    else:
        verdict = "Ready"
    write_readme(cfg, stations, coverage, support_flags, verdict)

    print(f"Created {cfg.output_dir}")
    print("Included stations:")
    for station in stations:
        print(f"- {station}")
    print(f"Final verdict: {verdict}")


if __name__ == "__main__":
    main()
