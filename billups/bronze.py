"""Load raw source files into an immutable local Bronze stage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession

from billups.common import add_load_metadata, build_spark, sha256, source_bytes, write_json


def run(raw_dir: Path, output_dir: Path, spark: SparkSession | None = None) -> None:
    """Overwrite Bronze Parquet and source provenance from raw files."""
    transaction_file = raw_dir / "historical_transactions.parquet"
    merchant_file = raw_dir / "merchants.csv"
    for source in (transaction_file, merchant_file):
        if not source.exists():
            raise FileNotFoundError(f"Required source file is missing: {source}")

    owns_spark = spark is None
    spark = spark or build_spark("billups-bronze")
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        loaded_at = datetime.now(timezone.utc)
        transactions = add_load_metadata(
            spark.read.parquet(str(transaction_file)),
            "bronze",
            loaded_at,
            transaction_file.name,
        )
        merchants = add_load_metadata(
            spark.read.option("header", True).csv(str(merchant_file)),
            "bronze",
            loaded_at,
            merchant_file.name,
        )
        transactions.write.mode("overwrite").parquet(str(output_dir / "historical_transactions"))
        merchants.write.mode("overwrite").parquet(str(output_dir / "merchants"))
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
    finally:
        if owns_spark:
            spark.stop()


def main() -> None:
    """Run the Raw-to-Bronze command-line stage."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/bronze"))
    args = parser.parse_args()
    run(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
