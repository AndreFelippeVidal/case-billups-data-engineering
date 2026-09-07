"""Deterministic analytical report helpers."""

from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def cramers_v(rows: list[dict[str, Any]]) -> float:
    """Calculate descriptive Cramer's V from city/category counts."""
    usable = [r for r in rows if r["city_id"] not in (None, -1)]
    cities = sorted({r["city_id"] for r in usable})
    categories = sorted({r["category"] for r in usable})
    if len(cities) < 2 or len(categories) < 2:
        return 0.0
    counts = {(r["city_id"], r["category"]): int(r["attempt_count"]) for r in usable}
    row_totals = {city: sum(counts.get((city, category), 0) for category in categories) for city in cities}
    column_totals = {
        category: sum(counts.get((city, category), 0) for city in cities) for category in categories
    }
    total = sum(row_totals.values())
    denominator = total * min(len(cities) - 1, len(categories) - 1)
    if denominator == 0:
        return 0.0
    chi_square = 0.0
    for city in cities:
        for category in categories:
            expected = row_totals[city] * column_totals[category] / total
            if expected:
                observed = counts.get((city, category), 0)
                chi_square += (observed - expected) ** 2 / expected
    return math.sqrt(chi_square / denominator)


def smallest_circular_interval(hour_amounts: dict[int, Decimal], target_share: float = 0.8) -> dict[str, Any]:
    """Find the shortest deterministic circular hour interval reaching a target share."""
    amounts = [Decimal(hour_amounts.get(hour, 0)) for hour in range(24)]
    total = sum(amounts)
    if total <= 0:
        return {"start_hour": 0, "end_hour": 0, "hours": 0, "share": 0.0}
    target = total * Decimal(str(target_share))
    candidates: list[tuple[int, int, Decimal]] = []
    for start in range(24):
        covered = Decimal(0)
        for length in range(1, 25):
            covered += amounts[(start + length - 1) % 24]
            if covered >= target:
                candidates.append((length, start, covered))
                break
    length, start, covered = min(candidates, key=lambda item: (item[0], item[1]))
    return {
        "start_hour": start,
        "end_hour": (start + length) % 24,
        "hours": length,
        "share": float(covered / total),
    }


