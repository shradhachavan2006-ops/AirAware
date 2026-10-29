"""Statistical analysis endpoints — inferential statistics for a dataset.

GET /analysis/{dataset_id}/statistics
    Comprehensive statistical analysis:
    - Enhanced descriptive statistics (skewness, kurtosis, CV, SEM)
    - Shapiro-Wilk normality test
    - One-sample t-tests vs WHO and India NAAQS PM2.5 guidelines
    - 95% confidence interval for the population mean
    - Seasonal (quarterly) one-way ANOVA + Kruskal-Wallis
    - Histogram bin counts for distribution visualisation

All p-values are two-tailed. Effect sizes use Cohen's d for t-tests.
Statistical conclusions are stated in plain language alongside the numbers.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.stats as stats
from fastapi import APIRouter, HTTPException

from backend.dataset_store import (
    WHO_ANNUAL_GUIDELINE_UG_M3,
    INDIA_NAAQS_ANNUAL_UG_M3,
    get_df,
    get_info,
)

router = APIRouter(prefix="/analysis", tags=["Statistical Analysis"])

_MIN_SHAPIRO = 3     # minimum n for Shapiro-Wilk
_MAX_SHAPIRO = 5000  # Shapiro-Wilk loses power above ~5000


def _fmt_p(p: float) -> str:
    if p < 0.0001:
        return "< 0.0001"
    return f"{p:.4f}"


def _effect_size_d(sample: np.ndarray, mu0: float) -> float:
    """Cohen's d for a one-sample t-test."""
    if sample.std(ddof=1) == 0:
        return float("nan")
    return (sample.mean() - mu0) / sample.std(ddof=1)


def _interpret_d(d: float) -> str:
    ad = abs(d)
    if ad < 0.2:  return "negligible"
    if ad < 0.5:  return "small"
    if ad < 0.8:  return "medium"
    return "large"


def _interpret_p(p: float, alpha: float = 0.05) -> str:
    return "significant" if p < alpha else "not significant"


