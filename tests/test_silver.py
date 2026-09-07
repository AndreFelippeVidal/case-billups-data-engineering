from __future__ import annotations

import pytest

from billups.transforms import to_silver


TX_COLUMNS = [
    "merchant_id",
    "purchase_date",
    "purchase_amount",
    "city_id",
    "state_id",
    "category",
    "installments",
    "authorized_flag",
]
TX_SCHEMA = "merchant_id string, purchase_date string, purchase_amount string, city_id long, state_id long, category string, installments long, authorized_flag string"


def transaction(merchant="m1", date="2017-01-01 10:00:00", amount="10.00", category="A"):
    return (merchant, date, amount, 1, 2, category, 1, "Y")


def test_silver_preserves_rows_and_resolves_names(spark):
    rows = [
        transaction("m1"),
        transaction("missing", category=None),
        transaction("ambiguous"),
        transaction(None),
        transaction("m1"),
    ]
    merchants = spark.createDataFrame(
        [("m1", "Known"), ("ambiguous", "Alpha"), ("ambiguous", "Beta"), ("blank", " ")],
        ["merchant_id", "merchant_name"],
    )
    result = to_silver(spark.createDataFrame(rows, TX_COLUMNS), merchants)
    actual = [row.asDict() for row in result.transactions.orderBy("merchant_id").collect()]
    assert len(actual) == len(rows)
    assert sum(row["merchant_id"] == "m1" for row in actual) == 2
    names = {row["merchant_id"]: row["merchant_name"] for row in actual}
    assert names["m1"] == "Known"
    assert names["missing"] == "missing"
    assert names["ambiguous"] == "ambiguous"
    assert names[None] == "Unknown merchant"
    assert next(row for row in actual if row["merchant_id"] == "missing")["category"] == "Unknown category"
    assert result.merchant_conflicts.first()["nonblank_names"] == ["Alpha", "Beta"]


@pytest.mark.parametrize(
    ("date", "amount"),
    [("not-a-date", "10"), ("2017-01-01 10:00:00", "not-money"), (None, "10")],
)
def test_silver_rejects_invalid_dates_and_amounts(spark, date, amount):
    tx = spark.createDataFrame([transaction(date=date, amount=amount)], TX_SCHEMA)
    merchants = spark.createDataFrame([("m1", "Known")], ["merchant_id", "merchant_name"])
    with pytest.raises(ValueError, match="invalid/null"):
        to_silver(tx, merchants)


def test_silver_requires_columns(spark):
    tx = spark.createDataFrame([("m1",)], ["merchant_id"])
    merchants = spark.createDataFrame([("m1", "Known")], ["merchant_id", "merchant_name"])
    with pytest.raises(ValueError, match="missing required columns"):
        to_silver(tx, merchants)


def test_silver_rejects_empty_transactions(spark):
    tx = spark.createDataFrame([], "merchant_id string, purchase_date string, purchase_amount string, city_id long, state_id long, category string, installments long, authorized_flag string")
    merchants = spark.createDataFrame([("m1", "Known")], ["merchant_id", "merchant_name"])
    with pytest.raises(ValueError, match="empty"):
        to_silver(tx, merchants)
