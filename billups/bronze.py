"""Load raw source files into an immutable local Bronze stage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession

from billups.common import build_spark, sha256, source_bytes, write_json


def run(raw_dir: Path, output_dir: Path, spark: SparkSession | None = None) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Bronze output directory already exists: {output_dir}")
    transaction_file = raw_dir / "historical_transactions.parquet"
    merchant_file = raw_dir / "merchants.csv"
    for source in (transaction_file, merchant_file):
        if not source.exists():
            raise FileNotFoundError(f"Required source file is missing: {source}")

    owns_spark = spark is None
    spark = spark or build_spark("billups-bronze")
    output_dir.mkdir(parents=True)
    try:
        transactions = spark.read.parquet(str(transaction_file))
        merchants = spark.read.option("header", True).csv(str(merchant_file))
        transactions.write.mode("errorifexists").parquet(str(output_dir / "historical_transactions"))
        merchants.write.mode("errorifexists").parquet(str(output_dir / "merchants"))
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
        write_json(
            output_dir / "SUCCESS.json",
            {
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "outputs": ["historical_transactions", "merchants", "provenance.json"],
                "stage": "bronze",
            },
        )
    finally:
        if owns_spark:
            spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
