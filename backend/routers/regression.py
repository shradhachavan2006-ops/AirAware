"""Regression analysis endpoints.

GET /analysis/{dataset_id}/regression
    - Pearson correlation between PM2.5 and its lag/rolling features
    - Simple linear regression (lag_1 → pm25_mean) using scipy
    - Multiple linear regression (lag_1, lag_7, rolling_3 → pm25_mean) with
      correct OLS p-values computed from the residual distribution
    - Residual diagnostics
    - All calculations are performed on the dataset-in-memory, never on disk data.

Statistical correctness:
    - Lag features are built without look-ahead (each row predicts the NEXT day,
      using only information available at the time — identical to forecast_engine.py).
    - OLS standard errors and p-values use the design-matrix formula:
        SE = sqrt(MSE * diag((X'X)^{-1}))
    - p-values are two-tailed t-statistics against the t-distribution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.stats as stats
from fastapi import APIRouter, HTTPException
from sklearn.linear_model import LinearRegression

from backend.dataset_store import get_df, get_info

router = APIRouter(prefix="/analysis", tags=["Regression"])

# Feature definitions
FEATURES = {
    "lag_1":          lambda s: s.shift(1),
    "lag_7":          lambda s: s.shift(7),
    "rolling_mean_3": lambda s: s.rolling(3, min_periods=3).mean(),
    "rolling_mean_7": lambda s: s.rolling(7, min_periods=7).mean(),
}

_MIN_ROWS = 15   # minimum samples needed for regression


def _build_feature_df(series: pd.Series) -> pd.DataFrame:
    """Build feature matrix for regression.

    Target is the NEXT day's PM2.5 (shift(-1)), representing the actual
    next-day prediction task. Only rows with all features and target
    non-NaN are returned (identical logic to forecast_engine._make_features).
    """
    df = pd.DataFrame({"pm25_mean": series})
    for fname, func in FEATURES.items():
        df[fname] = func(series)
    df["target"] = series.shift(-1)    # next-day PM2.5 (what we predict)
    return df.dropna()


def _pearson(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Return (r, p_value). Handles constant arrays gracefully."""
    if x.std() == 0 or y.std() == 0:
        return float("nan"), float("nan")
    r, p = stats.pearsonr(x, y)
    return float(r), float(p)


def _ols_pvalues(
    X: np.ndarray,
    y: np.ndarray,
    coefs: np.ndarray,
    intercept: float,
) -> tuple[np.ndarray, float]:
    """Compute OLS standard errors and two-tailed p-values.

    Parameters
    ----------
    X         : design matrix  (n × k), WITHOUT intercept column
    y         : target vector  (n,)
    coefs     : fitted coefficients (k,)
    intercept : fitted intercept scalar

    Returns
    -------
    p_values  : (k+1,) array — intercept first, then feature p-values
    mse       : mean squared error of residuals
    """
    n, k = X.shape
    df_resid = n - k - 1
    if df_resid <= 0:
        return np.full(k + 1, float("nan")), float("nan")

    y_pred = X @ coefs + intercept
    residuals = y - y_pred
    mse = float(np.sum(residuals**2) / df_resid)

    # Augment X with intercept column
    X_aug = np.column_stack([np.ones(n), X])
    try:
        XtX_inv = np.linalg.pinv(X_aug.T @ X_aug)
    except np.linalg.LinAlgError:
        return np.full(k + 1, float("nan")), mse

    se = np.sqrt(mse * np.diag(XtX_inv))
    full_coefs = np.concatenate([[intercept], coefs])
    t_stats = full_coefs / (se + 1e-12)
    p_values = 2.0 * stats.t.sf(np.abs(t_stats), df=df_resid)
    return p_values, mse


def _fmt_p(p: float) -> str:
    if np.isnan(p):
        return "N/A"
    if p < 0.0001:
        return "< 0.0001"
    return f"{p:.4f}"


def _significance_label(p: float) -> str:
    if np.isnan(p):
        return "—"
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


