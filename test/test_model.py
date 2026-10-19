import json

import joblib
import mlflow
import pytest

from heart.config import FEATURES
from heart.train import candidates, run_training


@pytest.fixture
def trained(clean_df, tmp_path):
    mlflow.set_tracking_uri(f"file://{tmp_path / 'mlruns'}")
    meta = run_training(
        clean_df, experiment="pytest", cv_folds=3, model_dir=tmp_path / "models", quick=True
    )
    return meta, tmp_path / "models"


def test_at_least_two_candidate_models():
    assert len(candidates(seed=1)) >= 2


def test_training_exports_model_and_metadata(trained):
    meta, model_dir = trained
    assert (model_dir / "model.joblib").exists()
    saved = json.loads((model_dir / "metadata.json").read_text())
    assert saved["model_name"] in {"logistic_regression", "random_forest"}
    for key in ["cv_accuracy_mean", "cv_precision_mean", "cv_recall_mean", "cv_roc_auc_mean"]:
        assert 0.0 <= saved["metrics"][key] <= 1.0


def test_exported_pipeline_predicts_probabilities(trained, clean_df):
    _, model_dir = trained
    model = joblib.load(model_dir / "model.joblib")
    proba = model.predict_proba(clean_df[FEATURES].head(20))
    assert proba.shape == (20, 2)
    assert ((proba >= 0) & (proba <= 1)).all()


def test_model_learns_signal(trained):
    meta, _ = trained
    assert meta["metrics"]["cv_roc_auc_mean"] > 0.6


def test_runs_are_logged_to_mlflow(trained):
    runs = mlflow.search_runs(experiment_names=["pytest"])
    assert len(runs) >= 2
    assert (runs["tags.champion"] == "true").sum() == 1
