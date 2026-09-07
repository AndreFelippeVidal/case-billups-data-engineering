# Verification evidence

Verified September 7, 2026 with Python 3.12, Java 17, uv, and PySpark 3.5.6.

## Focused behavior

Command: `uv run pytest -q`

Result: 14 tests passed. Fixtures cover known, missing and ambiguous merchant names; null category; repeated attempts; invalid amount/date; absent columns; empty input; join row conservation; Q1 six-way ties and year boundaries; shared display names; Q2 arithmetic mean; Q3 four tied hours; installment math and unknown exclusion; independent/associated contingency tables; a circular opening interval crossing midnight; and stage completion-marker contracts.

## Synthetic end to end

Commands:

```sh
uv run python scripts/generate_synthetic_data.py /private/tmp/billups-e2e-20260907-source
uv run python -m billups.pipeline --raw-dir /private/tmp/billups-e2e-20260907-source --output-dir /private/tmp/billups-e2e-20260907-run1
uv run python -m billups.pipeline --raw-dir /private/tmp/billups-e2e-20260907-source --output-dir /private/tmp/billups-e2e-20260907-run2
```

All ten canonicalized Gold tables had identical row counts and SHA-256 hashes between runs. Both runs produced `SUCCESS.json`.

A source generated with `--omit-merchant-name` failed on the required-column check. `/private/tmp/billups-e2e-20260907-failed/SUCCESS.json` did not exist after failure.

The standalone `billups.bronze`, `billups.silver`, and `billups.gold` commands were then run in separate Spark processes against the same synthetic source. Each produced its own `SUCCESS.json`, and all ten Gold tables matched the earlier orchestrated output. A final refactored `billups.pipeline` run also matched all ten tables and produced Bronze, Silver, Gold, and pipeline completion markers.

## Official data

Command:

```sh
uv run python -m billups.pipeline --raw-dir data/raw --output-dir runs/official --publish-gold data/gold
```

Result: success in approximately one minute on the local machine. The pipeline wrote both input SHA-256 hashes, Bronze and Silver Parquet, 10 Gold tables, DQ JSON, report, previews, and `SUCCESS.json`.

Reconciliation passed at 7,274,367 rows and 146,228,071,619.260000 amount in both Silver and Gold. Measured warnings were 41 ambiguous merchant IDs, 34,570 missing merchant IDs/unmatched lookups, 44,625 unknown categories, 628,174 denied attempts, 661,973 unknown states and 50 unknown installment values. No invalid date/amount, empty-input, fan-out, or reconciliation failure occurred.

## Review passes

`$spark-review`: all transformations use native DataFrame functions. Money is decimal(28,6), timestamps run in UTC, ranking ties are deterministic, Silver is disk-persisted only while reused, and collection is limited to small Gold summaries or the bounded city/category contingency table. The global popularity rank uses one global sort over merchant aggregates; the official run completed without a material bottleneck.

`$pipeline-review`: the fresh-directory guard, SHA-256 lineage, Bronze preservation, Silver lookup uniqueness, row conservation, whole-population reconciliation, completion marker, two-run equality and failed-run marker behavior passed. All five questions have Gold outputs and report coverage.

The committed-Gold Streamlit dashboard passed its local health endpoint and `streamlit.testing.v1.AppTest` with zero exceptions. It rendered five question tabs and the official totals of 7,274,367 attempts, 6,646,193 approved attempts, and 133,591,627,397.31 approved amount.

`$simplify`: each dependency serves a direct requirement: PySpark for the brief, pytest for focused evidence, and pandas/PyArrow/Streamlit for the Gold-only dashboard. No orchestration framework, cloud infrastructure, UDF, Spark SQL, or overwrite path was added. Shared aggregate helpers remove duplication while the question-specific transformations remain explicit.
