"""Offline inference with the exported pipeline.

Usage: python -m heart.predict sample_request.json
"""

from __future__ import annotations

import argparse
import json

import joblib
import pandas as pd

from heart.config import FEATURES, MODEL_PATH


def predict(records: list[dict], model_path=MODEL_PATH) -> list[dict]:
    model = joblib.load(model_path)
    X = pd.DataFrame(records).reindex(columns=FEATURES)
    proba = model.predict_proba(X)[:, 1]
    return [{"prediction": int(p >= 0.5), "probability_disease": round(float(p), 4)} for p in proba]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file with one record or a list of records")
    args = parser.parse_args()
    payload = json.loads(open(args.input).read())
    records = payload if isinstance(payload, list) else [payload]
    print(json.dumps(predict(records), indent=2))


if __name__ == "__main__":
    main()
