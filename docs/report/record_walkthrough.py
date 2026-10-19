"""Record a walkthrough video of the repository, the latest pipeline run and its evidence.

Usage: python docs/report/record_walkthrough.py <pipeline_run_url> <output.webm>
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = "https://github.com/SwathiVeerapalli/heart-disease-mlops"
BLOB = f"{REPO}/blob/main"


def pages(run_url: str) -> list[tuple[str, int]]:
    """(url, number of scroll steps) in the order a reviewer would walk through them."""
    return [
        (REPO, 6),
        (f"{BLOB}/.github/workflows/ci.yml", 8),
        (f"{REPO}/actions", 0),
        (run_url, 3),
        (f"{BLOB}/data/processed/heart_clean.csv", 1),
        (f"{BLOB}/reports/figures/01_class_balance.png", 0),
        (f"{BLOB}/reports/figures/03_correlation_heatmap.png", 2),
        (f"{BLOB}/screenshots/ci_02_unit_tests.png", 2),
        (f"{BLOB}/screenshots/ci_03_data_and_training.png", 1),
        (f"{BLOB}/screenshots/mlflow_01_experiment_runs.png", 0),
        (f"{BLOB}/screenshots/mlflow_03_compare_runs.png", 3),
        (f"{BLOB}/screenshots/docker_01_build_run_predict.png", 1),
        (f"{BLOB}/screenshots/k8s_01_resources.png", 0),
        (f"{BLOB}/screenshots/k8s_02_ingress_predict.png", 0),
        (f"{BLOB}/screenshots/monitoring_01_prometheus_targets.png", 0),
        (f"{BLOB}/screenshots/monitoring_03_grafana_dashboard.png", 2),
        (f"{REPO}/pkgs/container/heart-disease-mlops%2Fheart-api", 1),
    ]


def main() -> None:
    run_url, out = sys.argv[1], Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        browser = p.chromium.launch()
        size = {"width": 1440, "height": 900}
        context = browser.new_context(
            viewport=size, record_video_dir=str(tmp), record_video_size=size
        )
        page = context.new_page()
        for url, scrolls in pages(run_url):
            try:
                page.goto(url, wait_until="load", timeout=60_000)
            except Exception as exc:  # a slow page should not abort the whole recording
                print(f"warning: {url}: {exc}")
            page.wait_for_timeout(3000)
            for _ in range(scrolls):
                page.mouse.wheel(0, 420)
                page.wait_for_timeout(1300)
            page.wait_for_timeout(1500)
            print(f"recorded {url}")
        video = page.video.path()
        context.close()
        browser.close()
    shutil.move(video, out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
