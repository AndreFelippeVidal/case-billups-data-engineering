"""Load raw source files into an immutable local Bronze stage."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from pyspark.sql import SparkSession

from billups.common import (
    add_load_metadata,
    build_spark,
    configure_logging,
    sha256,
    source_bytes,
    write_json,
)


LOGGER = logging.getLogger("billups.bronze")


def run(raw_dir: Path, output_dir: Path, spark: SparkSession | None = None) -> None:
    """Overwrite Bronze Parquet and source provenance from raw files."""
    started = perf_counter()
    LOGGER.info("Starting Bronze stage: raw=%s output=%s", raw_dir, output_dir)
    owns_spark = spark is None
    try:
        transaction_file = raw_dir / "historical_transactions.parquet"
        merchant_file = raw_dir / "merchants.csv"
        for source in (transaction_file, merchant_file):
            if not source.exists():
                raise FileNotFoundError(f"Required source file is missing: {source}")
        spark = spark or build_spark("billups-bronze")
        output_dir.mkdir(parents=True, exist_ok=True)
        loaded_at = datetime.now(timezone.utc)
        LOGGER.info("Reading raw transactions: %s", transaction_file)
        transactions = add_load_metadata(
            spark.read.parquet(str(transaction_file)),
            "bronze",
            loaded_at,
            transaction_file.name,
        )
        LOGGER.info("Reading raw merchant metadata: %s", merchant_file)
        merchants = add_load_metadata(
            spark.read.option("header", True).csv(str(merchant_file)),
            "bronze",
            loaded_at,
            merchant_file.name,
        )
        LOGGER.info("Writing Bronze transactions and merchants with overwrite mode")
        transactions.write.mode("overwrite").parquet(str(output_dir / "historical_transactions"))
        merchants.write.mode("overwrite").parquet(str(output_dir / "merchants"))
        LOGGER.info("Calculating source SHA-256 provenance")
        provenance = {
            transaction_file.name: {
                "bytes": source_bytes(transaction_file),
                "sha256": sha256(transaction_file),
            },
            merchant_file.name: {
                "bytes": source_bytes(merchant_file),
                "sha256": sha256(merchant_file),
            },
        }
        write_json(output_dir / "provenance.json", provenance)
    except Exception:
        LOGGER.error("Bronze stage failed after %.1f seconds", perf_counter() - started)
        raise
    finally:
        if owns_spark and spark is not None:
            spark.stop()
    LOGGER.info("Bronze stage completed in %.1f seconds", perf_counter() - started)


def main() -> None:
    """Run the Raw-to-Bronze command-line stage."""
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/bronze"))
    args = parser.parse_args()
    run(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
