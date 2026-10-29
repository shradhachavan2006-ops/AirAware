"""AirAware V2 Dataset Store.

Central registry for all datasets: built-in city demos and user uploads.

Dataset IDs:
  Demo datasets : 'demo:pune'  'demo:mumbai'  'demo:nagpur'  'demo:nashik'
  Uploaded       : UUID4 strings (e.g. 'a3f8e2d1-4c77-...')

Schema (all datasets must conform):
  Required : date        (parseable, YYYY-MM-DD preferred)
             pm25_mean   (numeric, µg/m³)
  Optional : station_count  (numeric)
             coverage_pct   (numeric, 0–100)
             city            (string — kept if present, ignored if absent)

Lifecycle:
  - Demo datasets are loaded lazily from data/demo/{city}.csv.
  - Uploads are validated, normalised, stored in memory, and persisted
    to data/uploads/{uuid}.csv so they survive uvicorn reloads.
  - A companion data/uploads/meta.json tracks upload metadata.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Directories ───────────────────────────────────────────────────────────────
_ROOT = Path(__file__).parent.parent          # project root
_DEMO_DIR   = _ROOT / "data" / "demo"
_UPLOAD_DIR = _ROOT / "data" / "uploads"
_META_FILE  = _UPLOAD_DIR / "meta.json"

_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
DEMO_IDS: dict[str, str] = {
    "demo:pune":    "pune",
    "demo:mumbai":  "mumbai",
    "demo:nagpur":  "nagpur",
    "demo:nashik":  "nashik",
}

REQUIRED_COLUMNS = {"date", "pm25_mean"}
OPTIONAL_COLUMNS = {"station_count", "coverage_pct", "city"}
MIN_ROWS = 10

# Reference thresholds for hypothesis tests
WHO_ANNUAL_GUIDELINE_UG_M3 = 15.0     # WHO 2021 PM2.5 annual
INDIA_NAAQS_ANNUAL_UG_M3   = 40.0     # India NAAQS annual


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class DatasetInfo:
    id: str
    name: str
    city_hint: str          # best-guess city name for display
    is_demo: bool
    rows: int               # valid (non-NaN pm25_mean) rows
    total_rows: int         # rows including missing-pm25 rows
    date_start: str         # YYYY-MM-DD
    date_end: str           # YYYY-MM-DD
    has_station_count: bool
    has_coverage_pct: bool
    uploaded_at: str        # ISO-8601 timestamp
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    cleaned_df: Optional[pd.DataFrame] = None


# ── In-process stores ─────────────────────────────────────────────────────────

_df_store:   dict[str, pd.DataFrame] = {}
_info_store: dict[str, DatasetInfo]  = {}
_lock = threading.Lock()


# ── Validation & normalisation ────────────────────────────────────────────────

def _validate_and_clean(df: pd.DataFrame, name: str) -> ValidationResult:
    """Validate uploaded DataFrame. Returns errors (blocking) and warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    # Normalise column names
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        errors.append(
            f"Missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected: date, pm25_mean."
        )
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    # Parse dates
    try:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    except Exception as exc:
        errors.append(f"Cannot parse 'date' column: {exc}")
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    unparsed = df["date"].isna().sum()
    if unparsed > 0:
        pct = unparsed / len(df) * 100
        if pct > 50:
            errors.append(
                f"{unparsed} of {len(df)} rows have unparseable dates ({pct:.0f}%). "
                "Check date format (expected YYYY-MM-DD)."
            )
            return ValidationResult(ok=False, errors=errors, warnings=warnings)
        warnings.append(f"{unparsed} rows with unparseable dates were dropped.")
    df = df.dropna(subset=["date"])

    # Parse pm25_mean
    df["pm25_mean"] = pd.to_numeric(df["pm25_mean"], errors="coerce")
    null_pm25 = df["pm25_mean"].isna().sum()
    if null_pm25 > 0:
        pct = null_pm25 / len(df) * 100
        if pct > 80:
            errors.append(
                f"{null_pm25} of {len(df)} pm25_mean values are non-numeric ({pct:.0f}%). "
                "Is the pm25_mean column numeric (µg/m³)?"
            )
            return ValidationResult(ok=False, errors=errors, warnings=warnings)
        if pct > 50:
            warnings.append(f"{pct:.0f}% of pm25_mean values are missing.")

    # Drop rows where pm25_mean is NaN
    df_clean = df.dropna(subset=["pm25_mean"]).copy()

    if len(df_clean) < MIN_ROWS:
        errors.append(
            f"Only {len(df_clean)} valid rows remain after cleaning. "
            f"At least {MIN_ROWS} required for analysis."
        )
        return ValidationResult(ok=False, errors=errors, warnings=warnings)

    # Negative values
    neg = (df_clean["pm25_mean"] < 0).sum()
    if neg > 0:
        warnings.append(
            f"{neg} negative pm25_mean value(s) found. "
            "Negative PM2.5 is physically implausible; treat with caution."
        )

    # Implausibly high values
    extreme = (df_clean["pm25_mean"] > 500).sum()
    if extreme > 0:
        warnings.append(
            f"{extreme} pm25_mean value(s) exceed 500 µg/m³ — "
            "possible sensor error or data quality issue."
        )

    # Duplicate dates
    dupes = df_clean["date"].duplicated().sum()
    if dupes > 0:
        warnings.append(
            f"{dupes} duplicate date(s) found; later entries are kept."
        )
        df_clean = df_clean.sort_values("date").drop_duplicates("date", keep="last")

    # Small dataset warning
    if len(df_clean) < 30:
        warnings.append(
            f"Only {len(df_clean)} observations. "
            "Statistical results may have low reliability."
        )

    # Sort by date
    df_clean = df_clean.sort_values("date").reset_index(drop=True)

    # Parse optional numeric columns
    for col in ("station_count", "coverage_pct"):
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    return ValidationResult(
        ok=True,
        errors=errors,
        warnings=warnings,
        cleaned_df=df_clean,
    )


