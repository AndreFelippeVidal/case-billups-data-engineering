from pathlib import Path

import pytest

from billups.common import require_paths
from billups.gold import normalize_parquet_filename


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
