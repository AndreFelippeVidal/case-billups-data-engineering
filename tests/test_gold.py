from __future__ import annotations

from decimal import Decimal

from billups.transforms import (
    q1_top_merchants,
    q2_merchant_state,
    q3_category_hours,
    q4_association,
    q5_categories,
    q5_cities,
    q5_hours,
    q5_installments,
    q5_opening_hours,
    q5_overview,
    to_silver,
)


TX_COLUMNS = [
    "merchant_id", "purchase_date", "purchase_amount", "city_id", "state_id",
    "category", "installments", "authorized_flag",
]


def silver_fixture(spark):
    """Build a hand-computable Silver fixture for Gold tests."""
    rows = []
    for merchant in ["m6", "m5", "m4", "m3", "m2", "m1"]:
        rows.append((merchant, "2017-01-01 01:00:00", "10", 1, 1, "A", 1, "Y"))
    rows.extend([
        ("m1", "2017-01-02 02:00:00", "20", 1, 1, "A", 2, "Y"),
        ("same1", "2017-02-01 03:00:00", "30", 2, 2, "B", 3, "Y"),
        ("same2", "2017-02-01 04:00:00", "40", 2, 2, "B", 4, "N"),
        ("m1", "2018-01-01 05:00:00", "50", 1, 1, "A", 10, "Y"),
    ])
    merchants = [(f"m{i}", f"Merchant {i}") for i in range(1, 7)] + [
        ("same1", "Shared"), ("same2", "Shared")
    ]
    return to_silver(
        spark.createDataFrame(rows, TX_COLUMNS),
        spark.createDataFrame(merchants, ["merchant_id", "merchant_name"]),
    ).transactions


def test_q1_exact_top_five_tie_break_year_and_shared_names(spark):
    """Q1 handles ties, years, counts, and shared display names."""
    result = q1_top_merchants(silver_fixture(spark))
    january_2017 = result.filter("year_month = '2017-01' and city_id = 1").orderBy("rank").collect()
    assert len(january_2017) == 5
    assert january_2017[0]["merchant_id"] == "m1"
    assert [row["merchant_id"] for row in january_2017[1:]] == ["m2", "m3", "m4", "m5"]
    assert january_2017[0]["total_amount"] == Decimal("30.000000")
    assert january_2017[0]["attempt_count"] == 2
    assert result.filter("year_month = '2018-01'").count() == 1
    assert result.filter("year_month = '2017-02' and merchant_name = 'Shared'").count() == 2


def test_q2_uses_arithmetic_mean_at_merchant_state_grain(spark):
    """Q2 computes the arithmetic mean at the required grain."""
    result = q2_merchant_state(silver_fixture(spark))
    row = result.filter("merchant = 'Merchant 1' and state_id = 1").first()
    assert result.columns == ["merchant", "state_id", "average_amount"]
    assert row["average_amount"] == Decimal("26.666667")


def test_q3_exact_top_three_with_hour_tie_break(spark):
    """Q3 uses ascending hour to resolve equal totals."""
    rows = [
        ("m1", f"2017-01-01 0{hour}:00:00", "10", 1, 1, "C", 1, "Y")
        for hour in [4, 3, 2, 1]
    ]
    merchants = spark.createDataFrame([("m1", "Known")], ["merchant_id", "merchant_name"])
    silver = to_silver(spark.createDataFrame(rows, TX_COLUMNS), merchants).transactions
    result = q3_category_hours(silver)
    assert result.columns == ["category", "hour"]
    assert [row["hour"] for row in result.collect()] == ["0100", "0200", "0300"]


def test_installment_formula_and_unknown_exclusion(spark):
    """Installment scenarios follow the formula and exclude unknowns."""
    result = q5_installments(silver_fixture(spark))
    two = result.filter("plan_installments = 2").first()
    assert abs(two["monthly_default_probability"] - (1 - 0.771**2)) < 1e-12
    long_plan = result.filter("plan_installments = 10").first()
    assert long_plan["expected_profit_monthly"] < 0
    assert long_plan["expected_profit_rate_monthly"] < 0
    assert long_plan["monthly_profitability"] == "Negative"

    unknown_row = spark.createDataFrame(
        [("m", "2017-01-01 00:00:00", "5", 1, 1, "A", 999, "Y")], TX_COLUMNS
    )
    merchants = spark.createDataFrame([("m", "Known")], ["merchant_id", "merchant_name"])
    unknown = q5_installments(to_silver(unknown_row, merchants).transactions).first()
    assert unknown["installment_plan"] == "Unknown"
    assert unknown["expected_profit_monthly"] is None


def test_cramers_v_is_calculated_in_gold(spark):
    """Gold Cramer's V distinguishes independent and associated tables."""
    independent = [(city, category, 10) for city in [1, 2] for category in ["A", "B"]]
    associated = [(1, "A", 20), (1, "B", 0), (2, "A", 0), (2, "B", 20)]
    schema = ["city_id", "category", "attempt_count"]
    assert q4_association(spark.createDataFrame(independent, schema)).first()["cramers_v"] == 0
    assert q4_association(spark.createDataFrame(associated, schema)).first()["cramers_v"] == 1


def test_opening_interval_is_calculated_in_gold_and_can_cross_midnight(spark):
    """Gold opening interval supports demand spanning midnight."""
    hours = spark.createDataFrame(
        [(23, Decimal("50.00")), (0, Decimal("40.00")), (12, Decimal("10.00"))],
        ["hour", "approved_amount"],
    )
    result = q5_opening_hours(hours).first()
    assert result["start_hour"] == 23
    assert result["end_hour"] == 1
    assert result["hours"] == 2
    assert result["share"] == 0.9


def test_gold_recommendation_metrics_are_precomputed(spark):
    """Gold publishes overview, ranks, shares, and hourly shares."""
    silver = silver_fixture(spark)
    overview = q5_overview(silver).first()
    assert overview["recorded_attempts"] == 10
    assert overview["approved_attempts"] == 9
    assert overview["denied_attempts"] == 1
    assert overview["approval_rate"] == 0.9

    cities = q5_cities(silver).orderBy("rank").collect()
    categories = q5_categories(silver).orderBy("rank").collect()
    hours = q5_hours(silver).collect()
    assert cities[0]["rank"] == 1
    assert abs(sum(row["approved_share"] for row in cities) - 1) < 1e-12
    assert abs(sum(row["approved_share"] for row in categories) - 1) < 1e-12
    assert abs(sum(row["approved_share"] for row in hours) - 1) < 1e-12
