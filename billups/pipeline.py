"""Run Bronze, Silver and Gold in order as one local batch."""

from __future__ import annotations

import argparse
from pathlib import Path

from billups import bronze, gold, silver
from billups.common import build_spark


def run(
    raw_dir: Path,
    bronze_dir: Path,
    silver_dir: Path,
    gold_dir: Path,
    results_dir: Path,
) -> None:
    """Overwrite Bronze, Silver, Gold, and reports in dependency order."""
    spark = build_spark("billups-local-pipeline")
    try:
        bronze.run(raw_dir, bronze_dir, spark)
        print("Bronze stage completed.", flush=True)
        silver.run(bronze_dir, silver_dir, spark)
        print("Silver stage completed.", flush=True)
        gold.run(silver_dir, gold_dir, results_dir, spark)
        print("Gold stage completed.", flush=True)
    finally:
        spark.stop()
    print("Pipeline completed successfully.", flush=True)


def main() -> None:
    """Run the complete pipeline from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--bronze-dir", type=Path, default=Path("data/bronze"))
    parser.add_argument("--silver-dir", type=Path, default=Path("data/silver"))
    parser.add_argument("--gold-dir", type=Path, default=Path("data/gold"))
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    args = parser.parse_args()
    run(args.raw_dir, args.bronze_dir, args.silver_dir, args.gold_dir, args.results_dir)


if __name__ == "__main__":
    main()
