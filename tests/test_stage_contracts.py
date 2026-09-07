from pathlib import Path

import pytest

from billups.common import require_completed_stage


def test_stage_requires_success_marker(tmp_path: Path):
    stage = tmp_path / "bronze"
    stage.mkdir()
    with pytest.raises(ValueError, match="incomplete"):
        require_completed_stage(stage, "Bronze")


def test_stage_accepts_success_marker(tmp_path: Path):
    stage = tmp_path / "bronze"
    stage.mkdir()
    (stage / "SUCCESS.json").write_text("{}", encoding="utf-8")
    require_completed_stage(stage, "Bronze")
