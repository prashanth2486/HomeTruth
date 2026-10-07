"""Download the public Bengaluru listings file. No Kaggle key is required."""

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paths import RAW_CSV

DATA_URL = "https://raw.githubusercontent.com/dphi-official/Datasets/master/Bengaluru_House_Data.csv"


def ensure_dataset(path: Path | None = None) -> Path:
    destination = path or RAW_CSV
    if destination.exists() and destination.stat().st_size > 1000:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, destination)
    return destination


if __name__ == "__main__":
    saved = ensure_dataset()
    print(saved)
