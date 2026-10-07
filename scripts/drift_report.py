"""Summarise logged predictions. The log has no income and no office location."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from formatting import format_inr
from log_predictions import summarize_log


def main() -> None:
    summary = summarize_log()
    print(f"Logged predictions: {summary['count']}")
    if summary["median_p50_inr"] is None:
        print("No predictions yet.")
        return
    print(f"Median mid estimate: {format_inr(summary['median_p50_inr'])}")
    print("Localities:")
    for name, count in sorted(summary["localities"].items(), key=lambda item: (-item[1], item[0])):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
