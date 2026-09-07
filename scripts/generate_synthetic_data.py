"""Generate a small deterministic source pair for end-to-end verification."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pyspark.sql import SparkSession


def generate(destination: Path, omit_merchant_name: bool = False) -> None:
    """Write a deterministic source pair for pipeline verification."""
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")
    destination.mkdir(parents=True)
    spark = (
        SparkSession.builder.master("local[2]")
        .appName("billups-synthetic-source")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    rows = [
        ("Y", "c1", 1, 0, "A", 10, "m1", 0, "2017-01-01 23:00:00", 1, 1, 100.0),
        ("Y", "c2", 1, 2, "A", 10, "m1", 0, "2017-01-02 00:00:00", 1, 1, 50.0),
        ("N", "c3", 2, 3, None, 20, "m2", 0, "2017-02-01 12:00:00", 2, 2, 25.0),
        ("Y", "c4", -1, 999, "B", 20, "missing", 0, "2017-02-02 12:00:00", -1, 2, 75.0),
    ]
    schema = "authorized_flag string, customer_id string, city_id long, installments long, category string, merchant_category_id long, merchant_id string, month_lag long, purchase_date string, state_id long, subsector_id long, purchase_amount double"
    spark.createDataFrame(rows, schema).coalesce(1).write.parquet(
        str(destination / "historical_transactions.parquet")
    )
    spark.stop()
    with (destination / "merchants.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        if omit_merchant_name:
            writer.writerow(["merchant_id"])
            writer.writerow(["m1"])
            writer.writerow(["m2"])
        else:
            writer.writerow(["merchant_id", "merchant_name"])
            writer.writerow(["m1", "Merchant One"])
            writer.writerow(["m2", "Merchant Two"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--omit-merchant-name", action="store_true")
    args = parser.parse_args()
    generate(args.destination, args.omit_merchant_name)