@router.get("/{dataset_id}/regression")
def get_regression(dataset_id: str):
    """Return correlation and regression analysis for a dataset."""
    try:
        df   = get_df(dataset_id)
        info = get_info(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pm25_series = (
        df.dropna(subset=["pm25_mean"])
        .sort_values("date")
        .set_index("date")["pm25_mean"]
        .asfreq("D")   # fill calendar gaps with NaN
    )

    feat_df = _build_feature_df(pm25_series)
    n = len(feat_df)

    if n < _MIN_ROWS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Only {n} complete rows after feature engineering. "
                f"At least {_MIN_ROWS} required. "
                "Ensure the dataset has ≥ 15 non-gap daily observations."
            ),
        )

    y    = feat_df["target"].values
    fnames = list(FEATURES.keys())

    # ── Pearson correlations ──────────────────────────────────────────────────
    correlation: dict[str, dict] = {}
    for fname in fnames:
        r, p = _pearson(feat_df[fname].values, y)
        correlation[fname] = {
            "r":        round(r, 4) if not np.isnan(r) else None,
            "r_squared": round(r**2, 4) if not np.isnan(r) else None,
            "p_value":  round(p, 6) if not np.isnan(p) else None,
            "p_display": _fmt_p(p),
            "significance": _significance_label(p),
            "interpretation": (
                "strong" if abs(r) >= 0.7 else
                "moderate" if abs(r) >= 0.4 else
                "weak"
            ) + (" positive" if r > 0 else " negative") + " correlation"
            if not np.isnan(r) else "N/A",
        }

    # ── Simple linear regression (lag_1 → target) ────────────────────────────
    x_simple = feat_df["lag_1"].values
    lr = stats.linregress(x_simple, y)
    slr_preds = lr.slope * x_simple + lr.intercept
    slr_residuals = y - slr_preds
    slr_r2 = float(lr.rvalue ** 2)

    # Sample 80 scatter points (evenly spaced for chart)
    step = max(1, n // 80)
    scatter_sample = feat_df.iloc[::step].copy()
    scatter_sample["predicted"] = lr.slope * scatter_sample["lag_1"] + lr.intercept
    scatter_data = [
        {
            "x": round(float(row["lag_1"]), 3),
            "y": round(float(row["target"]), 3),
            "predicted": round(float(row["predicted"]), 3),
        }
        for _, row in scatter_sample.iterrows()
    ]

    # Residual plot data (fitted vs residual)
    residual_sample = scatter_sample.copy()
    residual_sample["residual"] = (
        residual_sample["target"]
        - (lr.slope * residual_sample["lag_1"] + lr.intercept)
    )
    residual_data = [
        {
            "fitted": round(float(row["predicted"]), 3),
            "residual": round(float(row["residual"]), 3),
        }
        for _, row in residual_sample.iterrows()
    ]

    simple_regression = {
        "feature":     "lag_1",
        "feature_label": "Previous day PM2.5 (lag 1)",
        "n":           n,
        "slope":       round(float(lr.slope), 6),
        "intercept":   round(float(lr.intercept), 6),
        "r":           round(float(lr.rvalue), 6),
        "r_squared":   round(slr_r2, 6),
        "p_value":     round(float(lr.pvalue), 8),
        "p_display":   _fmt_p(lr.pvalue),
        "std_error":   round(float(lr.stderr), 6),
        "equation":    f"PM2.5 = {lr.slope:.4f} × lag_1 + {lr.intercept:.4f}",
        "scatter_data":  scatter_data,
        "residual_data": residual_data,
        "interpretation": (
            f"The simple linear model explains {slr_r2*100:.1f}% of variance in next-day PM2.5 "
            f"(R² = {slr_r2:.4f}). "
            f"The slope ({lr.slope:.4f}) is {'statistically significant' if lr.pvalue < 0.05 else 'not statistically significant'} "
            f"(p {_fmt_p(lr.pvalue)}), meaning for every 1 µg/m³ increase in today's PM2.5, "
            f"tomorrow's PM2.5 is expected to change by {lr.slope:.2f} µg/m³."
        ),
    }

    # ── Multiple linear regression (lag_1, lag_7, rolling_mean_3 → target) ───
    mlr_features = ["lag_1", "lag_7", "rolling_mean_3"]
    X_mlr = feat_df[mlr_features].values
    y_mlr = feat_df["target"].values

    mlr_model = LinearRegression()
    mlr_model.fit(X_mlr, y_mlr)
    y_mlr_pred = mlr_model.predict(X_mlr)

    mlr_residuals = y_mlr - y_mlr_pred
    ss_res = float(np.sum(mlr_residuals**2))
    ss_tot = float(np.sum((y_mlr - y_mlr.mean())**2))
    mlr_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    k = len(mlr_features)
    mlr_adj_r2 = 1.0 - (1.0 - mlr_r2) * (n - 1) / max(n - k - 1, 1)

    p_values_mlr, mse_mlr = _ols_pvalues(X_mlr, y_mlr, mlr_model.coef_, mlr_model.intercept_)

    coeff_table = [
        {
            "feature":      "Intercept",
            "coefficient":  round(float(mlr_model.intercept_), 6),
            "p_value":      round(float(p_values_mlr[0]), 6),
            "p_display":    _fmt_p(p_values_mlr[0]),
            "significance": _significance_label(p_values_mlr[0]),
        }
    ] + [
        {
            "feature":      f,
            "coefficient":  round(float(mlr_model.coef_[i]), 6),
            "p_value":      round(float(p_values_mlr[i + 1]), 6),
            "p_display":    _fmt_p(p_values_mlr[i + 1]),
            "significance": _significance_label(p_values_mlr[i + 1]),
        }
        for i, f in enumerate(mlr_features)
    ]

    # Actual vs predicted sample (up to 80 points)
    avp_sample_idx = range(0, n, max(1, n // 80))
    actual_vs_predicted = [
        {
            "index": int(i),
            "actual":    round(float(y_mlr[i]), 3),
            "predicted": round(float(y_mlr_pred[i]), 3),
        }
        for i in avp_sample_idx
    ]

    multiple_regression = {
        "features":           mlr_features,
        "n":                  n,
        "r_squared":          round(mlr_r2, 6),
        "adjusted_r_squared": round(mlr_adj_r2, 6),
        "mse":                round(mse_mlr, 4) if not np.isnan(mse_mlr) else None,
        "rmse":               round(float(np.sqrt(mse_mlr)), 4) if not np.isnan(mse_mlr) else None,
        "coefficients":       coeff_table,
        "actual_vs_predicted": actual_vs_predicted,
        "interpretation": (
            f"The multiple regression model with {len(mlr_features)} features explains "
            f"{mlr_r2*100:.1f}% of variance in next-day PM2.5 "
            f"(adjusted R² = {mlr_adj_r2:.4f}). "
            f"RMSE = {np.sqrt(mse_mlr):.2f} µg/m³. "
            + ("Significant predictors (α = 0.05): "
               + ", ".join(
                   c["feature"] for c in coeff_table
                   if c.get("p_value") is not None and c["p_value"] < 0.05
               ) or "None"
               + ".")
        ),
        "significance_note": "*** p < 0.001  ** p < 0.01  * p < 0.05  ns = not significant",
    }

    return {
        "dataset_id":         dataset_id,
        "dataset_name":       info.name,
        "n_samples":          n,
        "features_built":     fnames,
        "target":             "Next-day PM2.5 (lag-free, no look-ahead)",
        "correlation":        correlation,
        "simple_regression":  simple_regression,
        "multiple_regression": multiple_regression,
        "methodology_note": (
            "Features are built using only past observations: lag_1 is yesterday's PM2.5, "
            "lag_7 is 7 days ago, rolling means use windows ending at today. "
            "The target is tomorrow's PM2.5. No data leakage occurs."
        ),
    }
