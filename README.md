# Billups data engineering challenge

A local PySpark Bronze/Silver/Gold pipeline answering the five questions in the supplied Billups case. The repository includes the generated Gold Parquet tables, an analytical report, bounded previews, and a Streamlit dashboard, so results can be reviewed without rerunning the 7.27-million-row pipeline.

## Results

- [Analytical report](results/report.md)
- [Bounded result previews](results/previews.md)
- `data/gold/`: committed dashboard-ready Parquet outputs for all five questions

The official run preserved and reconciled 7,274,367 transaction attempts totaling 146,228,071,619.260000 supplied monetary units. Recommendations compare all attempts with approved exposure; the report states the limitations around authorization, timezone, currency, costs, and installments.

## Requirements

- Python 3.12
- Java 17
- [uv](https://docs.astral.sh/uv/)

Install the exact locked environment:

```sh
uv sync --locked --dev
```

PySpark is pinned to 3.5.6. The pipeline uses native DataFrame functions and local Parquet only.

## Review the dashboard without running the pipeline

The default dashboard reads the committed `data/gold` tables:

```sh
uv run streamlit run dashboard.py
```

Open the local URL printed by Streamlit.

## Download the official source files

The repository does not commit raw, Bronze, or Silver data. Download both official sources atomically into `data/raw`:

```sh
uv run python scripts/download_data.py --destination data/raw
```

The command creates these exact paths:

```text
data/raw/historical_transactions.parquet
data/raw/merchants.csv
```

The links come from the supplied challenge PDF. The script leaves an existing file untouched and downloads through a temporary file before renaming it.

If downloading manually, use the links below and rename/place the files exactly as shown:

- [Historical transactions Parquet](https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/interview_historical_transactions.parquet/part-00000-tid-860771939793626614-979f966a-6d53-4896-9692-f81194d27b99-109986-1-c000.snappy.parquet) → `data/raw/historical_transactions.parquet`
- [Merchant CSV](https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/merchants-subset.csv) → `data/raw/merchants.csv`

## Run end to end

Choose a new output directory for every run. The pipeline refuses an existing path and never deletes or overwrites a prior run:

```sh
uv run python -m billups.pipeline \
  --raw-dir data/raw \
  --output-dir runs/local-001
```

The command writes:

```text
runs/local-001/
├── bronze/
├── silver/
├── gold/
├── previews/
├── provenance.json
├── dq.json
├── report.md
└── SUCCESS.json
```

`SUCCESS.json` is written last. A failed run may contain diagnostic partial outputs but is not consumable. Input SHA-256 hashes are stored in `provenance.json`; row and amount reconciliation plus quality counts are stored in `dq.json`.

Open the dashboard against the fresh run:

```sh
BILLUPS_GOLD_DIR=runs/local-001/gold uv run streamlit run dashboard.py
```

## Run individual stages

The same pipeline can be resumed at explicit stage boundaries. Each command requires the preceding stage's `SUCCESS.json`, writes to a new directory, and publishes its own `SUCCESS.json` only after the stage is complete.

1. Raw to Bronze, including source SHA-256 provenance:

   ```sh
   uv run python -m billups.bronze \
     --raw-dir data/raw \
     --output-dir runs/staged-001/bronze
   ```

2. Bronze to Silver, including validation, cleanup, merchant enrichment, ambiguity evidence, and DQ metrics:

   ```sh
   uv run python -m billups.silver \
     --bronze-dir runs/staged-001/bronze \
     --output-dir runs/staged-001/silver
   ```

3. Silver to Gold, including all five business questions, reconciliation, report, and bounded previews:

   ```sh
   uv run python -m billups.gold \
     --silver-dir runs/staged-001/silver \
     --output-dir runs/staged-001/gold
   ```

4. Open the dashboard from that Gold stage:

   ```sh
   BILLUPS_GOLD_DIR=runs/staged-001/gold uv run streamlit run dashboard.py
   ```

This is the local equivalent of an ordered three-task DAG:

```text
data/raw → billups.bronze → billups.silver → billups.gold → dashboard
                 └──────── billups.pipeline runs all three ────────┘
```

Rerun only a downstream stage by selecting a new output directory for it. Existing completed stages remain immutable, which makes lineage explicit and prevents accidental mixed or overwritten outputs.

## Verify

Run the hand-computable Silver, Gold, report, and edge-case checks:

```sh
uv run pytest -q
```

The pipeline also ships a deterministic synthetic source generator used for end-to-end rerun and failure-marker verification:

```sh
uv run python scripts/generate_synthetic_data.py /tmp/billups-synthetic-source
uv run python -m billups.pipeline --raw-dir /tmp/billups-synthetic-source --output-dir /tmp/billups-run-1
```

## Data handling

`data/raw`, `data/bronze`, `data/silver`, and `runs` are ignored by Git. Their directories can exist locally without committing source or runtime data. Only the final Gold data under `data/gold` is committed. The dashboard has no dependency on raw, Bronze, or Silver files.