def _records(frame: DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    """Collect a Gold aggregate as dictionaries with an optional row limit."""
    selected = frame.limit(limit) if limit else frame
    return [row.asDict(recursive=True) for row in selected.collect()]


def _money(value: Any) -> str:
    """Format a monetary value with two decimal places."""
    return f"{Decimal(value):,.2f}"


def render_report(gold: dict[str, DataFrame], destination: Path) -> dict[str, Any]:
    """Render the analytical findings and assumptions as Markdown."""
    cities = _records(gold["q5_cities"].orderBy("approved_amount", ascending=False), 5)
    categories = _records(gold["q5_categories"].orderBy("approved_amount", ascending=False), 5)
    months = _records(gold["q5_months"].orderBy("approved_amount_per_observed_day", ascending=False), 5)
    installments = _records(gold["q5_installments"].orderBy("plan_installments"))
    contingency = _records(gold["q4_city_category"])
    hours = _records(gold["q5_hours"])
    association = cramers_v(contingency)
    interval = smallest_circular_interval(
        {int(row["hour"]): Decimal(row["approved_amount"]) for row in hours}
    )

    lines = [
        "# Billups historical transaction analysis",
        "",
        "This report answers the five questions in the supplied case using all recorded transaction attempts. Recommendations also show approved exposure because an attempt is not necessarily realized revenue.",
        "",
        "## Q1 - Monthly top merchants by city",
        "",
        "The complete `q1_top_merchants` Gold table contains the exact top five merchant IDs for every observed year-month and city, ordered by total purchase amount with merchant ID as the deterministic tie-break. Counts are source attempts and repeated source rows are retained.",
        "",
        "## Q2 - Average amount by merchant and state",
        "",
        "The complete `q2_merchant_state` Gold table reports the arithmetic mean and attempt count at merchant ID and transaction-state grain, with the largest means first. Merchant IDs remain in the grain so two merchants sharing a display name do not collapse.",
        "",
        "## Q3 - Top hours by category",
        "",
        "The complete `q3_category_hours` Gold table contains the three hours with the largest total amount for each category. Unknown category is retained, and ascending hour breaks equal-amount ties.",
        "",
        "## Q4 - Popular merchants and city/category association",
        "",
        "Popularity is transaction-attempt count. `q4_popular_merchants` shows the five most popular merchants globally across the cities where their attempts occurred, including each city rank.",
        f"Cramer's V for known cities is **{association:.4f}**. This is a descriptive association between anonymized city and category, not evidence that location causes category demand. Unknown categories remain in the calculation; null and -1 city values are reported in Gold but excluded from this statistic.",
        "",
        "## Q5 - Advice for a new merchant",
        "",
        "### Cities",
        "",
        "Prioritize the leading cities below for further validation because they have the largest approved historical amount. City IDs are anonymized, so operational feasibility still needs local context.",
        "",
        "| City ID | Approved amount | Approved attempts | All-attempt amount |",
        "|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['city_id']} | {_money(row['approved_amount'])} | {row['approved_count']:,} | {_money(row['all_attempt_amount'])} |"
        for row in cities
    )
    lines.extend([
        "",
        "### Categories",
        "",
        "Use the leading approved-exposure categories as candidates for market research; historical amount alone does not establish margin or future demand.",
        "",
        "| Category | Approved amount | Approved attempts | All-attempt amount |",
        "|---|---:|---:|---:|",
    ])
    lines.extend(
        f"| {row['category']} | {_money(row['approved_amount'])} | {row['approved_count']:,} | {_money(row['all_attempt_amount'])} |"
        for row in categories
    )
    lines.extend([
        "",
        "### Months",
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
        "### Hours",
        "",
        f"A deterministic smallest circular interval covering at least 80% of approved amount starts at **{interval['start_hour']:02d}:00** and closes at **{interval['end_hour']:02d}:00** after {interval['hours']} hours (observed share {interval['share']:.1%}). This describes recorded demand. The source does not specify a timezone or operating costs, so it is not a profit-optimal schedule.",
        "",
        "### Installments",
        "",
        "The model treats values 0 and 1 as a one-payment baseline, n >= 2 except 999 as installment plans, and other values as unknown. Unknown values stay in Gold and are excluded from modeled profit. For n payments, cumulative default probability is 1 - 0.771^n. With 25% gross margin and 50% of value paid before default, expected profit is approved amount x (0.25 - 0.5 x probability). The flat-lifetime scenario applies 22.9% once. Half payment means half the transaction value, including odd installment counts.",
        "",
        "| Plan | Approved exposure | All-attempt exposure | Monthly-default expected profit | Flat-lifetime expected profit |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in installments:
        monthly = "Excluded" if row["expected_profit_monthly"] is None else _money(row["expected_profit_monthly"])
        flat = "Excluded" if row["expected_profit_flat_lifetime"] is None else _money(row["expected_profit_flat_lifetime"])
        lines.append(
            f"| {row['installment_plan']} | {_money(row['approved_amount'])} | {_money(row['all_attempt_amount'])} | {monthly} | {flat} |"
        )
    lines.extend([
        "",
        "Longer plans can produce negative modeled expected profit under a monthly independent-default assumption. Treat this as a sensitivity analysis: the source has no operating costs, causal effect of offering installments, realized repayment records, true currency, or merchant-specific credit policy.",
        "",
        "## Assumptions and data quality",
        "",
        "Timestamps are interpreted as source wall time in a UTC-configured Spark session for reproducibility; the business timezone is unknown. Amounts use the supplied monetary units at decimal(28,6). All authorization statuses, repeated attempts, unknown geography, nonpositive amounts and unknown installment counts are retained. Missing merchant names fall back to merchant ID; null merchant IDs use `Unknown merchant`; ambiguous merchant IDs also fall back to ID and are exported for review.",
        "",
    ])
    destination.write_text("\n".join(lines), encoding="utf-8")
    return {"cramers_v": association, "opening_interval": interval}


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
            ["year_month", "city_id", "merchant_id", "merchant_name", "total_amount", "attempt_count", "rank"],
            5,
        ),
        (
            "Q2 - Largest merchant/state averages",
            gold["q2_merchant_state"].orderBy("average_amount", ascending=False),
            ["merchant_id", "merchant_name", "state_id", "average_amount", "attempt_count"],
            5,
        ),
        (
            "Q3 - Leading category hours",
            gold["q3_category_hours"].orderBy("category", "rank"),
            ["category", "hour", "total_amount", "attempt_count", "rank"],
            12,
        ),
        (
            "Q4 - Popular merchants across cities",
            gold["q4_popular_merchants"].orderBy("global_rank", F.desc("city_attempt_count")),
            ["city_id", "merchant_id", "merchant_name", "city_attempt_count", "city_rank", "global_attempt_count", "global_rank"],
            10,
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
