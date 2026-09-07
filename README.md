# Billups data engineering challenge

A deliberately small local PySpark implementation of Bronze/Silver/Gold, focused on five analytical questions and reproducible evidence.

## Current state
The Python environment is prepared. Pipeline implementation and the final analytical report are pending; no analytical result is claimed yet.

## Environment
Use Python 3.12, Java 17 and uv.

```sh
uv sync --locked --dev
```

PySpark is pinned to 3.5.6 and dependencies are locked in uv.lock. The local .venv and input datasets are ignored by Git.

## Scope
Native PySpark functions, local Parquet layers, proportional quality checks and a report. Main answers include all recorded attempts; recommendations also compare approved transactions. Repository visibility is private by user request; the original brief requests public submission.
