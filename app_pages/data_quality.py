"""Present committed Gold data-quality results without upstream dependencies."""

import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).parents[1]
GOLD = Path(os.environ.get("BILLUPS_GOLD_DIR", PROJECT_ROOT / "data" / "gold"))
if not GOLD.is_absolute():
    GOLD = PROJECT_ROOT / GOLD


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    """Load one committed Gold Parquet table for the quality page."""
    path = GOLD / name
    if not path.exists():
        raise FileNotFoundError(f"Missing Gold table: {path}")
    frame = pd.read_parquet(path)
    for column in frame.select_dtypes(include="object"):
        first = next((value for value in frame[column] if value is not None), None)
        if isinstance(first, Decimal):
            frame[column] = frame[column].astype(float)
    return frame


def metric_value(summary: pd.DataFrame, check_name: str) -> tuple[int, float | None]:
    """Return the count and optional rate for one named quality check."""
    row = summary.loc[summary["check_name"] == check_name].iloc[0]
    rate = None if pd.isna(row["result_rate"]) else float(row["result_rate"])
    return int(row["result_count"]), rate


def format_metric(count: int, rate: float | None = None, rows: bool = False) -> str:
    """Format a quality metric as a count, percentage, or row label."""
    if rate is not None:
        return f"{rate:.2%}"
    if rows:
        return f"{count:,} rows"
    return f"{count:,}"


st.title("Data quality")
st.caption(
    "These check results are committed Gold artifacts. This page can be reviewed without raw, "
    "Bronze, or Silver files."
)

if not GOLD.exists():
    st.error("Gold outputs are missing. Run the pipeline command from README.md first.")
    st.stop()

summary = load_table("data_quality_summary")
samples = load_table("data_quality_warning_samples")
conflicts = load_table("data_quality_merchant_conflicts")

first_row = st.columns(4)
for column, name, use_rate in zip(
    first_row,
    ["Rows processed", "Rows dropped", "Missing merchant ID", "Merchant identity collisions"],
    [False, False, True, False],
):
    count, rate = metric_value(summary, name)
    column.metric(name, format_metric(count, rate if use_rate else None))

second_row = st.columns(4)
for column, name, use_rate, rows in zip(
    second_row,
    ["Unknown category", "Unknown state", "Unknown installments", "Denied authorization"],
    [True, True, False, True],
    [False, False, True, False],
):
    count, rate = metric_value(summary, name)
    column.metric(name, format_metric(count, rate if use_rate else None, rows=rows))

st.info(
    "The pipeline fails on missing required columns, invalid dates or amounts, empty input, merchant "
    "join fan-out, or failed row/amount reconciliation. The conditions below are warnings or context: "
    "their rows remain in the dataset so the analysis stays reconcilable to the source."
)

st.subheader("Quality check results")
summary_display = summary.rename(columns={
    "check_name": "Check", "status": "Status", "result_count": "Affected Rows",
    "population_count": "Population", "result_rate": "Rate", "description": "Meaning",
})
summary_display["Affected Rows"] = summary_display["Affected Rows"].map(lambda value: f"{int(value):,}")
summary_display["Population"] = summary_display["Population"].map(
    lambda value: "" if pd.isna(value) else f"{int(value):,}"
)
st.dataframe(
    summary_display,
    column_config={
        "Rate": st.column_config.NumberColumn("Rate", format="percent"),
    },
    use_container_width=True,
    hide_index=True,
)

st.subheader("Merchant identity collisions")
st.write(
    f"{len(conflicts):,} merchant IDs have more than one nonblank name in the merchant source. "
    "The Silver logic uses the merchant ID as the display name for these records, avoiding an arbitrary "
    "name choice and preserving a many-to-one transaction join."
)
conflict_display = conflicts.copy()
conflict_display["nonblank_names"] = conflict_display["nonblank_names"].map(
    lambda values: " | ".join(values)
)
conflict_display = conflict_display.rename(columns={
    "merchant_id": "Merchant ID", "nonblank_names": "Source Names",
    "distinct_name_count": "Distinct Names",
})
st.dataframe(conflict_display, use_container_width=True, hide_index=True)

st.subheader("Warning samples")
st.write(
    "These are deterministic examples from preserved Silver rows, exported by the Gold stage. "
    "They support investigation without committing the full intermediate dataset."
)
available_checks = samples["check_name"].drop_duplicates().tolist()
selected_check = st.selectbox("Warning condition", available_checks)
sample_display = samples[samples["check_name"] == selected_check].drop(
    columns=["check_name", "sample_rank"]
).rename(columns={
    "merchant_id": "Merchant ID", "merchant_name": "Merchant", "purchase_date": "Purchase Date",
    "city_id": "City ID", "state_id": "State ID", "category": "Category",
    "installments": "Installments", "authorized_flag": "Authorized",
    "purchase_amount": "Purchase Amount",
})
st.dataframe(
    sample_display,
    column_config={"Purchase Amount": st.column_config.NumberColumn("Purchase Amount", format="$%.2f")},
    use_container_width=True,
    hide_index=True,
)

st.subheader("About possible duplicates")
st.warning(
    "The source has no unique transaction identifier, so identical-looking rows cannot be classified "
    "reliably as accidental duplicates. Repeated attempts may be valid behavior and are intentionally "
    "preserved. Therefore, the dashboard does not report an unsupported exact-duplicate KPI."
)

st.subheader("How the audit artifacts fit together")
st.markdown(
    "- `data/bronze/provenance.json` fingerprints each downloaded input with SHA-256, allowing a rerun "
    "to prove which exact file bytes were processed.\n"
    "- `data/silver/dq.json` records full-population counts produced while Silver validates and enriches "
    "the transactions.\n"
    "- `data/gold/reconciliation.json` confirms that the Gold city aggregate ties back to the Silver "
    "row count and total amount.\n"
    "- The three `data/gold/data_quality_*` tables publish the summary, warning samples, and merchant "
    "collisions used by this page."
)