def _make_info(
    dataset_id: str,
    name: str,
    city_hint: str,
    is_demo: bool,
    df: pd.DataFrame,
    warnings: list[str],
) -> DatasetInfo:
    return DatasetInfo(
        id=dataset_id,
        name=name,
        city_hint=city_hint,
        is_demo=is_demo,
        rows=len(df.dropna(subset=["pm25_mean"])),
        total_rows=len(df),
        date_start=str(df["date"].min().date()),
        date_end=str(df["date"].max().date()),
        has_station_count=bool("station_count" in df.columns and df["station_count"].notna().any()),
        has_coverage_pct=bool("coverage_pct" in df.columns and df["coverage_pct"].notna().any()),
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        warnings=warnings,
    )


# ── Demo dataset loading ──────────────────────────────────────────────────────

def _load_demo(city_key: str) -> None:
    """Lazily load a demo dataset into the store."""
    city_name = DEMO_IDS[city_key]
    csv_path = _DEMO_DIR / f"{city_name}.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Demo dataset file not found: {csv_path}. "
            "Run the demo CSV creation script."
        )

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pm25_mean"] = pd.to_numeric(df["pm25_mean"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    display_name = city_name.capitalize()
    info = _make_info(
        dataset_id=city_key,
        name=f"{display_name} (Demo)",
        city_hint=display_name,
        is_demo=True,
        df=df,
        warnings=[],
    )

    with _lock:
        _df_store[city_key] = df
        _info_store[city_key] = info


# ── Upload persistence ────────────────────────────────────────────────────────

def _save_upload_meta() -> None:
    meta = {
        did: asdict(info)
        for did, info in _info_store.items()
        if not info.is_demo
    }
    _META_FILE.write_text(json.dumps(meta, indent=2, default=str))


