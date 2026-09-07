"""Streamlit dashboard backed only by committed Gold Parquet tables."""

import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).parent
GOLD = Path(os.environ.get("BILLUPS_GOLD_DIR", PROJECT_ROOT / "data" / "gold"))
if not GOLD.is_absolute():
    GOLD = PROJECT_ROOT / GOLD


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    path = GOLD / name
    if not path.exists():
        raise FileNotFoundError(f"Missing Gold table: {path}")
    frame = pd.read_parquet(path)
    for column in frame.select_dtypes(include="object"):
        first = next((value for value in frame[column] if value is not None), None)
        if isinstance(first, Decimal):
            frame[column] = frame[column].astype(float)
    return frame


st.set_page_config(page_title="Billups transaction analysis", page_icon="📊", layout="wide")
st.title("Billups historical transaction analysis")
st.caption("Reproducible answers from the committed Gold Parquet outputs")

if not GOLD.exists():
    st.error("Gold outputs are missing. Run the pipeline command from README.md first.")
    st.stop()

q5_cities = load_table("q5_cities").sort_values("approved_amount", ascending=False)
q5_categories = load_table("q5_categories").sort_values("approved_amount", ascending=False)
q5_months = load_table("q5_months").sort_values("year_month")
q5_hours = load_table("q5_hours").sort_values("hour")

total_approved = q5_cities["approved_amount"].sum()
total_attempts = int(q5_cities["all_attempt_count"].sum())
approved_attempts = int(q5_cities["approved_count"].sum())
col1, col2, col3 = st.columns(3)
col1.metric("Recorded attempts", f"{total_attempts:,}")
col2.metric("Approved attempts", f"{approved_attempts:,}")
col3.metric("Approved amount", f"{total_approved:,.2f}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Q1 Top merchants", "Q2 Merchant averages", "Q3 Category hours", "Q4 Location", "Q5 Advice"]
)

with tab1:
    q1 = load_table("q1_top_merchants")
    months = sorted(q1["year_month"].dropna().unique())
    selected_month = st.selectbox("Month", months)
    month_rows = q1[q1["year_month"] == selected_month]
    cities = sorted(month_rows["city_id"].dropna().unique())
    selected_city = st.selectbox("City", cities)
    st.dataframe(
        month_rows[month_rows["city_id"] == selected_city].sort_values("rank"),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.dataframe(
        load_table("q2_merchant_state").sort_values("average_amount", ascending=False).head(100),
        use_container_width=True,
        hide_index=True,
    )

with tab3:
    st.dataframe(
        load_table("q3_category_hours").sort_values(["category", "rank"]),
        use_container_width=True,
        hide_index=True,
    )

with tab4:
    st.subheader("Most popular merchants across cities")
    st.dataframe(
        load_table("q4_popular_merchants").sort_values(["global_rank", "city_attempt_count"], ascending=[True, False]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Popularity is the number of recorded transaction attempts. See results/report.md for Cramer's V and interpretation.")

with tab5:
    left, right = st.columns(2)
    with left:
        st.subheader("Leading cities by approved amount")
        st.bar_chart(q5_cities.head(10).set_index("city_id")["approved_amount"])
        st.subheader("Monthly approved amount per observed day")
        st.line_chart(q5_months.set_index("year_month")["approved_amount_per_observed_day"])
    with right:
        st.subheader("Leading categories by approved amount")
        st.bar_chart(q5_categories.head(10).set_index("category")["approved_amount"])
        st.subheader("Approved amount by hour")
        st.line_chart(q5_hours.set_index("hour")["approved_amount"])
    st.subheader("Installment sensitivity")
    st.dataframe(
        load_table("q5_installments").sort_values("plan_installments"),
        use_container_width=True,
        hide_index=True,
    )
    st.info("Amounts are supplied monetary units. The source timezone, currency, operating costs, and causal demand effects are unknown.")
