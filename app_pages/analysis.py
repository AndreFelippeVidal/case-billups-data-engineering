"""Streamlit dashboard backed only by committed Gold Parquet tables."""

import os
from decimal import Decimal
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).parents[1]
GOLD = Path(os.environ.get("BILLUPS_GOLD_DIR", PROJECT_ROOT / "data" / "gold"))
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
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


def currency_column(label: str, help_text: str) -> st.column_config.NumberColumn:
    """Build a dashboard column formatted as US dollars."""
    return st.column_config.NumberColumn(label, help=help_text, format="$%.2f")


def number_column(label: str, help_text: str, format_value: str | None = None):
    """Build a numeric column with an explanatory header tooltip."""
    return st.column_config.NumberColumn(label, help=help_text, format=format_value)


def month_label(value: str) -> str:
    """Format a sortable year-month value for presentation."""
    year, month = value.split("-")
    return f"{MONTH_NAMES[int(month) - 1]} {year}"


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


def merchant_city_chart(frame: pd.DataFrame) -> None:
    """Show each popular merchant's recorded attempts split across cities."""
    chart_data = frame.copy()
    chart_data["city_label"] = chart_data["city_id"].astype(str)
    merchant_order = (
        chart_data.sort_values("global_rank")["merchant_name"].drop_duplicates().tolist()
    )
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            y=alt.Y("merchant_name:N", sort=merchant_order, title="Merchant"),
            x=alt.X("sum(city_attempt_count):Q", title="Recorded Attempts"),
            color=alt.Color("city_label:N", title="City ID"),
            order=alt.Order("city_attempt_count:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("merchant_name:N", title="Merchant"),
                alt.Tooltip("city_label:N", title="City ID"),
                alt.Tooltip("city_attempt_count:Q", title="City Transactions", format=","),
                alt.Tooltip("city_share:Q", title="Merchant Share", format=".2%"),
                alt.Tooltip("global_attempt_count:Q", title="Global Transactions", format=","),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)