def _load_persisted_uploads() -> None:
    """Called once at startup to reload saved uploads."""
    if not _META_FILE.exists():
        return
    try:
        meta = json.loads(_META_FILE.read_text())
    except json.JSONDecodeError:
        return

    for did, info_dict in meta.items():
        csv_path = _UPLOAD_DIR / f"{did}.csv"
        if not csv_path.exists():
            continue
        try:
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["pm25_mean"] = pd.to_numeric(df["pm25_mean"], errors="coerce")
            df = df.sort_values("date").reset_index(drop=True)
            info = DatasetInfo(**{k: info_dict.get(k, v)
                                  for k, v in DatasetInfo.__dataclass_fields__.items()
                                  if hasattr(DatasetInfo, '__dataclass_fields__')})
            # Rebuild safely
            info = DatasetInfo(
                id=info_dict["id"],
                name=info_dict["name"],
                city_hint=info_dict.get("city_hint", "Custom"),
                is_demo=False,
                rows=info_dict.get("rows", len(df)),
                total_rows=info_dict.get("total_rows", len(df)),
                date_start=info_dict.get("date_start", ""),
                date_end=info_dict.get("date_end", ""),
                has_station_count=info_dict.get("has_station_count", False),
                has_coverage_pct=info_dict.get("has_coverage_pct", False),
                uploaded_at=info_dict.get("uploaded_at", ""),
                warnings=info_dict.get("warnings", []),
            )
            with _lock:
                _df_store[did] = df
                _info_store[did] = info
        except Exception:
            pass  # Skip corrupt uploads silently


# ── Public API ────────────────────────────────────────────────────────────────

def get_df(dataset_id: str) -> pd.DataFrame:
    """Return the DataFrame for a dataset_id. Raises KeyError if not found."""
    with _lock:
        if dataset_id in _df_store:
            return _df_store[dataset_id].copy()

    # Try lazy-loading a demo dataset
    if dataset_id in DEMO_IDS:
        _load_demo(dataset_id)
        with _lock:
            return _df_store[dataset_id].copy()

    raise KeyError(f"Dataset '{dataset_id}' not found. Upload it or choose a demo.")


def get_info(dataset_id: str) -> DatasetInfo:
    """Return metadata for a dataset_id."""
    get_df(dataset_id)   # ensures lazy load
    with _lock:
        return _info_store[dataset_id]


def list_datasets() -> list[DatasetInfo]:
    """Return metadata for all known datasets (demos first, then uploads)."""
    demos = []
    for did in DEMO_IDS:
        try:
            demos.append(get_info(did))
        except FileNotFoundError:
            pass

    with _lock:
        uploads = [
            info for info in _info_store.values()
            if not info.is_demo
        ]

    return demos + sorted(uploads, key=lambda i: i.uploaded_at, reverse=True)


def register_upload(
    raw_df: pd.DataFrame,
    name: str,
) -> tuple[DatasetInfo, list[str]]:
    """Validate, clean and register a user-uploaded DataFrame.

    Returns (DatasetInfo, warnings_list).
    Raises ValueError with a human-readable message on validation failure.
    """
    result = _validate_and_clean(raw_df, name)
    if not result.ok:
        raise ValueError("; ".join(result.errors))

    df = result.cleaned_df
    dataset_id = str(uuid.uuid4())

    # Guess city from data
    city_hint = "Custom"
    if "city" in df.columns and df["city"].notna().any():
        city_hint = str(df["city"].dropna().iloc[0]).strip().capitalize()

    info = _make_info(
        dataset_id=dataset_id,
        name=name.strip() or f"Upload {dataset_id[:8]}",
        city_hint=city_hint,
        is_demo=False,
        df=df,
        warnings=result.warnings,
    )

    # Persist to disk
    csv_path = _UPLOAD_DIR / f"{dataset_id}.csv"
    df.to_csv(csv_path, index=False)

    with _lock:
        _df_store[dataset_id] = df
        _info_store[dataset_id] = info

    _save_upload_meta()
    return info, result.warnings


def delete_upload(dataset_id: str) -> bool:
    """Delete an uploaded dataset. Returns True if deleted, False if not found or is a demo."""
    with _lock:
        if dataset_id not in _info_store:
            return False
        if _info_store[dataset_id].is_demo:
            return False
        del _df_store[dataset_id]
        del _info_store[dataset_id]

    csv_path = _UPLOAD_DIR / f"{dataset_id}.csv"
    if csv_path.exists():
        csv_path.unlink()

    _save_upload_meta()
    return True


def get_pm25_series(dataset_id: str) -> pd.Series:
    """Return the pm25_mean Series (non-NaN, sorted by date) for a dataset."""
    df = get_df(dataset_id)
    return df.dropna(subset=["pm25_mean"]).sort_values("date")["pm25_mean"].reset_index(drop=True)


# Bootstrap: load persisted uploads at module import time
_load_persisted_uploads()
