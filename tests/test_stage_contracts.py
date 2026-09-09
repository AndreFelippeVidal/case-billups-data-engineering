import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from pyspark.sql import functions as F

from billups import bronze, pipeline
from billups.common import add_load_metadata, require_paths
from billups.gold import normalize_parquet_filename, quality_rows


def test_stage_requires_input_paths(tmp_path: Path):
    """A stage rejects missing upstream datasets."""
    with pytest.raises(FileNotFoundError, match="inputs are missing"):
        require_paths([tmp_path / "transactions"], "Gold")


def test_stage_accepts_existing_input_paths(tmp_path: Path):
    """A stage accepts existing upstream datasets."""
    transactions = tmp_path / "transactions"
    transactions.mkdir()
    require_paths([transactions], "Gold")


def test_gold_uses_a_stable_parquet_filename(tmp_path: Path):
    """Gold normalizes Spark's generated part filename for Git."""
    table = tmp_path / "table"
    table.mkdir()
    part = table / "part-uuid.parquet"
    part.write_bytes(b"parquet")
    (table / ".part-uuid.parquet.crc").write_bytes(b"checksum")
    normalize_parquet_filename(table)
    assert (table / "data.parquet").read_bytes() == b"parquet"
    assert not list(table.glob(".part-*.crc"))


def test_quality_rows_exposes_counts_rates_and_reconciliation():
    """Gold quality rows preserve measured counts and calculate rates."""
    metrics = {
        "row_count": 100,
        "missing_merchant_id": 2,
        "unmatched_merchant_lookup": 2,
        "ambiguous_merchant_ids": 1,
        "unknown_category": 3,
        "unknown_city": 0,
        "unknown_state": 4,
        "denied": 10,
        "unknown_authorization": 0,
        "nonpositive_amount": 0,
        "unknown_installments": 1,
    }
    rows = quality_rows(metrics, {"gold_count": 100})
    by_name = {row[0]: row for row in rows}
    assert by_name["Rows dropped"][1:5] == ("Passed", 0, 100, 0.0)
    assert by_name["Missing merchant ID"][1:5] == ("Warning", 2, 100, 0.02)
    assert by_name["Merchant identity collisions"][3:5] == (None, None)


def test_load_metadata_has_source_name_and_stage_timestamp(spark):
    """Layer metadata records the source filename and UTC load instant."""
    loaded_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    frame = spark.createDataFrame([(1,)], ["value"])
    enriched = add_load_metadata(frame, "bronze", loaded_at, "source.parquet")
    row = enriched.first()
    assert row["source_file_name"] == "source.parquet"
    formatted = enriched.select(
        F.date_format("bronze_load_timestamp", "yyyy-MM-dd HH:mm:ss").alias("loaded_at")
    ).first()
    assert formatted["loaded_at"] == "2026-01-02 03:04:05"


def test_bronze_logs_stage_failure(caplog, tmp_path: Path):
    """Bronze logs its stage boundary when required inputs are missing."""
    caplog.set_level(logging.INFO, logger="billups.bronze")
    with pytest.raises(FileNotFoundError):
        bronze.run(tmp_path / "raw", tmp_path / "bronze")
    messages = [record.getMessage() for record in caplog.records]
    assert any(message.startswith("Starting Bronze stage") for message in messages)
    assert any(message.startswith("Bronze stage failed") for message in messages)


def test_pipeline_logs_successful_stage_sequence(caplog, monkeypatch, tmp_path: Path):
    """The complete runner logs an explicit final success boundary."""
    class FakeSpark:
        """Provide the stop operation used by the pipeline runner."""

        def stop(self) -> None:
            """Record a no-op Spark shutdown."""

    fake_spark = FakeSpark()
    monkeypatch.setattr(pipeline, "build_spark", Mock(return_value=fake_spark))
    monkeypatch.setattr(pipeline.bronze, "run", Mock())
    monkeypatch.setattr(pipeline.silver, "run", Mock())
    monkeypatch.setattr(pipeline.gold, "run", Mock())
    caplog.set_level(logging.INFO, logger="billups.pipeline")

    pipeline.run(
        tmp_path / "raw",
        tmp_path / "bronze",
        tmp_path / "silver",
        tmp_path / "gold",
        tmp_path / "results",
    )

    messages = [record.getMessage() for record in caplog.records]
    assert messages[0] == "Starting complete Bronze-Silver-Gold pipeline"
    assert messages[-1].startswith("Pipeline completed successfully")
