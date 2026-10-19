"""Exploratory data analysis: writes figures and summary tables to reports/.

Usage: python -m heart.eda
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from heart.config import (  # noqa: E402
    CATEGORICAL_FEATURES,
    CLEAN_PATH,
    FIGURES_DIR,
    NUMERIC_FEATURES,
    REPORTS_DIR,
    TARGET,
)

LABELS = {0: "No disease", 1: "Disease"}


def class_balance(df: pd.DataFrame) -> None:
    counts = df[TARGET].map(LABELS).value_counts()
    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(counts.index, counts.values, color=["#4C72B0", "#C44E52"])
    for bar, n in zip(bars, counts.values, strict=False):
        ax.annotate(
            f"{n} ({n / len(df):.0%})",
            (bar.get_x() + bar.get_width() / 2, n),
            ha="center",
            va="bottom",
        )
    ax.set_title("Class balance")
    ax.set_ylabel("Patients")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_class_balance.png", dpi=150)
    plt.close(fig)


def numeric_histograms(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    plot_df = df.assign(label=df[TARGET].map(LABELS))
    for ax, col in zip(axes.flat, NUMERIC_FEATURES, strict=False):
        sns.histplot(plot_df, x=col, hue="label", kde=True, ax=ax, element="step")
        ax.set_title(col)
    fig.suptitle("Numeric feature distributions by outcome")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_numeric_histograms.png", dpi=150)
    plt.close(fig)


def correlation_heatmap(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(11, 9))
    corr = df.corr(numeric_only=True)
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax, square=True)
    ax.set_title("Feature correlation matrix")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_correlation_heatmap.png", dpi=150)
    plt.close(fig)


def categorical_rates(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    for ax, col in zip(axes.flat, CATEGORICAL_FEATURES, strict=False):
        rate = df.groupby(col)[TARGET].mean()
        ax.bar(rate.index.astype(str), rate.values, color="#55A868")
        ax.set_ylim(0, 1)
        ax.set_title(f"Disease rate by {col}")
    axes.flat[-1].axis("off")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_categorical_disease_rate.png", dpi=150)
    plt.close(fig)


def outlier_boxplots(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, len(NUMERIC_FEATURES), figsize=(18, 4))
    for ax, col in zip(axes, NUMERIC_FEATURES, strict=False):
        sns.boxplot(y=df[col], ax=ax, color="#8172B2")
        ax.set_title(col)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_outliers.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CLEAN_PATH)
    df.describe().T.to_csv(REPORTS_DIR / "summary_stats.csv")
    df.isna().sum().rename("missing").to_csv(REPORTS_DIR / "missing_values.csv")
    class_balance(df)
    numeric_histograms(df)
    correlation_heatmap(df)
    categorical_rates(df)
    outlier_boxplots(df)
    print(f"EDA figures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
