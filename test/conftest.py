"""Shared fixtures. Tests use synthetic data in the UCI schema so CI never
depends on network access for the unit-test stage."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from heart.config import RAW_COLUMNS


def make_raw_df(n: int = 240, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(29, 78, n),
            "sex": rng.integers(0, 2, n),
            "cp": rng.integers(1, 5, n),
            "trestbps": rng.integers(94, 200, n),
            "chol": rng.integers(126, 564, n),
            "fbs": rng.integers(0, 2, n),
            "restecg": rng.integers(0, 3, n),
            "thalach": rng.integers(71, 202, n),
            "exang": rng.integers(0, 2, n),
            "oldpeak": rng.uniform(0, 6.2, n).round(1),
            "slope": rng.integers(1, 4, n),
            "ca": rng.integers(0, 4, n).astype(float),
            "thal": rng.choice([3.0, 6.0, 7.0], n),
        }
    ).astype(float)
    risk = (
        0.04 * (df.age - 54) + 0.9 * df.exang + 0.7 * (df.cp == 4)
        + 0.4 * df.oldpeak - 0.02 * (df.thalach - 150) + 0.6 * df.ca
    )  # fmt: skip
    df["num"] = np.where(risk + rng.normal(0, 0.8, n) > np.median(risk), rng.integers(1, 5, n), 0)
    df.loc[rng.choice(n, 4, replace=False), "ca"] = np.nan
    df.loc[rng.choice(n, 2, replace=False), "thal"] = np.nan
    return df[RAW_COLUMNS]


@pytest.fixture
def raw_df() -> pd.DataFrame:
    return make_raw_df()


@pytest.fixture
def clean_df(raw_df) -> pd.DataFrame:
    from heart.data import clean

    return clean(raw_df)


@pytest.fixture
def sample_payload() -> dict:
    return {
        "age": 58, "sex": 1, "cp": 4, "trestbps": 140, "chol": 289, "fbs": 0,
        "restecg": 2, "thalach": 120, "exang": 1, "oldpeak": 2.6, "slope": 2,
        "ca": 2, "thal": 7,
    }  # fmt: skip
