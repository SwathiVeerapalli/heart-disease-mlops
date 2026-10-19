import mlflow
import pytest
from fastapi.testclient import TestClient

from heart.train import run_training


@pytest.fixture
def client(clean_df, tmp_path, monkeypatch):
    mlflow.set_tracking_uri(f"file://{tmp_path / 'mlruns'}")
    run_training(
        clean_df, experiment="api-test", cv_folds=3, model_dir=tmp_path / "models", quick=True
    )
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "models" / "model.joblib"))
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_predict_returns_prediction_and_confidence(client, sample_payload):
    r = client.post("/predict", json=sample_payload)
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in (0, 1)
    assert 0.5 <= body["confidence"] <= 1.0
    assert "x-request-id" in r.headers


def test_predict_accepts_missing_optional_fields(client, sample_payload):
    sample_payload.pop("ca")
    sample_payload.pop("thal")
    assert client.post("/predict", json=sample_payload).status_code == 200


def test_predict_rejects_invalid_input(client, sample_payload):
    sample_payload["age"] = -4
    assert client.post("/predict", json=sample_payload).status_code == 422


def test_metrics_exposed(client, sample_payload):
    client.post("/predict", json=sample_payload)
    text = client.get("/metrics").text
    assert "api_requests_total" in text
    assert "model_predictions_total" in text
