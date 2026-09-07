# Billups data engineering challenge

A local PySpark Bronze/Silver/Gold pipeline answering the five questions in the supplied Billups case. The repository includes the generated Gold Parquet tables, an analytical report, bounded previews, and a Streamlit dashboard, so results can be reviewed without rerunning the 7.27-million-row pipeline.

## Results

- [Analytical report](results/report.md)
- [Bounded result previews](results/previews.md)
- `data/gold/`: committed dashboard-ready Parquet outputs for all five questions

The official run preserved and reconciled 7,274,367 transaction attempts totaling 146,228,071,619.260000 supplied monetary units. Recommendations compare all attempts with approved exposure; the report states the limitations around authorization, timezone, currency, costs, and installments.

Recorded attempts count every source transaction row, including denied authorizations. Approved attempts are the rows where `authorized_flag = Y` and are used as the closer proxy for realized sales. The source has no unique transaction ID, so neither count is a deduplicated purchase count.

## Requirements

- Python 3.12
- Java 17
- [uv](https://docs.astral.sh/uv/)

Install the exact locked environment:

```sh
uv python install 3.12
uv sync --python 3.12 --locked --dev
```

PySpark is pinned to 3.5.6. The pipeline uses native DataFrame functions and local Parquet only.

## Review the dashboard without running the pipeline

The default dashboard reads the committed `data/gold` tables:

```sh
uv run streamlit run dashboard.py --server.headless false
```

The command keeps running in that terminal, prints `http://localhost:8501`, and asks the operating system to open the default browser. If no tab opens, visit [http://localhost:8501](http://localhost:8501) manually. It opens Chrome automatically only when Chrome is the system default browser.

For the written analysis, open [results/report.md](results/report.md). The supporting bounded rows are in [results/previews.md](results/previews.md), while the dashboard presents the same committed Gold tables interactively.

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

Run the complete full-refresh pipeline with one command:

```sh
uv run python -m billups.pipeline
```

Every trigger replaces the generated layers and reports with outputs from the current raw inputs:

```text
data/
├── raw/       # untouched source files
├── bronze/    # overwritten source-shaped Parquet and provenance
├── silver/    # overwritten validated/enriched Parquet and DQ
└── gold/      # overwritten business tables and reconciliation
results/
├── report.md
└── previews.md
```

Input SHA-256 hashes are stored in `data/bronze/provenance.json`. Silver quality counts are stored in `data/silver/dq.json`, and whole-population reconciliation is stored in `data/gold/reconciliation.json`.

Open the dashboard after the run:

```sh
uv run streamlit run dashboard.py --server.headless false
```

Keep this terminal running while using the dashboard. Streamlit prints the local URL, normally [http://localhost:8501](http://localhost:8501), and asks the operating system to open the default browser. Open that URL manually if the browser does not appear. If the command exits without a URL, recreate the environment with the two installation commands in the Requirements section; this avoids a stale or broken Python interpreter in `.venv`.

## Run individual stages

The same pipeline can be run at explicit stage boundaries. Each command validates that its required upstream datasets exist and overwrites only its own output layer.

1. Raw to Bronze, including source SHA-256 provenance:

   ```sh
   uv run python -m billups.bronze
   ```

2. Bronze to Silver, including validation, cleanup, merchant enrichment, ambiguity evidence, and DQ metrics:

   ```sh
   uv run python -m billups.silver
   ```

3. Silver to Gold, including all five business questions, reconciliation, report, and bounded previews:

   ```sh
   uv run python -m billups.gold
   ```

4. Open the dashboard:

   ```sh
   uv run streamlit run dashboard.py --server.headless false
   ```

This is the local equivalent of an ordered three-task DAG:

```text
data/raw → billups.bronze → billups.silver → billups.gold → dashboard
                 └──────── billups.pipeline runs all three ────────┘
```

Rerun a downstream command when only that layer needs rebuilding. For example, changing business logic requires only `billups.gold` when `data/silver` is current. This provides the useful behavior of an ordered DAG without an orchestration framework or run-state subsystem.

All paths can still be overridden through CLI arguments when testing in temporary directories. Run `uv run python -m billups.<stage> --help` for the available options.

## Debug with the notebook

Install the optional notebook tools and start JupyterLab:

```sh
uv sync --python 3.12 --locked --dev --group notebook
uv run --group notebook jupyter lab notebooks/data_debugging.ipynb
```

The notebook reads `data/bronze`, `data/silver`, and `data/gold` lazily with PySpark. It includes schema inspection and small query examples without embedding source rows or outputs in Git. Run the required pipeline stage first if a local layer does not exist.

## Verify

Run the hand-computable Silver, Gold, report, and edge-case checks:

```sh
uv run pytest -q
```

The pipeline also ships a deterministic synthetic source generator used for end-to-end overwrite verification:

```sh
uv run python scripts/generate_synthetic_data.py /tmp/billups-synthetic-source
uv run python -m billups.pipeline \
  --raw-dir /tmp/billups-synthetic-source \
  --bronze-dir /tmp/billups-bronze \
  --silver-dir /tmp/billups-silver \
  --gold-dir /tmp/billups-gold \
  --results-dir /tmp/billups-results
```

## Data handling

`data/raw`, `data/bronze`, and `data/silver` are ignored by Git. Their directories can exist locally without committing source or intermediate data. Only the final Gold data under `data/gold` is committed. The dashboard has no dependency on raw, Bronze, or Silver files.
