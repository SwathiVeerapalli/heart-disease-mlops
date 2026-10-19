"""Train candidate models with CV + grid search, track everything in MLflow,
and export the best pipeline (preprocessing + model) for serving.

Usage: python -m heart.train [--quick]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import mlflow.sklearn  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import sklearn  # noqa: E402
from mlflow.models import infer_signature  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (  # noqa: E402
    GridSearchCV,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline  # noqa: E402

from heart.config import CLEAN_PATH, FEATURES, MODEL_DIR, SEED, TARGET  # noqa: E402
from heart.data import validate  # noqa: E402
from heart.features import build_preprocessor  # noqa: E402

SCORING = ["accuracy", "precision", "recall", "f1", "roc_auc"]


def candidates(seed: int, quick: bool = False) -> dict:
    """Model name -> (estimator, hyper-parameter grid)."""
    if quick:
        return {
            "logistic_regression": (
                LogisticRegression(max_iter=2000, solver="liblinear", random_state=seed),
                {"clf__C": [0.1, 1.0]},
            ),
            "random_forest": (
                RandomForestClassifier(n_estimators=50, random_state=seed),
                {"clf__max_depth": [4]},
            ),
        }
    return {
        "logistic_regression": (
            LogisticRegression(max_iter=2000, solver="liblinear", random_state=seed),
            {
                "clf__C": [0.01, 0.1, 1.0, 10.0],
                "clf__penalty": ["l1", "l2"],
                "clf__class_weight": [None, "balanced"],
            },
        ),
        "random_forest": (
            RandomForestClassifier(random_state=seed, n_jobs=-1),
            {
                "clf__n_estimators": [200, 400],
                "clf__max_depth": [None, 4, 8],
                "clf__min_samples_leaf": [1, 3, 5],
            },
        ),
    }


def holdout_metrics(model, X: pd.DataFrame, y: pd.Series) -> dict:
    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "test_accuracy": accuracy_score(y, pred),
        "test_precision": precision_score(y, pred, zero_division=0),
        "test_recall": recall_score(y, pred, zero_division=0),
        "test_f1": f1_score(y, pred, zero_division=0),
        "test_roc_auc": roc_auc_score(y, proba),
    }


def log_plots(model, X: pd.DataFrame, y: pd.Series, name: str, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(5, 4))
    ConfusionMatrixDisplay.from_estimator(model, X, y, ax=ax, colorbar=False)
    ax.set_title(f"{name} - confusion matrix (test)")
    path = outdir / f"{name}_confusion_matrix.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    mlflow.log_artifact(str(path), "plots")

    fig, ax = plt.subplots(figsize=(5, 4))
    RocCurveDisplay.from_estimator(model, X, y, ax=ax)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_title(f"{name} - ROC (test)")
    path = outdir / f"{name}_roc.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    mlflow.log_artifact(str(path), "plots")

    clf = model.named_steps["clf"]
    names = model.named_steps["prep"].get_feature_names_out()
    if hasattr(clf, "feature_importances_"):
        weights, label = clf.feature_importances_, "importance"
    else:
        weights, label = np.abs(clf.coef_[0]), "|coefficient|"
    imp = pd.Series(weights, index=names).sort_values().tail(15)
    fig, ax = plt.subplots(figsize=(6, 5))
    imp.plot.barh(ax=ax, color="#4C72B0")
    ax.set_title(f"{name} - top features ({label})")
    path = outdir / f"{name}_feature_importance.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    mlflow.log_artifact(str(path), "plots")


def run_training(
    df: pd.DataFrame,
    experiment: str = "heart-disease",
    cv_folds: int = 5,
    seed: int = SEED,
    model_dir: Path = MODEL_DIR,
    quick: bool = False,
) -> dict:
    validate(df)
    X, y = df[FEATURES], df[TARGET]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=seed)
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    mlflow.set_experiment(experiment)
    plot_dir = model_dir / "plots"
    results = []

    for name, (estimator, grid) in candidates(seed, quick).items():
        with mlflow.start_run(run_name=name) as run:
            pipe = Pipeline([("prep", build_preprocessor()), ("clf", estimator)])
            search = GridSearchCV(pipe, grid, cv=cv, scoring="roc_auc", n_jobs=-1)
            search.fit(X_tr, y_tr)
            best = search.best_estimator_

            cv_res = cross_validate(best, X_tr, y_tr, cv=cv, scoring=SCORING)
            metrics = {}
            for m in SCORING:
                metrics[f"cv_{m}_mean"] = float(np.mean(cv_res[f"test_{m}"]))
                metrics[f"cv_{m}_std"] = float(np.std(cv_res[f"test_{m}"]))
            metrics.update(holdout_metrics(best, X_te, y_te))

            mlflow.log_params(
                {
                    "model": name,
                    "cv_folds": cv_folds,
                    "seed": seed,
                    "train_rows": len(X_tr),
                    "test_rows": len(X_te),
                    "grid_size": len(search.cv_results_["params"]),
                    **{k.replace("clf__", ""): v for k, v in search.best_params_.items()},
                }
            )
            mlflow.log_metrics(metrics)

            grid_path = plot_dir / f"{name}_grid_results.csv"
            plot_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(search.cv_results_).to_csv(grid_path, index=False)
            mlflow.log_artifact(str(grid_path), "tuning")
            log_plots(best, X_te, y_te, name, plot_dir)

            signature = infer_signature(X_tr, best.predict_proba(X_tr))
            mlflow.sklearn.log_model(
                best, artifact_path="model", signature=signature, input_example=X_tr.head(3)
            )
            print(
                f"{name}: cv_roc_auc={metrics['cv_roc_auc_mean']:.3f} "
                f"test_roc_auc={metrics['test_roc_auc']:.3f}"
            )
            results.append(
                {
                    "name": name,
                    "run_id": run.info.run_id,
                    "model": best,
                    "metrics": metrics,
                    "params": search.best_params_,
                }
            )

    # Select on cross-validated ROC-AUC (not the single test split) to avoid overfitting
    champion = max(results, key=lambda r: r["metrics"]["cv_roc_auc_mean"])
    mlflow.MlflowClient().set_tag(champion["run_id"], "champion", "true")

    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(champion["model"], model_dir / "model.joblib")
    metadata = {
        "model_name": champion["name"],
        "mlflow_run_id": champion["run_id"],
        "version": datetime.now(UTC).strftime("%Y%m%d%H%M%S"),
        "sklearn_version": sklearn.__version__,
        "features": FEATURES,
        "best_params": {k: str(v) for k, v in champion["params"].items()},
        "metrics": {k: round(v, 4) for k, v in champion["metrics"].items()},
        "candidates": {r["name"]: round(r["metrics"]["cv_roc_auc_mean"], 4) for r in results},
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Champion: {champion['name']} -> {model_dir / 'model.joblib'}")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(CLEAN_PATH))
    parser.add_argument("--experiment", default="heart-disease")
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument("--quick", action="store_true", help="tiny grids for smoke tests")
    args = parser.parse_args()
    df = pd.read_csv(args.data)
    run_training(df, args.experiment, args.cv_folds, quick=args.quick)


if __name__ == "__main__":
    main()