def hourly_demand_chart(frame: pd.DataFrame) -> None:
    """Display approved hourly demand and visually flag midnight."""
    chart_data = frame.copy()
    chart_data["hour_label"] = chart_data["hour"].map(lambda value: f"{int(value):02d}:00")
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("hour_label:N", sort=chart_data["hour_label"].tolist(), title="Hour of day"),
            y=alt.Y("approved_amount:Q", title="Approved Amount"),
            color=alt.condition(
                alt.datum.hour == 0,
                alt.value("#e45756"),
                alt.value("#74b9eb"),
            ),
            tooltip=[
                alt.Tooltip("hour_label:N", title="Hour"),
                alt.Tooltip("approved_amount:Q", title="Approved Amount", format="$,.2f"),
                alt.Tooltip("approved_count:Q", title="Approved Attempts", format=","),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def installment_profitability_chart(frame: pd.DataFrame) -> None:
    """Plot expected profit per approved monetary unit by installment plan."""
    chart_data = frame[
        frame["plan_installments"].between(1, 12) & (frame["approved_amount"] > 0)
    ].copy()
    base = alt.Chart(chart_data).encode(
        x=alt.X(
            "plan_installments:Q",
            title="Number of payments",
            axis=alt.Axis(values=list(range(1, 13)), format="d"),
            scale=alt.Scale(domain=[1, 12]),
        ),
        y=alt.Y("expected_profit_rate_monthly:Q", title="Expected profit per approved unit", axis=alt.Axis(format=".0%")),
    )
    line = base.mark_line(color="#9c9c9c")
    points = base.mark_point(filled=True, size=90).encode(
        color=alt.Color(
            "monthly_profitability:N",
            title="Outcome",
            scale=alt.Scale(domain=["Positive", "Negative"], range=["#2ca02c", "#d62728"]),
        ),
        tooltip=[
            alt.Tooltip("plan_installments:Q", title="Payments"),
            alt.Tooltip("expected_profit_rate_monthly:Q", title="Expected Profit Rate", format=".2%"),
        ],
    )
    zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(strokeDash=[5, 5], color="#777").encode(y="zero:Q")
    st.altair_chart(line + points + zero, use_container_width=True)


st.title("Billups historical transaction analysis")
st.caption("Reproducible answers from the committed Gold Parquet outputs")

if not GOLD.exists():
    st.error("Gold outputs are missing. Run the pipeline command from README.md first.")
    st.stop()

q5_cities = load_table("q5_cities").sort_values("rank")
q5_categories = load_table("q5_categories").sort_values("rank")
q5_months = load_table("q5_months").sort_values("year_month")
q5_hours = load_table("q5_hours").sort_values("hour")
overview_values = load_table("q5_overview").iloc[0]
opening_hours = load_table("q5_opening_hours").iloc[0]
leading_city_ids = ", ".join(str(value) for value in q5_cities.head(5)["city_id"])
leading_categories = ", ".join(
    str(value) for value in q5_categories[q5_categories["category"] != "Unknown category"].head(3)["category"]
)
leading_months = (
    q5_months.sort_values("exposure_adjusted_rank")
    .head(5)["year_month"]
    .map(month_label)
    .str.cat(sep=", ")
)

total_approved = overview_values["approved_amount"]
total_recorded = overview_values["recorded_amount"]
total_attempts = int(overview_values["recorded_attempts"])
approved_attempts = int(overview_values["approved_attempts"])
denied_attempts = int(overview_values["denied_attempts"])
st.subheader("Business overview")
overview = st.columns(5)
overview[0].metric(
    "Recorded amount",
    f"${total_recorded / 1_000_000_000:,.1f}B",
    help="Sum of purchase_amount across every recorded transaction attempt.",
)
overview[1].metric(
    "Recorded attempts",
    f"{total_attempts:,}",
    help="Count of all source transaction rows, regardless of authorization status.",
)
overview[2].metric(
    "Average recorded amount",
    f"${overview_values['average_recorded_amount']:,.2f}",
    help="Recorded amount divided by recorded attempts.",
)
overview[3].metric(
    "Cities",
    f"{int(overview_values['city_count']):,}",
    help="Count of distinct transaction City IDs observed in the source.",
)
overview[4].metric(
    "Months",
    f"{int(overview_values['month_count']):,}",
    help="Count of distinct calendar year-months observed in purchase timestamps.",
)
st.subheader("Authorization context")
authorization = st.columns(5)
authorization[0].metric(
    "Approved attempts",
    f"{approved_attempts:,}",
    help="Count of source rows where authorized_flag equals Y.",
)
authorization[1].metric(
    "Approval rate",
    f"{overview_values['approval_rate']:.1%}",
    help="Approved attempts divided by all recorded attempts.",
)
authorization[2].metric(
    "Approved amount",
    f"${total_approved:,.2f}",
    help="Sum of purchase_amount for rows where authorized_flag equals Y.",
)
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
    selected_month = st.selectbox("Month", months, format_func=month_label)
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
    q1_display["Month"] = q1_display["Month"].map(month_label)
    show_table(q1_display, {
        "Rank": number_column(
            "Rank", "Position within the selected month and city by descending Purchase Total."
        ),
        "Purchase Total": currency_column(
            "Purchase Total", "Sum of recorded purchase_amount for this month, city, and merchant."
        ),
        "No of Sales": number_column(
            "No of Sales", "Count of recorded transaction attempts for this month, city, and merchant."
        ),
    })

with tab2:
    st.caption(
        "Average Amount is the arithmetic mean of recorded purchase amounts for each merchant and "
        "transaction state. Merchant ID remains part of the internal aggregation grain so merchants "
        "sharing a name are not combined, but it is omitted from the requested published result."
    )
    q2_display = (
        load_table("q2_merchant_state").sort_values("average_amount", ascending=False).head(100)
        [["merchant", "state_id", "average_amount"]]
        .rename(columns={"merchant": "Merchant", "state_id": "State ID", "average_amount": "Average Amount"})
    )
    show_table(q2_display, {
        "Average Amount": currency_column(
            "Average Amount",
            "Arithmetic mean: total recorded purchase amount divided by attempts for the merchant and state.",
        )
    })

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
    show_table(q3_display, {
        "Rank": number_column(
            "Rank", "Position of the hour within its category by descending recorded purchase amount."
        ),
        "Hour": st.column_config.TextColumn(
            "Hour", help="Hour bucket selected among the top three for the category; displayed as HH00."
        ),
    })

with tab4:
    st.subheader("Where the most popular merchants are located")
    st.caption(
        "Popularity follows the challenge definition: the number of recorded transaction attempts "
        "for each merchant. City ID is the city recorded on each transaction."
    )
    q4 = load_table("q4_popular_merchants").sort_values(
        ["global_rank", "city_attempt_count"], ascending=[True, False]
    )
    merchant_city_chart(q4)
    q4_display = q4[
        ["global_rank", "merchant_name", "city_id", "city_attempt_count", "city_rank", "global_attempt_count"]
    ].rename(columns={
        "global_rank": "Global Rank", "merchant_name": "Merchant", "city_id": "City ID",
        "city_attempt_count": "City Transactions", "city_rank": "City Rank",
        "global_attempt_count": "Global Transactions",
    })
    show_table(q4_display, {
        "Global Rank": number_column(
            "Global Rank", "Merchant position by total recorded attempts across every city."
        ),
        "City Transactions": number_column(
            "City Transactions", "Recorded attempts for this merchant in this transaction city."
        ),
        "City Rank": number_column(
            "City Rank", "Merchant position by recorded attempts within this transaction city."
        ),
        "Global Transactions": number_column(
            "Global Transactions", "Recorded attempts for this merchant across all transaction cities."
        ),
    })

    association = load_table("q4_association").iloc[0]
    st.subheader("City and category association")
    st.metric(
        "Cramer's V",
        f"{association['cramers_v']:.4f}",
        help=(
            "Association strength between transaction City ID and Category: "
            "sqrt(chi-square / (population × min(cities−1, categories−1)))."
        ),
    )
    st.write(
        "The result indicates a weak descriptive association between transaction city and category. "
        "It does not show that location causes category demand. Unknown categories are retained, "
        "while null and -1 city values are excluded from this statistic."
    )

with tab5:
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
        city_table = q5_cities.head(10).copy()
        city_table = city_table[
            ["rank", "city_id", "approved_amount", "approved_count", "approved_share"]
        ].rename(columns={
            "rank": "Rank", "city_id": "City ID", "approved_amount": "Approved Amount",
            "approved_count": "Approved Sales", "approved_share": "Approved Share",
        })
        show_table(city_table, {
            "Rank": number_column("Rank", "City position by descending Approved Amount."),
            "Approved Amount": currency_column(
                "Approved Amount", "Sum of purchase_amount for approved attempts in this city."
            ),
            "Approved Sales": number_column(
                "Approved Sales", "Count of attempts with authorized_flag equal to Y in this city."
            ),
            "Approved Share": number_column(
                "Approved Share",
                "City Approved Amount divided by the approved amount across all cities.",
                "percent",
            ),
        })
    with right:
        st.subheader("b. Categories to sell")
        st.write(
            f"Prioritize Categories {leading_categories} for market testing because they have the highest "
            "approved historical amounts. Unknown category is excluded from the recommendation; historical "
            "exposure alone does not establish future demand or margin."
        )
        ordered_bar_chart(q5_categories.head(10), "category", "approved_amount", "Category")
        category_table = q5_categories.copy()
        category_table = category_table[
            ["rank", "category", "approved_amount", "approved_count", "approved_share"]
        ].rename(columns={
            "rank": "Rank", "category": "Category", "approved_amount": "Approved Amount",
            "approved_count": "Approved Sales", "approved_share": "Approved Share",
        })
        show_table(category_table, {
            "Rank": number_column("Rank", "Category position by descending Approved Amount."),
            "Approved Amount": currency_column(
                "Approved Amount", "Sum of purchase_amount for approved attempts in this category."
            ),
            "Approved Sales": number_column(
                "Approved Sales", "Count of attempts with authorized_flag equal to Y in this category."
            ),
            "Approved Share": number_column(
                "Approved Share",
                "Category Approved Amount divided by the approved amount across all categories.",
                "percent",
            ),
        })
    left, right = st.columns(2)
    with left:
        st.subheader("c. Interesting months")
        st.write(
            f"The strongest months per observed day are {leading_months}. This exposure-adjusted comparison "
            "accounts for partial boundary months; the peaks do not prove annual seasonality."
        )
        st.line_chart(q5_months.set_index("year_month")["approved_amount_per_observed_day"])
    with right:
        st.subheader("d. Recommended opening hours")
        st.write(
            f"Open at {int(opening_hours['start_hour']):02d}:00 and close at "
            f"{int(opening_hours['end_hour']):02d}:00. This shortest contiguous interval covers "
            f"{opening_hours['share']:.1%} of approved historical "
            "amount; operating costs and the unknown source timezone may change the practical schedule."
        )
        hourly_demand_chart(q5_hours)
        midnight = q5_hours[q5_hours["hour"] == 0].iloc[0]
        st.warning(
            f"The midnight bucket contains {int(midnight['approved_count']):,} approved attempts and "
            f"${midnight['approved_amount']:,.2f}, or {midnight['approved_share']:.1%} "
            "of approved amount. Its level is unusual relative to neighboring hours. It may represent "
            "real behavior, timezone conversion, or batched/default timestamps; the source does not "
            "contain enough context to distinguish these explanations."
        )

    st.subheader("e. Installment recommendation")
    st.write(
        "Under the requested monthly 22.9% independent-default interpretation, two payments retain "
        "positive modeled expected profit, while plans of three or more payments turn negative. Recommend "
        "at most two payments under these assumptions and validate the result with actual repayment data. "
        "The alternative flat-lifetime interpretation stays positive and is shown to expose this ambiguity."
    )
    installments = load_table("q5_installments").sort_values("plan_installments")
    installment_profitability_chart(installments)
    installment_display = installments[[
        "plan_installments", "installment_plan", "all_attempt_amount", "all_attempt_count",
        "approved_amount", "approved_count", "monthly_default_probability",
        "flat_lifetime_default_probability", "expected_profit_monthly",
        "expected_profit_flat_lifetime",
    ]].rename(columns={
        "plan_installments": "Installments", "installment_plan": "Plan",
        "all_attempt_amount": "Recorded Amount", "all_attempt_count": "Recorded Attempts",
        "approved_amount": "Approved Amount", "approved_count": "Approved Attempts",
        "monthly_default_probability": "Monthly Model Default Probability",
        "flat_lifetime_default_probability": "Flat Lifetime Default Probability",
        "expected_profit_monthly": "Monthly Model Expected Profit",
        "expected_profit_flat_lifetime": "Flat Lifetime Expected Profit",
    })
    show_table(installment_display, {
        "Installments": number_column(
            "Installments",
            "Normalized payment count: source values 0 and 1 form the one-payment baseline; 999 is unknown.",
        ),
        "Plan": st.column_config.TextColumn(
            "Plan", help="Readable label derived from the normalized number of payments."
        ),
        "Recorded Amount": currency_column(
            "Recorded Amount", "Sum of purchase_amount for all attempts in this payment plan."
        ),
        "Recorded Attempts": number_column(
            "Recorded Attempts", "Count of all source attempts in this payment plan."
        ),
        "Approved Amount": currency_column(
            "Approved Amount", "Sum of purchase_amount for approved attempts in this payment plan."
        ),
        "Approved Attempts": number_column(
            "Approved Attempts", "Count of attempts with authorized_flag equal to Y in this payment plan."
        ),
        "Monthly Model Default Probability": number_column(
            "Monthly Model Default Probability",
            "Cumulative probability under independent monthly default: 1 − 0.771^n.",
            "percent",
        ),
        "Flat Lifetime Default Probability": number_column(
            "Flat Lifetime Default Probability",
            "Alternative scenario applying the 22.9% default probability once over the plan lifetime.",
            "percent",
        ),
        "Monthly Model Expected Profit": currency_column(
            "Monthly Model Expected Profit",
            "Approved Amount × (25% gross margin − 50% × cumulative monthly default probability).",
        ),
        "Flat Lifetime Expected Profit": currency_column(
            "Flat Lifetime Expected Profit",
            "Approved Amount × (25% gross margin − 50% × 22.9% lifetime default probability).",
        ),
    })
