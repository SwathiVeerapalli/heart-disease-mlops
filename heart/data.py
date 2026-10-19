"""Loading, cleaning and validating the UCI Cleveland heart disease data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from heart.config import FEATURES, RAW_COLUMNS, TARGET

# Physiologically impossible values that appear as 0 in some UCI subsets.
ZERO_MEANS_MISSING = ["trestbps", "chol"]


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read the headerless UCI file; '?' marks a missing value."""
    return pd.read_csv(path, header=None, names=RAW_COLUMNS, na_values="?")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned frame with a binary target.

    Missing values are deliberately left as NaN: imputation happens inside the
    sklearn pipeline so that training and serving apply exactly the same logic.
    """
    out = df.copy()
    out = out.apply(pd.to_numeric, errors="coerce")
    for col in ZERO_MEANS_MISSING:
        out.loc[out[col] == 0, col] = np.nan
    out[TARGET] = (out["num"] > 0).astype(int)  # 0 = no disease, 1-4 = disease
    out = out.drop(columns=["num"]).drop_duplicates().reset_index(drop=True)
    return out[FEATURES + [TARGET]]


def validate(df: pd.DataFrame) -> None:
    """Fail fast on schema problems before anything is trained."""
    missing = set(FEATURES + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if not set(df[TARGET].unique()) <= {0, 1}:
        raise ValueError("Target must be binary (0/1)")
    if len(df) < 50:
        raise ValueError(f"Too few rows to train on: {len(df)}")
