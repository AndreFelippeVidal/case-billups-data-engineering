from pathlib import Path

import pytest

from billups.common import require_paths


def test_stage_requires_input_paths(tmp_path: Path):
    """A stage rejects missing upstream datasets."""
    with pytest.raises(FileNotFoundError, match="inputs are missing"):
        require_paths([tmp_path / "transactions"], "Gold")


def test_stage_accepts_existing_input_paths(tmp_path: Path):
    """A stage accepts existing upstream datasets."""
    transactions = tmp_path / "transactions"
    transactions.mkdir()
    require_paths([transactions], "Gold")
