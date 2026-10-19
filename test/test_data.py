import numpy as np
import pandas as pd
import pytest

from heart.config import FEATURES, RAW_COLUMNS, TARGET
from heart.data import clean, load_raw, validate


def test_load_raw_parses_question_marks_as_nan(tmp_path):
    row = "63.0,1.0,1.0,145.0,233.0,1.0,2.0,150.0,0.0,2.3,3.0,?,6.0,0\n"
    path = tmp_path / "raw.data"
    path.write_text(row * 3)
    df = load_raw(path)
    assert list(df.columns) == RAW_COLUMNS
    assert df["ca"].isna().all()


def test_clean_binarises_target(raw_df):
    out = clean(raw_df)
    assert set(out[TARGET].unique()) <= {0, 1}
    assert "num" not in out.columns
    assert (out[TARGET] == 1).sum() == (raw_df.drop_duplicates()["num"] > 0).sum()


def test_clean_treats_zero_cholesterol_as_missing(raw_df):
    raw_df.loc[0, "chol"] = 0
    assert np.isnan(clean(raw_df).loc[0, "chol"])


def test_clean_drops_duplicates(raw_df):
    doubled = pd.concat([raw_df, raw_df.head(10)])
    assert len(clean(doubled)) == len(clean(raw_df))


def test_clean_keeps_feature_order(raw_df):
    assert list(clean(raw_df).columns) == FEATURES + [TARGET]


def test_validate_rejects_missing_column(clean_df):
    with pytest.raises(ValueError, match="Missing columns"):
        validate(clean_df.drop(columns=["age"]))


def test_validate_rejects_non_binary_target(clean_df):
    clean_df.loc[0, TARGET] = 3
    with pytest.raises(ValueError, match="binary"):
        validate(clean_df)
