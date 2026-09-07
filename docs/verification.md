# Verification evidence

Verified September 7, 2026 with Python 3.12, Java 17, the uv-locked environment, and PySpark 3.5.6.

## Focused behavior

The complete suite passed: 15 tests. Fixtures cover merchant fallbacks, null category, repeated attempts, invalid dates and amounts, required columns, empty input, row conservation, exact ranking ties, year boundaries, shared display names, arithmetic means, the published Q2 schema, HH00 hours, installment math, Cramer's V, circular hours, required upstream paths and stable committed Gold filenames.

An AST inspection confirmed that every function in application code, scripts and tests has a concise docstring.

## Full-refresh overwrite

The complete official pipeline was triggered twice against the same paths:

```sh
uv run python -m billups.pipeline
```

Both triggers overwrote `data/bronze`, `data/silver`, `data/gold`, `results/report.md` and `results/previews.md`. All ten canonicalized Gold tables had identical row counts and SHA-256 hashes after both triggers. No run directory or success-state file is produced.

The machine had another 4 GB Spark application running during final verification. The official reruns therefore used the bundled Python 3.12 runtime with the uv-locked project packages and a 1 GB, two-worker Spark driver. The documented uv command uses the same code and dependency lock.

## Official data

Whole-population reconciliation passed at 7,274,367 rows and 146,228,071,619.260000 amount in both Silver and Gold.

Measured warnings are 41 ambiguous merchant IDs, 34,570 missing merchant IDs/unmatched lookups, 44,625 unknown categories, 628,174 denied attempts, 661,973 unknown states and 50 unknown installment values. No invalid date/amount, empty-input, join fan-out or reconciliation failure occurred.

## Dashboard

The committed-Gold Streamlit dashboard passed `streamlit.testing.v1.AppTest` with zero exceptions and a visual Chrome review of all five tabs. It renders the official totals of 7,274,367 recorded attempts, 6,646,193 approved attempts and $133,591,627,397.31 approved amount. The tables use readable headers and visual currency/percentage formatting without changing numeric Gold types. Q1 shows Rank plus the five requested report columns; Q2 publishes only Merchant, State ID and Average Amount; Q3 publishes Category and HH00 Hour; Q4 displays Cramer's V and its interpretation; Q5 directly answers items a-e and states its assumptions before the analysis. The city and category charts preserve descending approved-amount order through explicit categorical axis ordering.

The debugging notebook is valid notebook v4 JSON, contains lazy PySpark readers for all three layers, and has no stored execution counts or outputs. Its optional JupyterLab and kernel dependencies are pinned in `uv.lock`.

## Review passes

`$spark-review`: transformations use native DataFrame functions. Money is decimal(28,6), timestamps run in UTC, ranking ties are deterministic, Silver is disk-persisted only while reused, and collection is limited to bounded Gold summaries or the city/category aggregate. Two local workers reduced concurrent memory without changing outputs.

`$pipeline-review`: SHA-256 lineage, Bronze preservation, Silver lookup uniqueness, row conservation, whole-population reconciliation, stage ordering and repeated overwrite behavior passed. All five questions have Gold outputs and report coverage.

`$simplify`: the run-directory and completion-marker subsystem was removed. Four commands now use direct layer defaults, and each stage overwrites only its owned output. PySpark serves the challenge requirement; pytest provides focused evidence; pandas, PyArrow and Streamlit serve the Gold-only dashboard. No orchestration framework, cloud infrastructure, UDF or Spark SQL was added.
