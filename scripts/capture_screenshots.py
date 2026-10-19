"""Capture UI screenshots (MLflow, Swagger, Prometheus, Grafana) with a headless browser.

Expects the services to be running locally (see the `monitoring` job in ci.yml).
Usage: python scripts/capture_screenshots.py <output_dir>
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import quote

import mlflow
from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
MLFLOW = "http://127.0.0.1:5000/#"


def pages() -> list[tuple[str, str, int]]:
    mlflow.set_tracking_uri("file:./mlruns")
    exp = mlflow.get_experiment_by_name("heart-disease")
    runs = mlflow.search_runs([exp.experiment_id])
    champion = runs.loc[runs["tags.champion"] == "true", "run_id"].iloc[0]
    run_ids = quote(json.dumps(runs["run_id"].tolist()))
    exp_ids = quote(json.dumps([exp.experiment_id]))
    prom_query = quote("sum by (path, status) (api_requests_total)")
    return [
        ("mlflow_01_experiment_runs", f"{MLFLOW}/experiments/{exp.experiment_id}", 8),
        ("mlflow_02_champion_run", f"{MLFLOW}/experiments/{exp.experiment_id}/runs/{champion}", 8),
        (
            "mlflow_03_compare_runs",
            f"{MLFLOW}/compare-runs?runs={run_ids}&experiments={exp_ids}",
            10,
        ),
        ("api_01_swagger_docs", "http://localhost:8000/docs", 4),
        ("monitoring_01_prometheus_targets", "http://localhost:9090/targets", 4),
        (
            "monitoring_02_prometheus_requests",
            f"http://localhost:9090/graph?g0.expr={prom_query}&g0.tab=1",
            5,
        ),
        (
            "monitoring_03_grafana_dashboard",
            "http://localhost:3000/d/heart-api/heart-disease-api?orgId=1&from=now-15m&to=now&kiosk",
            12,
        ),
    ]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, url, settle in pages():
            try:
                page.goto(url, wait_until="load", timeout=60_000)
            except Exception as exc:  # keep going: one slow page must not lose the rest
                print(f"warning: {name}: {exc}")
            time.sleep(settle)
            page.screenshot(path=OUT / f"{name}.png", full_page=True)
            print(f"saved {name}.png")
        browser.close()


if __name__ == "__main__":
    main()
