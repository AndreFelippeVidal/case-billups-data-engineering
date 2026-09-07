from pathlib import Path

import pytest

from billups.common import require_paths
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
