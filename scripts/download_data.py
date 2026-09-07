"""Download the official Billups source files atomically."""

from __future__ import annotations

import argparse
import tempfile
import urllib.request
from pathlib import Path


FILES = {
    "historical_transactions.parquet": "https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/interview_historical_transactions.parquet/part-00000-tid-860771939793626614-979f966a-6d53-4896-9692-f81194d27b99-109986-1-c000.snappy.parquet",
    "merchants.csv": "https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/merchants-subset.csv",
}


def download(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename, url in FILES.items():
        target = destination / filename
        if target.exists():
            print(f"Already present: {target}")
            continue
        with tempfile.NamedTemporaryFile(dir=destination, prefix=f".{filename}.", delete=False) as temp:
            temporary = Path(temp.name)
        try:
            print(f"Downloading {url}")
            urllib.request.urlretrieve(url, temporary)
            temporary.replace(target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=Path("data/raw"))
    download(parser.parse_args().destination)
