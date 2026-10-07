"""Filesystem locations shared by training, the API, and the app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_CSV = DATA_DIR / "raw" / "Bengaluru_House_Data.csv"
CATALOG_PATH = DATA_DIR / "catalog.json"
RENT_YIELDS_PATH = DATA_DIR / "rent_yields.json"
DATABASE_PATH = DATA_DIR / "app.db"
CACHE_DIR = DATA_DIR / "cache"
LOG_DIR = DATA_DIR / "logs"
PREDICTION_LOG = LOG_DIR / "predictions.jsonl"
MODEL_DIR = ROOT / "models"
ARTIFACT_PATH = MODEL_DIR / "hometruth.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
