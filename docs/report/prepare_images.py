"""Prepare figures for the written report: architecture diagram + evidence images.

Reads screenshots/ and reports/ (committed by the ml-pipeline workflow) and writes
docs/report/build/ plus an index (imgs.json) used by build_report.js.
Usage: python docs/report/prepare_images.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "build"

SOURCES = {
    "f1": "reports/figures/01_class_balance.png",
    "f2": "reports/figures/02_numeric_histograms.png",
    "f3": "reports/figures/03_correlation_heatmap.png",
    "f4": "reports/figures/04_categorical_disease_rate.png",
    "roc": "reports/model_plots/logistic_regression_roc.png",
    "cm": "reports/model_plots/logistic_regression_confusion_matrix.png",
    "ml3": "screenshots/mlflow_03_compare_runs.png",
    "ci0": "screenshots/ci_00_github_actions_run.jpg",
    "ci2": "screenshots/ci_02_unit_tests.png",
    "ci3": "screenshots/ci_03_data_and_training.png",
    "d1": "screenshots/docker_01_build_run_predict.png",
    "k1": "screenshots/k8s_01_resources.png",
    "k2": "screenshots/k8s_02_ingress_predict.png",
    "k3": "screenshots/k8s_03_pod_logs.png",
    "g": "screenshots/monitoring_03_grafana_dashboard.png",
}
CROP_HEIGHT = {"ml3": 1150}  # keep the comparison table, drop the long plot area


def architecture(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.4))
    ax.set_xlim(0, 130)
    ax.set_ylim(-3, 72)
    ax.axis("off")

    def box(x, y, w, h, title, sub, fc):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5", fc=fc, ec="#2b2f36"
            )
        )
        ty = y + h * (0.64 if sub else 0.5)
        ax.text(x + w / 2, ty, title, ha="center", va="center", fontsize=10.5, weight="bold")
        if sub:
            ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=8.2)

    def arrow(x1, y1, x2, y2, label=None, dash=False, rad=0, ly=1.4):
        ax.add_patch(
            FancyArrowPatch(
                (x1, y1),
                (x2, y2),
                arrowstyle="-|>",
                mutation_scale=13,
                lw=1.3,
                color="#444",
                linestyle="--" if dash else "-",
                connectionstyle=f"arc3,rad={rad}",
            )
        )
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + ly, label, ha="center", fontsize=7.8)

    def group(x, y, w, h, label, ec):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.6,rounding_size=2",
                fc="none",
                ec=ec,
                lw=1.4,
                linestyle=(0, (4, 3)),
            )
        )
        ax.text(x + 1, y + h + 1.2, label, fontsize=9.5, weight="bold", color=ec)

    group(2, 46, 126, 19, "ML pipeline (heart/ package)", "#2f6db5")
    box(4, 49, 18, 12, "UCI Cleveland", "303 patients, 14 cols", "#dce9f9")
    box(28, 49, 20, 12, "Clean & validate", "'?'→NaN, binary target", "#dce9f9")
    box(54, 49, 16, 12, "EDA", "5 figure sets", "#dce9f9")
    box(
        76, 49, 24, 12, "Train + tune", "GridSearchCV, 5-fold CV\nLogReg vs RandomForest", "#dce9f9"
    )
    box(106, 49, 20, 12, "MLflow", "params, metrics,\nplots, models", "#fde9c8")
    arrow(22.5, 55, 27.5, 55)
    arrow(48.5, 55, 53.5, 55)
    arrow(70.5, 55, 75.5, 55)
    arrow(100.5, 55, 105.5, 55, "log")
    group(2, 24, 126, 15, "GitHub Actions CI/CD (.github/workflows/ci.yml)", "#2c8a4b")
    stages = ["lint", "test", "train", "docker", "deploy-k8s", "monitoring", "publish"]
    for i, stage in enumerate(stages):
        x = 5 + i * 17.5
        box(x, 27, 14, 9, stage, "", "#daf2e1")
        if i:
            arrow(x - 3.3, 31.5, x - 0.4, 31.5)
    arrow(88, 48.5, 40, 36.5, "model.joblib artifact", dash=True)
    group(2, 1, 126, 16, "Serving & monitoring runtime", "#8a3fb5")
    box(4, 4, 22, 10, "Docker image", "FastAPI + pipeline", "#efe0f7")
    box(32, 4, 26, 10, "Kubernetes (kind)", "Deployment ×2, Service, HPA", "#efe0f7")
    box(64, 4, 18, 10, "NGINX Ingress", "heart-api.local", "#efe0f7")
    box(88, 4, 16, 10, "Prometheus", "scrapes /metrics", "#efe0f7")
    box(110, 4, 16, 10, "Grafana", "6-panel dashboard", "#efe0f7")
    arrow(26.5, 9, 31.5, 9)
    arrow(63.5, 9, 58.5, 9, "routes", ly=1.2)
    arrow(104.5, 9, 109.5, 9)
    arrow(45, 3.4, 96, 3.4, "/metrics scrape", rad=0.18, ly=-6.2)
    arrow(66, 26.5, 20, 14.5, "build & push to GHCR", dash=True)
    plt.tight_layout()
    plt.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    arch = OUT / "img_arch.png"
    architecture(arch)
    with Image.open(arch) as im:
        index["arch"] = [f"build/{arch.name}", im.width, im.height]
    for key, rel in SOURCES.items():
        im = Image.open(ROOT / rel).convert("RGB")
        if key in CROP_HEIGHT:
            im = im.crop((0, 0, im.width, min(im.height, CROP_HEIGHT[key])))
        out = OUT / f"img_{key}.png"
        im.save(out)
        index[key] = [f"build/{out.name}", im.width, im.height]
    (OUT / "imgs.json").write_text(json.dumps(index, indent=1))
    print(f"prepared {len(index)} images in {OUT}")


if __name__ == "__main__":
    main()
