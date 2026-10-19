import numpy as np

from heart.config import FEATURES
from heart.features import build_preprocessor


def test_preprocessor_imputes_all_missing_values(clean_df):
    X = clean_df[FEATURES]
    assert X.isna().any().any()  # fixture includes NaNs
    Xt = build_preprocessor().fit_transform(X)
    assert not np.isnan(Xt).any()


def test_numeric_features_are_scaled(clean_df):
    prep = build_preprocessor().fit(clean_df[FEATURES])
    Xt = prep.transform(clean_df[FEATURES])
    n_numeric = 6
    assert np.allclose(Xt[:, :n_numeric].mean(axis=0), 0, atol=1e-6)


def test_unseen_category_does_not_crash(clean_df):
    prep = build_preprocessor().fit(clean_df[FEATURES])
    row = clean_df[FEATURES].head(1).copy()
    row["cp"] = 99
    assert prep.transform(row).shape[0] == 1
