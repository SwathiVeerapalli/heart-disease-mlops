"""FastAPI model-serving app: /predict, /health, /metrics (Prometheus)."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field

FEATURES = [
    "age", "trestbps", "chol", "thalach", "oldpeak", "ca",
    "sex", "cp", "fbs", "restecg", "exang", "slope", "thal",
]  # fmt: skip


# ---------- structured JSON logging ----------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "extra_fields", {}))
        return json.dumps(payload)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("heart-api")
logger.handlers = [handler]
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
logger.propagate = False


# ---------- Prometheus metrics ----------
REQUESTS = Counter("api_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("api_request_latency_seconds", "Request latency", ["path"])
PREDICTIONS = Counter("model_predictions_total", "Predictions by class", ["label"])
CONFIDENCE = Histogram(
    "model_prediction_confidence", "Confidence of returned predictions",
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
)  # fmt: skip
MODEL_LOADED = Gauge("model_loaded", "1 if the model is loaded")


# ---------- schemas ----------
class PatientFeatures(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "age": 58,
                "sex": 1,
                "cp": 4,
                "trestbps": 140,
                "chol": 289,
                "fbs": 0,
                "restecg": 2,
                "thalach": 120,
                "exang": 1,
                "oldpeak": 2.6,
                "slope": 2,
                "ca": 2,
                "thal": 7,
            }  # fmt: skip
        }
    )

    age: float = Field(..., ge=1, le=120, description="Age in years")
    sex: Literal[0, 1] = Field(..., description="1 = male, 0 = female")
    cp: Literal[1, 2, 3, 4] = Field(..., description="Chest pain type")
    trestbps: float = Field(..., gt=0, le=300, description="Resting blood pressure (mm Hg)")
    chol: float = Field(..., gt=0, le=700, description="Serum cholesterol (mg/dl)")
    fbs: Literal[0, 1] = Field(..., description="Fasting blood sugar > 120 mg/dl")
    restecg: Literal[0, 1, 2] = Field(..., description="Resting ECG result")
    thalach: float = Field(..., gt=0, le=250, description="Max heart rate achieved")
    exang: Literal[0, 1] = Field(..., description="Exercise-induced angina")
    oldpeak: float = Field(..., ge=-5, le=10, description="ST depression")
    slope: Literal[1, 2, 3] = Field(..., description="Slope of peak exercise ST segment")
    ca: Optional[float] = Field(None, ge=0, le=4, description="Major vessels coloured (0-3)")
    thal: Optional[Literal[3, 6, 7]] = Field(None, description="3 normal, 6 fixed, 7 reversible")


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int
    label: str
    confidence: float
    probability_disease: float
    model_version: str
    request_id: str


# ---------- app ----------
state: dict = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    model_path = Path(os.getenv("MODEL_PATH", "models/model.joblib"))
    state["model"] = joblib.load(model_path)
    meta_path = model_path.with_name("metadata.json")
    state["meta"] = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    MODEL_LOADED.set(1)
    logger.info("model loaded", extra={"extra_fields": {"path": str(model_path)}})
    yield
    MODEL_LOADED.set(0)


app = FastAPI(title="Heart Disease Risk API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(path).observe(elapsed)
    if path != "/metrics":
        logger.info(
            "request",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "latency_ms": round(elapsed * 1000, 2),
                    "client": request.client.host if request.client else None,
                }
            },
        )
    response.headers["x-request-id"] = request_id
    return response


@app.get("/health")
def health():
    if "model" not in state:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ok", "model": state["meta"].get("model_name", "unknown")}


@app.get("/model-info")
def model_info():
    return state.get("meta", {})


@app.post("/predict", response_model=PredictionResponse)
def predict(features: PatientFeatures, request: Request):
    X = pd.DataFrame([features.model_dump()]).reindex(columns=FEATURES).astype(float)
    p_disease = float(state["model"].predict_proba(X)[0, 1])
    prediction = int(p_disease >= 0.5)
    confidence = p_disease if prediction else 1 - p_disease
    label = "disease" if prediction else "no_disease"
    PREDICTIONS.labels(label).inc()
    CONFIDENCE.observe(confidence)
    logger.info(
        "prediction",
        extra={
            "extra_fields": {
                "request_id": request.state.request_id,
                "prediction": prediction,
                "confidence": round(confidence, 4),
            }
        },
    )
    return PredictionResponse(
        prediction=prediction,
        label=label,
        confidence=round(confidence, 4),
        probability_disease=round(p_disease, 4),
        model_version=state["meta"].get("version", "unknown"),
        request_id=request.state.request_id,
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
