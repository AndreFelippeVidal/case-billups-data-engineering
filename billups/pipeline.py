"""Run Bronze, Silver and Gold in order as one local batch."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from billups import bronze, gold, silver
from billups.common import build_spark, write_json


def run(raw_dir: Path, output_dir: Path, publish_gold: Path | None = None) -> None:
    if output_dir.exists():
        raise FileExistsError(f"Pipeline output directory already exists: {output_dir}")
    if publish_gold and publish_gold.exists():
        raise FileExistsError(f"Published Gold directory already exists: {publish_gold}")
    output_dir.mkdir(parents=True)
    spark = build_spark("billups-local-pipeline")
    try:
        bronze.run(raw_dir, output_dir / "bronze", spark)
        silver.run(output_dir / "bronze", output_dir / "silver", spark)
        gold.run(output_dir / "silver", output_dir / "gold", publish_gold, spark)

        shutil.copyfile(output_dir / "bronze" / "provenance.json", output_dir / "provenance.json")
        shutil.copyfile(output_dir / "gold" / "report.md", output_dir / "report.md")
        shutil.copytree(output_dir / "gold" / "previews", output_dir / "previews")
        silver_dq = json.loads((output_dir / "silver" / "dq.json").read_text(encoding="utf-8"))
        gold_dq = json.loads((output_dir / "gold" / "dq.json").read_text(encoding="utf-8"))
        silver_dq.update(gold_dq)
        write_json(output_dir / "dq.json", silver_dq)
        write_json(
            output_dir / "SUCCESS.json",
            {
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "stages": {
                    "bronze": "bronze/SUCCESS.json",
                    "silver": "silver/SUCCESS.json",
                    "gold": "gold/SUCCESS.json",
                },
            },
        )
    finally:
        spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--publish-gold", type=Path)
    args = parser.parse_args()
    run(args.raw_dir, args.output_dir, args.publish_gold)


if __name__ == "__main__":
    main()
