"""Streamlit dashboard backed only by committed Gold Parquet tables."""

import os
from decimal import Decimal
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from billups.report import cramers_v, smallest_circular_interval


PROJECT_ROOT = Path(__file__).parent
GOLD = Path(os.environ.get("BILLUPS_GOLD_DIR", PROJECT_ROOT / "data" / "gold"))
if not GOLD.is_absolute():
    GOLD = PROJECT_ROOT / GOLD


@st.cache_data
def load_table(name: str) -> pd.DataFrame:
    """Load one Gold Parquet table for presentation."""
    path = GOLD / name
    if not path.exists():
        raise FileNotFoundError(f"Missing Gold table: {path}")
    frame = pd.read_parquet(path)
    for column in frame.select_dtypes(include="object"):
        first = next((value for value in frame[column] if value is not None), None)
        if isinstance(first, Decimal):
            frame[column] = frame[column].astype(float)
    return frame


def currency_column(label: str) -> st.column_config.NumberColumn:
    """Build a dashboard column formatted as US dollars."""
    return st.column_config.NumberColumn(label, format="$%.2f")


def show_table(frame: pd.DataFrame, formats: dict | None = None) -> None:
    """Display a full-width table with normalized labels."""
    st.dataframe(
        frame,
        column_config=formats or {},
        use_container_width=True,
        hide_index=True,
    )


def ordered_bar_chart(frame: pd.DataFrame, category: str, value: str, category_label: str) -> None:
    """Display bars in the descending order supplied by the frame."""
    chart_data = frame.copy()
    chart_data[category] = chart_data[category].astype(str)
    category_order = chart_data[category].tolist()
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(f"{category}:N", sort=category_order, title=category_label),
            y=alt.Y(f"{value}:Q", title="Approved Amount"),
            tooltip=[
                alt.Tooltip(f"{category}:N", title=category_label),
                alt.Tooltip(f"{value}:Q", title="Approved Amount", format="$,.2f"),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)


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
leading_city_ids = ", ".join(str(value) for value in q5_cities.head(5)["city_id"])
leading_categories = ", ".join(
    str(value) for value in q5_categories[q5_categories["category"] != "Unknown category"].head(3)["category"]
)
leading_months = (
    q5_months.sort_values("approved_amount_per_observed_day", ascending=False)
    .head(5)["year_month"]
    .str.cat(sep=", ")
)

total_approved = q5_cities["approved_amount"].sum()
total_attempts = int(q5_cities["all_attempt_count"].sum())
approved_attempts = int(q5_cities["approved_count"].sum())
denied_attempts = total_attempts - approved_attempts
col1, col2, col3 = st.columns(3)
col1.metric("Recorded attempts", f"{total_attempts:,}")
col2.metric("Approved attempts", f"{approved_attempts:,}")
col3.metric("Approved amount", f"${total_approved:,.2f}")
st.caption(
    "Recorded attempts are all source transaction rows, regardless of authorization. "
    f"Approved attempts are the {approved_attempts:,} rows with authorized_flag = Y; "
    f"the remaining {denied_attempts:,} attempts were denied. Because the source has no unique "
    "transaction ID, counts describe recorded attempts rather than deduplicated purchases."
)

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
    q1_display = (
        month_rows[month_rows["city_id"] == selected_city]
        .sort_values("rank")
        [["rank", "year_month", "city_id", "merchant_name", "total_amount", "attempt_count"]]
        .rename(columns={
            "rank": "Rank", "year_month": "Month", "city_id": "City",
            "merchant_name": "Merchant", "total_amount": "Purchase Total",
            "attempt_count": "No of Sales",
        })
    )
    show_table(q1_display, {"Purchase Total": currency_column("Purchase Total")})

with tab2:
    st.caption(
        "Average Amount is the arithmetic mean of recorded purchase amounts for each merchant and "
        "transaction state. Merchant ID remains part of the internal aggregation grain so merchants "
        "sharing a name are not combined, but it is omitted from the requested published result."
    )
    q2_display = (
        load_table("q2_merchant_state").sort_values("average_amount", ascending=False).head(100)
        .rename(columns={"merchant": "Merchant", "state_id": "State ID", "average_amount": "Average Amount"})
    )
    show_table(q2_display, {"Average Amount": currency_column("Average Amount")})

with tab3:
    st.info(
        "Unknown category represents source rows where category was null or blank. It is retained "
        "to preserve the source population and make missing classification easy to identify visually."
    )
    q3 = load_table("q3_category_hours")
    q3["rank"] = q3.groupby("category", sort=False).cumcount() + 1
    q3_display = q3[["rank", "category", "hour"]].rename(
        columns={"rank": "Rank", "category": "Category", "hour": "Hour"}
    )
    show_table(q3_display)

