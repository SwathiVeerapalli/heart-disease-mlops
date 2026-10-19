"""Download the UCI Cleveland dataset and write the cleaned CSV.

Usage: python -m heart.download [--force]
"""

from __future__ import annotations

import argparse
import time
import urllib.request

from heart.config import CLEAN_PATH, DATA_URL, RAW_PATH
from heart.data import clean, load_raw, validate


def download(force: bool = False) -> None:
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if RAW_PATH.exists() and not force:
        print(f"Raw data already present: {RAW_PATH}")
    else:
        for attempt in range(1, 4):
            try:
                print(f"Downloading {DATA_URL} (attempt {attempt})")
                urllib.request.urlretrieve(DATA_URL, RAW_PATH)
                break
            except OSError as exc:
                if attempt == 3:
                    raise
                print(f"Download failed: {exc}; retrying")
                time.sleep(5 * attempt)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()

    download(args.force)
    raw = load_raw(RAW_PATH)
    df = clean(raw)
    validate(df)
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)
    print(f"Raw rows: {len(raw)} -> clean rows: {len(df)}")
    print(f"Missing values:\n{df.isna().sum()[df.isna().sum() > 0]}")
    print(f"Class balance:\n{df['target'].value_counts(normalize=True).round(3)}")
    print(f"Saved {CLEAN_PATH}")


if __name__ == "__main__":
    main()
