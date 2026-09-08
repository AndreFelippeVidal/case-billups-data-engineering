"""Deterministic analytical report helpers."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _records(frame: DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    """Collect a Gold aggregate as dictionaries with an optional row limit."""
    selected = frame.limit(limit) if limit else frame
    return [row.asDict(recursive=True) for row in selected.collect()]


def _money(value: Any) -> str:
    """Format a monetary value with two decimal places."""
    amount = Decimal(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _month_label(value: str) -> str:
    """Format a sortable year-month value for presentation."""
    year, month = value.split("-")
    return f"{MONTH_NAMES[int(month) - 1]} {year}"


def render_report(gold: dict[str, DataFrame], destination: Path) -> dict[str, Any]:
    """Render the analytical findings and assumptions as Markdown."""
    q1_sample = _records(gold["q1_top_merchants"].orderBy("year_month", "city_id", "rank"), 5)
    q2_leaders = _records(gold["q2_merchant_state"].orderBy("average_amount", ascending=False), 5)
    q3_hours = _records(gold["q3_category_hours"])
    popular_merchants = _records(
        gold["q4_popular_merchants"].orderBy("global_rank", F.desc("city_attempt_count"))
    )
    cities = _records(gold["q5_cities"].orderBy("rank"), 5)
    categories = _records(gold["q5_categories"].orderBy("rank"), 5)
    months = _records(gold["q5_months"].orderBy("exposure_adjusted_rank"), 5)
    installments = _records(gold["q5_installments"].orderBy("plan_installments"))
    association = _records(gold["q4_association"])[0]
    interval = _records(gold["q5_opening_hours"])[0]
    overview = _records(gold["q5_overview"])[0]

    lines = [
        "# Billups historical transaction analysis",
        "",
        "This report answers the five questions in the supplied case. A recorded attempt is every source row regardless of authorization; an approved attempt is a row with `authorized_flag = Y` and is the closer proxy for realized sales. The source has no unique transaction ID, so counts are attempts rather than deduplicated purchases.",
        "",
        "## Gold business overview",
        "",
        f"The Gold overview records **{overview['recorded_attempts']:,}** attempts totaling **{_money(overview['recorded_amount'])}**, with an average recorded amount of **{_money(overview['average_recorded_amount'])}** across **{overview['city_count']:,}** cities and **{overview['month_count']:,}** months. **{overview['approved_attempts']:,}** attempts were approved ({overview['approval_rate']:.1%}), totaling **{_money(overview['approved_amount'])}**; **{overview['denied_attempts']:,}** were not approved.",
        "",
        "## Q1 - Monthly top merchants by city",
        "",
        "The complete `q1_top_merchants` Gold table answers every observed year-month and city. It ranks total recorded purchase amount, uses merchant ID as the deterministic tie-break, and retains repeated source rows. The first month/city result is shown below; the dashboard provides selectors for the complete answer.",
        "",
        "| Rank | Month | City | Merchant | Purchase Total | No of Sales |",
        "|---:|---|---:|---|---:|---:|",
    ]
    lines.extend(
        f"| {row['rank']} | {_month_label(row['year_month'])} | {row['city_id']} | {row['merchant_name']} | {_money(row['total_amount'])} | {row['attempt_count']:,} |"
        for row in q1_sample
    )
    lines.extend([
        "",
        "## Q2 - Average amount by merchant and state",
        "",
        "The table reports the arithmetic mean of recorded purchase amounts at merchant and transaction-state grain, with the largest averages first. Merchant ID remains in the internal aggregation grain so merchants sharing a display name do not collapse, but the requested published result contains only Merchant, State ID and Average Amount.",
        "",
        "| Merchant | State ID | Average Amount |",
        "|---|---:|---:|",
    ])
    lines.extend(
        f"| {row['merchant']} | {row['state_id']} | {_money(row['average_amount'])} |"
        for row in q2_leaders
    )
    lines.extend([
        "",
        "## Q3 - Top hours by category",
        "",
        "The table contains the three hours with the largest total recorded purchase amount for each category. Unknown category represents source rows with a null or blank category and is retained for visible identification. Hours use the requested HH00 format; ascending hour breaks equal-amount ties.",
        "",
        "| Category | Hour |",
        "|---|---:|",
    ])
    lines.extend(f"| {row['category']} | {row['hour']} |" for row in q3_hours)
    lines.extend([
        "",
        "## Q4 - Popular merchants and city/category association",
        "",
        "Popularity is the number of recorded transaction attempts for each merchant, as specified by the challenge. The table shows the five most popular merchants globally and the cities where their attempts occurred.",
        "",
        "| Global Rank | Merchant | City ID | City Transactions | City Rank | Global Transactions |",
        "|---:|---|---:|---:|---:|---:|",
    ])
    lines.extend(
        f"| {row['global_rank']} | {row['merchant_name']} | {row['city_id']} | {row['city_attempt_count']:,} | {row['city_rank']:,} | {row['global_attempt_count']:,} |"
        for row in popular_merchants
    )
    lines.extend([
        "",
        f"Cramer's V for known cities is **{association['cramers_v']:.4f}**, calculated in Gold from {association['population']:,} attempts across {association['city_count']:,} cities and {association['category_count']:,} categories. This is a descriptive association between anonymized city and category, not evidence that location causes category demand. Unknown categories remain in the calculation; null and -1 city values are reported in Gold but excluded from this statistic.",
        "",
        "## Q5 - Advice for a new merchant",
        "",
        "### a. Cities",
        "",
        "Prioritize the leading cities below for further validation because they have the largest approved historical amount. City IDs are anonymized, so operational feasibility still needs local context.",
        "",
        "| Rank | City ID | Approved amount | Approved share | Approved attempts | All-attempt amount |",
        "|---:|---:|---:|---:|---:|---:|",
    ])
    lines.extend(
        f"| {row['rank']} | {row['city_id']} | {_money(row['approved_amount'])} | {row['approved_share']:.2%} | {row['approved_count']:,} | {_money(row['all_attempt_amount'])} |"
        for row in cities
    )
    lines.extend([
        "",
        "### b. Categories",
        "",
        "Use the leading approved-exposure categories as candidates for market research; historical amount alone does not establish margin or future demand.",
        "",
        "| Rank | Category | Approved amount | Approved share | Approved attempts | All-attempt amount |",
        "|---:|---|---:|---:|---:|---:|",
    ])
    lines.extend(
        f"| {row['rank']} | {row['category']} | {_money(row['approved_amount'])} | {row['approved_share']:.2%} | {row['approved_count']:,} | {_money(row['all_attempt_amount'])} |"
        for row in categories
    )
    lines.extend([
        "",
        "### c. Months",
        "",
        "The dataset covers 14 months, with partial boundary months possible. Ranking below uses approved amount per observed date to avoid favoring months with more observed days. It does not establish recurring annual seasonality.",
        "",
        "| Month | Observed dates | Days | Approved amount/day |",
        "|---|---|---:|---:|",
    ])
    lines.extend(
        f"| {row['year_month']} | {row['first_observed_date']} to {row['last_observed_date']} | {row['observed_days']} | {_money(row['approved_amount_per_observed_day'])} |"
        for row in months
    )
    lines.extend([
        "",
        "### d. Hours",
        "",
        f"A deterministic smallest circular interval covering at least 80% of approved amount starts at **{interval['start_hour']:02d}:00** and closes at **{interval['end_hour']:02d}:00** after {interval['hours']} hours. It covers **{_money(interval['covered_amount'])}**, or {interval['share']:.1%} of the Gold approved total. This describes recorded demand. The source does not specify a timezone or operating costs, so it is not a profit-optimal schedule.",
        "",
        "### e. Installments",
        "",
        "The model treats values 0 and 1 as a one-payment baseline, n >= 2 except 999 as installment plans, and other values as unknown. Unknown values stay in Gold and are excluded from modeled profit. For n payments, cumulative default probability is 1 - 0.771^n. With 25% gross margin and 50% of value paid before default, expected profit is approved amount x (0.25 - 0.5 x probability). The flat-lifetime scenario applies 22.9% once. Half payment means half the transaction value, including odd installment counts.",
        "",
        "| Plan | Approved exposure | All-attempt exposure | Monthly expected rate | Monthly-default expected profit | Flat-lifetime expected profit |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in installments:
        monthly = "Excluded" if row["expected_profit_monthly"] is None else _money(row["expected_profit_monthly"])
        flat = "Excluded" if row["expected_profit_flat_lifetime"] is None else _money(row["expected_profit_flat_lifetime"])
        rate = "Excluded" if row["expected_profit_rate_monthly"] is None else f"{row['expected_profit_rate_monthly']:.2%}"
        lines.append(
            f"| {row['installment_plan']} | {_money(row['approved_amount'])} | {_money(row['all_attempt_amount'])} | {rate} | {monthly} | {flat} |"
        )
    lines.extend([
        "",
        "Under the requested monthly independent-default interpretation, two payments retain positive modeled expected profit while plans of three or more payments turn negative. Recommend at most two payments under these assumptions, then validate with actual repayment data. The flat-lifetime alternative remains positive and is shown because the wording can also be read as applying 22.9% once over the plan lifetime.",
        "",
        "## Assumptions and data quality",
        "",
        "Recommendations use approved attempts as the sales proxy and are based strictly on the historical transactions. Timestamps are interpreted as source wall time in a UTC-configured Spark session; the business timezone is unknown. Silver standardizes amounts to the supplied monetary units at decimal(28,2); dollar signs are presentation formatting because the true currency is unspecified. Layer load timestamps are technical metadata and are omitted from this report. The 14-month period cannot establish recurring annual seasonality. City and category IDs are anonymized. All authorization statuses, repeated attempts, unknown geography, nonpositive amounts and unknown installment counts are retained. Missing merchant names fall back to merchant ID; null merchant IDs use `Unknown merchant`; ambiguous merchant IDs also fall back to ID and are exported for review. The installment model assumes equal payments, a 25% gross margin, independent monthly 22.9% default probability, and 50% of transaction value paid before default; operating costs, repayment history and causal sales uplift are unavailable.",
        "",
    ])
    destination.write_text("\n".join(lines), encoding="utf-8")
    return {"cramers_v": association["cramers_v"], "opening_interval": interval}


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> list[str]:
    """Render bounded result rows as a simple Markdown table."""
    labels = [column.replace("_", " ").title() for column in columns]
    lines = ["| " + " | ".join(labels) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        values = []
        for column in columns:
            value = row[column]
            values.append(f"{value:.2f}" if isinstance(value, Decimal) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_previews(
    gold: dict[str, DataFrame], reconciliation: dict[str, Any], destination: Path
) -> None:
    """Render bounded, reproducible previews of the main Gold answers."""
    selections = [
        (
            "Q1 - Monthly top merchants by city",
            gold["q1_top_merchants"].orderBy("year_month", "city_id", "rank"),
            ["rank", "year_month", "city_id", "merchant_id", "merchant_name", "total_amount", "attempt_count"],
            5,
        ),
        (
            "Q2 - Largest merchant/state averages",
            gold["q2_merchant_state"].orderBy("average_amount", ascending=False),
            ["merchant", "state_id", "average_amount"],
            5,
        ),
        (
            "Q3 - Leading category hours",
            gold["q3_category_hours"],
            ["category", "hour"],
            12,
        ),
        (
            "Q4 - Popular merchants across cities",
            gold["q4_popular_merchants"].orderBy("global_rank", F.desc("city_attempt_count")),
            ["city_id", "merchant_id", "merchant_name", "city_attempt_count", "city_rank", "global_attempt_count", "global_rank"],
            10,
        ),
        (
            "Q4 - City and category association",
            gold["q4_association"],
            ["population", "city_count", "category_count", "chi_square", "cramers_v"],
            1,
        ),
        (
            "Q5 - Business overview",
            gold["q5_overview"],
            ["recorded_amount", "recorded_attempts", "approved_amount", "approved_attempts", "approval_rate"],
            1,
        ),
        (
            "Q5 - Recommended opening interval",
            gold["q5_opening_hours"],
            ["start_hour", "end_hour", "hours", "covered_amount", "share", "target_share"],
            1,
        ),
    ]
    lines = [
        "# Bounded Gold previews",
        "",
        "These deterministic samples come from the generated Gold Parquet outputs.",
        "",
    ]
    for title, frame, columns, limit in selections:
        lines.extend([f"## {title}", ""])
        lines.extend(_markdown_table(_records(frame.select(*columns), limit), columns))
        lines.append("")
    lines.extend(
        [
            "## Reconciliation",
            "",
            f"Silver and Gold reconcile at {reconciliation['gold_count']:,} rows and {reconciliation['gold_amount']} total amount.",
            "",
        ]
    )
    destination.write_text("\n".join(lines), encoding="utf-8")