with tab4:
    st.subheader("Where the most popular merchants are located")
    st.caption(
        "Popularity follows the challenge definition: the number of recorded transaction attempts "
        "for each merchant. City ID is the city recorded on each transaction."
    )
    q4 = load_table("q4_popular_merchants").sort_values(
        ["global_rank", "city_attempt_count"], ascending=[True, False]
    )
    q4_display = q4[
        ["global_rank", "merchant_name", "city_id", "city_attempt_count", "city_rank", "global_attempt_count"]
    ].rename(columns={
        "global_rank": "Global Rank", "merchant_name": "Merchant", "city_id": "City ID",
        "city_attempt_count": "City Transactions", "city_rank": "City Rank",
        "global_attempt_count": "Global Transactions",
    })
    show_table(q4_display)

    contingency = load_table("q4_city_category")
    association = cramers_v(contingency.to_dict("records"))
    st.subheader("City and category association")
    st.metric("Cramer's V", f"{association:.4f}")
    st.write(
        "The result indicates a weak descriptive association between transaction city and category. "
        "It does not show that location causes category demand. Unknown categories are retained, "
        "while null and -1 city values are excluded from this statistic."
    )

with tab5:
    interval = smallest_circular_interval(
        {int(row.hour): Decimal(str(row.approved_amount)) for row in q5_hours.itertuples()}
    )
    st.info(
        "Advice is based strictly on the historical transactions. Approved attempts are used as the "
        "sales proxy. City and category IDs are anonymized; the source currency and business timezone "
        "are unspecified; the 14-month period cannot prove recurring seasonality; and no operating-cost, "
        "repayment, or causal demand data is available. Dollar signs below are presentation formatting."
    )

    left, right = st.columns(2)
    with left:
        st.subheader("a. Cities to focus on")
        st.write(
            f"Focus first on City IDs {leading_city_ids}. They have the highest approved historical "
            "amount and the strongest observed sales exposure. Local costs and market access still need review."
        )
        ordered_bar_chart(q5_cities.head(10), "city_id", "approved_amount", "City ID")
        st.subheader("c. Interesting months")
        st.write(
            f"The strongest months per observed day are {leading_months}. This exposure-adjusted comparison "
            "accounts for partial boundary months; the peaks do not prove annual seasonality."
        )
        st.line_chart(q5_months.set_index("year_month")["approved_amount_per_observed_day"])
    with right:
        st.subheader("b. Categories to sell")
        st.write(
            f"Prioritize Categories {leading_categories} for market testing because they have the highest "
            "approved historical amounts. Unknown category is excluded from the recommendation; historical "
            "exposure alone does not establish future demand or margin."
        )
        ordered_bar_chart(q5_categories.head(10), "category", "approved_amount", "Category")
        st.subheader("d. Recommended opening hours")
        st.write(
            f"Open at {interval['start_hour']:02d}:00 and close at {interval['end_hour']:02d}:00. "
            f"This shortest contiguous interval covers {interval['share']:.1%} of approved historical "
            "amount; operating costs and the unknown source timezone may change the practical schedule."
        )
        st.line_chart(q5_hours.set_index("hour")["approved_amount"])

    st.subheader("e. Installment recommendation")
    st.write(
        "Under the requested monthly 22.9% independent-default interpretation, two payments retain "
        "positive modeled expected profit, while plans of three or more payments turn negative. Recommend "
        "at most two payments under these assumptions and validate the result with actual repayment data. "
        "The alternative flat-lifetime interpretation stays positive and is shown to expose this ambiguity."
    )
    installment_display = load_table("q5_installments").sort_values("plan_installments").rename(columns={
        "plan_installments": "Installments", "installment_plan": "Plan",
        "all_attempt_amount": "Recorded Amount", "all_attempt_count": "Recorded Attempts",
        "approved_amount": "Approved Amount", "approved_count": "Approved Attempts",
        "monthly_default_probability": "Monthly Model Default Probability",
        "flat_lifetime_default_probability": "Flat Lifetime Default Probability",
        "expected_profit_monthly": "Monthly Model Expected Profit",
        "expected_profit_flat_lifetime": "Flat Lifetime Expected Profit",
    })
    show_table(installment_display, {
        "Recorded Amount": currency_column("Recorded Amount"),
        "Approved Amount": currency_column("Approved Amount"),
        "Monthly Model Default Probability": st.column_config.NumberColumn(
            "Monthly Model Default Probability", format="percent"
        ),
        "Flat Lifetime Default Probability": st.column_config.NumberColumn(
            "Flat Lifetime Default Probability", format="percent"
        ),
        "Monthly Model Expected Profit": currency_column("Monthly Model Expected Profit"),
        "Flat Lifetime Expected Profit": currency_column("Flat Lifetime Expected Profit"),
    })
