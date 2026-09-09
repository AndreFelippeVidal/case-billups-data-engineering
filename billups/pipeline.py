"""Run Bronze, Silver and Gold in order as one local batch."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from time import perf_counter

from billups import bronze, gold, silver
from billups.common import build_spark, configure_logging


LOGGER = logging.getLogger("billups.pipeline")


def run(
    raw_dir: Path,
    bronze_dir: Path,
    silver_dir: Path,
    gold_dir: Path,
    results_dir: Path,
) -> None:
    """Overwrite Bronze, Silver, Gold, and reports in dependency order."""
    started = perf_counter()
    LOGGER.info("Starting complete Bronze-Silver-Gold pipeline")
    spark = None
    try:
        spark = build_spark("billups-local-pipeline")
        bronze.run(raw_dir, bronze_dir, spark)
        silver.run(bronze_dir, silver_dir, spark)
        gold.run(silver_dir, gold_dir, results_dir, spark)
    except Exception:
        LOGGER.error("Pipeline failed after %.1f seconds", perf_counter() - started)
        raise
    finally:
        if spark is not None:
            spark.stop()
    LOGGER.info("Pipeline completed successfully in %.1f seconds", perf_counter() - started)


def main() -> None:
    """Run the complete pipeline from the command line."""
    configure_logging()
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
