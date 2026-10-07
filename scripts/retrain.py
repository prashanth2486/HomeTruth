"""Download the listings file if needed, then retrain and write models/metrics.json."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from download_data import ensure_dataset
from train import train_and_save


def main() -> None:
    ensure_dataset()
    train_and_save()


if __name__ == "__main__":
    main()