@router.get("/{dataset_id}/statistics")
def get_statistics(dataset_id: str):
    """Return inferential and descriptive statistics for a dataset."""
    try:
        df   = get_df(dataset_id)
        info = get_info(dataset_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pm25 = df.dropna(subset=["pm25_mean"])["pm25_mean"].values.astype(float)
    n = len(pm25)

    if n < 3:
        raise HTTPException(
            status_code=422,
            detail=f"Only {n} valid PM2.5 values. At least 3 required for analysis.",
        )

    # ── Descriptive statistics ────────────────────────────────────────────────
    mean   = float(np.mean(pm25))
    median = float(np.median(pm25))
    std    = float(np.std(pm25, ddof=1))
    sem    = float(stats.sem(pm25))
    q1     = float(np.percentile(pm25, 25))
    q3     = float(np.percentile(pm25, 75))
    iqr    = q3 - q1
    skew   = float(stats.skew(pm25))
    kurt   = float(stats.kurtosis(pm25, fisher=True))  # excess kurtosis
    cv     = (std / mean * 100) if mean != 0 else float("nan")

    descriptive = {
        "n":      n,
        "mean":   round(mean, 4),
        "median": round(median, 4),
        "std":    round(std, 4),
        "sem":    round(sem, 4),
        "min":    round(float(pm25.min()), 4),
        "max":    round(float(pm25.max()), 4),
        "q1":     round(q1, 4),
        "q3":     round(q3, 4),
        "iqr":    round(iqr, 4),
        "skewness": round(skew, 4),
        "kurtosis_excess": round(kurt, 4),
        "cv_pct":  round(cv, 2),
        "interpretation": (
            f"The distribution is {'right' if skew > 0.5 else 'left' if skew < -0.5 else 'approximately symmetrically'} "
            f"skewed (skewness = {skew:.2f}). "
            f"{'Positive kurtosis indicates heavier tails than a normal distribution.' if kurt > 0 else 'Negative kurtosis indicates lighter tails than a normal distribution.'}"
        ),
    }

    # ── Normality test (Shapiro-Wilk) ─────────────────────────────────────────
    sw_sample = pm25[:_MAX_SHAPIRO] if n > _MAX_SHAPIRO else pm25
    if len(sw_sample) >= _MIN_SHAPIRO:
        sw_stat, sw_p = stats.shapiro(sw_sample)
        is_normal = bool(sw_p >= 0.05)
        normality = {
            "test":       "Shapiro-Wilk",
            "n_tested":   len(sw_sample),
            "statistic":  round(float(sw_stat), 6),
            "p_value":    round(float(sw_p), 6),
            "p_display":  _fmt_p(sw_p),
            "is_normal":  is_normal,
            "conclusion": (
                f"W = {sw_stat:.4f}, p {_fmt_p(sw_p)}. "
                f"{'Fail to reject' if is_normal else 'Reject'} H₀ (normality) at α = 0.05. "
                f"The data {'appears consistent with' if is_normal else 'is not'} a normal distribution. "
                + ("Note: Shapiro-Wilk has reduced power with very large samples (n > 5000). "
                   f"The test used a random sample of {len(sw_sample)} observations."
                   if n > _MAX_SHAPIRO else "")
            ),
        }
    else:
        normality = {
            "test": "Shapiro-Wilk",
            "n_tested": n,
            "statistic": None,
            "p_value": None,
            "p_display": "N/A",
            "is_normal": None,
            "conclusion": f"Insufficient data for normality test (n = {n}, minimum = {_MIN_SHAPIRO}).",
        }

    # ── One-sample t-tests ────────────────────────────────────────────────────
    def _one_sample_ttest(mu0: float, label: str) -> dict:
        t, p = stats.ttest_1samp(pm25, popmean=mu0)
        d    = _effect_size_d(pm25, mu0)
        ci_lo, ci_hi = stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem)
        reject = bool(p < 0.05)
        direction = "exceeds" if mean > mu0 else "falls below"
        return {
            "null_hypothesis":    f"μ = {mu0} µg/m³ ({label})",
            "t_statistic":        round(float(t), 4),
            "p_value":            round(float(p), 6),
            "p_display":          _fmt_p(p),
            "degrees_of_freedom": n - 1,
            "reject_null":        reject,
            "cohens_d":           round(d, 4) if not np.isnan(d) else None,
            "effect_size_label":  _interpret_d(d),
            "conclusion": (
                f"t({n-1}) = {t:.2f}, p {_fmt_p(p)}. "
                f"{'Reject' if reject else 'Fail to reject'} H₀ at α = 0.05. "
                f"The mean PM2.5 ({mean:.1f} µg/m³) statistically {direction} the guideline "
                f"of {mu0} µg/m³ "
                f"({'with' if reject else 'without'} statistical significance, "
                f"effect size: {_interpret_d(d)})."
            ),
        }

    ttest_who    = _one_sample_ttest(WHO_ANNUAL_GUIDELINE_UG_M3,  "WHO 2021 annual PM2.5 guideline")
    ttest_naaqs  = _one_sample_ttest(INDIA_NAAQS_ANNUAL_UG_M3,    "India NAAQS annual standard")

    # ── 95% Confidence interval for the mean ─────────────────────────────────
    ci_lo, ci_hi = stats.t.interval(0.95, df=n - 1, loc=mean, scale=sem)
    confidence_interval = {
        "level": 0.95,
        "lower": round(float(ci_lo), 4),
        "upper": round(float(ci_hi), 4),
        "interpretation": (
            f"We are 95% confident that the true population mean PM2.5 lies between "
            f"{ci_lo:.1f} and {ci_hi:.1f} µg/m³. "
            f"This interval {'does not include' if ci_lo > WHO_ANNUAL_GUIDELINE_UG_M3 else 'includes'} "
            f"the WHO guideline of {WHO_ANNUAL_GUIDELINE_UG_M3} µg/m³."
        ),
    }

    # ── Seasonal ANOVA (quarterly) ────────────────────────────────────────────
    df_pm = df.dropna(subset=["pm25_mean"]).copy()
    df_pm["quarter"] = pd.to_datetime(df_pm["date"]).dt.quarter
    q_groups = {
        q: df_pm[df_pm["quarter"] == q]["pm25_mean"].values
        for q in [1, 2, 3, 4]
    }
    q_labels = {1: "Q1 (Jan–Mar)", 2: "Q2 (Apr–Jun)",
                 3: "Q3 (Jul–Sep)", 4: "Q4 (Oct–Dec)"}
    valid_groups = {k: v for k, v in q_groups.items() if len(v) >= 2}

    if len(valid_groups) >= 2:
        group_arrays = list(valid_groups.values())
        f_stat, anova_p = stats.f_oneway(*group_arrays)
        kw_stat, kw_p   = stats.kruskal(*group_arrays)

        group_stats = {}
        for q, vals in q_groups.items():
            if len(vals) >= 1:
                group_stats[q_labels[q]] = {
                    "n":    len(vals),
                    "mean": round(float(vals.mean()), 2),
                    "std":  round(float(vals.std(ddof=1)), 2) if len(vals) > 1 else 0.0,
                }

        anova_reject = bool(anova_p < 0.05)
        seasonal_anova = {
            "test":       "One-way ANOVA",
            "f_statistic": round(float(f_stat), 4),
            "p_value":     round(float(anova_p), 6),
            "p_display":   _fmt_p(anova_p),
            "reject_null": anova_reject,
            "group_stats": group_stats,
            "kruskal_wallis": {
                "statistic": round(float(kw_stat), 4),
                "p_value":   round(float(kw_p), 6),
                "p_display": _fmt_p(kw_p),
                "reject_null": bool(kw_p < 0.05),
            },
            "conclusion": (
                f"F = {f_stat:.2f}, p {_fmt_p(anova_p)}. "
                f"{'Reject' if anova_reject else 'Fail to reject'} H₀ (equal quarterly means) "
                f"at α = 0.05. "
                + ("There are statistically significant seasonal differences in PM2.5 across quarters. "
                   if anova_reject else
                   "No statistically significant seasonal differences detected. ")
                + "Non-parametric Kruskal-Wallis confirms: "
                f"H = {kw_stat:.2f}, p {_fmt_p(kw_p)}."
            ),
        }
    else:
        seasonal_anova = {
            "test": "One-way ANOVA",
            "conclusion": (
                f"Insufficient data for seasonal ANOVA. "
                f"Only {len(valid_groups)} quarter(s) with ≥ 2 observations."
            ),
            "group_stats": {},
            "f_statistic": None,
            "p_value": None,
        }

    # ── Histogram data ────────────────────────────────────────────────────────
    counts, bin_edges = np.histogram(pm25, bins=min(30, max(10, n // 10)))
    histogram = {
        "bins":   [round(float(e), 2) for e in bin_edges],
        "counts": [int(c) for c in counts],
        "bin_width": round(float(bin_edges[1] - bin_edges[0]), 2),
    }

    return {
        "dataset_id":        dataset_id,
        "dataset_name":      info.name,
        "descriptive":       descriptive,
        "normality":         normality,
        "ttest_who_annual":  ttest_who,
        "ttest_india_naaqs": ttest_naaqs,
        "confidence_interval_95": confidence_interval,
        "seasonal_anova":    seasonal_anova,
        "histogram":         histogram,
        "reference_values": {
            "who_annual_guideline_ug_m3":  WHO_ANNUAL_GUIDELINE_UG_M3,
            "india_naaqs_annual_ug_m3":    INDIA_NAAQS_ANNUAL_UG_M3,
            "note": (
                "WHO 2021 PM2.5 guideline: 15 µg/m³ (24-hour), 5 µg/m³ (annual). "
                "India NAAQS: 60 µg/m³ (24-hour), 40 µg/m³ (annual). "
                "This analysis compares against annual standards."
            ),
        },
    }
