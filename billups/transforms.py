"""Silver and Gold transformations for the Billups challenge."""

from __future__ import annotations

from dataclasses import dataclass

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType


MONEY = DecimalType(28, 6)
TRANSACTION_COLUMNS = {
    "merchant_id",
    "purchase_date",
    "purchase_amount",
    "city_id",
    "state_id",
    "category",
    "installments",
    "authorized_flag",
}
MERCHANT_COLUMNS = {"merchant_id", "merchant_name"}


@dataclass(frozen=True)
class SilverResult:
    transactions: DataFrame
    merchant_lookup: DataFrame
    merchant_conflicts: DataFrame


def require_columns(frame: DataFrame, required: set[str], source: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def build_merchant_lookup(merchants: DataFrame) -> tuple[DataFrame, DataFrame]:
    """Return one deterministic display name per merchant and conflict evidence."""
    require_columns(merchants, MERCHANT_COLUMNS, "merchant source")
    names = merchants.select(
        F.col("merchant_id"),
        F.when(F.length(F.trim(F.col("merchant_name"))) > 0, F.trim(F.col("merchant_name"))).alias(
            "clean_name"
        ),
    )
    grouped = names.groupBy("merchant_id").agg(
        F.sort_array(F.collect_set("clean_name")).alias("nonblank_names")
    )
    grouped = grouped.withColumn("distinct_name_count", F.size("nonblank_names"))
    conflicts = grouped.filter(F.col("distinct_name_count") > 1).select(
        "merchant_id", "nonblank_names", "distinct_name_count"
    )
    lookup = grouped.select(
        "merchant_id",
        F.when(F.col("merchant_id").isNull(), F.lit("Unknown merchant"))
        .when(F.col("distinct_name_count") == 1, F.element_at("nonblank_names", 1))
        .otherwise(F.col("merchant_id"))
        .alias("merchant_name"),
        (F.col("distinct_name_count") > 1).alias("merchant_name_ambiguous"),
        F.lit(True).alias("merchant_lookup_matched"),
    )
    return lookup, conflicts


def to_silver(transactions: DataFrame, merchants: DataFrame) -> SilverResult:
    """Validate, normalize and enrich transaction attempts without changing grain."""
    require_columns(transactions, TRANSACTION_COLUMNS, "transaction source")
    lookup, conflicts = build_merchant_lookup(merchants)

    parsed = transactions.withColumn(
        "purchase_timestamp", F.to_timestamp("purchase_date", "yyyy-MM-dd HH:mm:ss")
    ).withColumn("purchase_amount_decimal", F.col("purchase_amount").cast(MONEY))

    invalid = parsed.filter(
        F.col("purchase_timestamp").isNull()
        | F.col("purchase_amount_decimal").isNull()
        | F.isnan(F.col("purchase_amount").cast("double"))
    ).limit(1)
    if invalid.count():
        raise ValueError("transaction source contains an invalid/null date or non-finite/uncastable amount")

    normalized = (
        parsed.drop("purchase_date", "purchase_amount")
        .withColumnRenamed("purchase_timestamp", "purchase_date")
        .withColumnRenamed("purchase_amount_decimal", "purchase_amount")
        .withColumn(
            "category",
            F.when(
                F.col("category").isNull() | (F.length(F.trim(F.col("category"))) == 0),
                F.lit("Unknown category"),
            ).otherwise(F.col("category")),
        )
    )
    source_count = normalized.count()
    if source_count == 0:
        raise ValueError("transaction source is empty")
    enriched = normalized.join(F.broadcast(lookup), "merchant_id", "left").withColumn(
        "merchant_name",
        F.coalesce(
            "merchant_name",
            F.when(F.col("merchant_id").isNull(), F.lit("Unknown merchant")).otherwise(
                F.col("merchant_id")
            ),
        ),
    ).withColumn("merchant_name_ambiguous", F.coalesce("merchant_name_ambiguous", F.lit(False)))
    enriched = enriched.withColumn(
        "merchant_lookup_matched", F.coalesce("merchant_lookup_matched", F.lit(False))
    )
    if enriched.count() != source_count:
        raise ValueError("merchant enrichment changed transaction row count")
    return SilverResult(enriched, lookup, conflicts)


def _approved_amount() -> F.Column:
    return F.when(F.col("authorized_flag") == "Y", F.col("purchase_amount")).otherwise(
        F.lit(0).cast(MONEY)
    )


def q1_top_merchants(silver: DataFrame) -> DataFrame:
    monthly = silver.groupBy(
        F.date_format("purchase_date", "yyyy-MM").alias("year_month"),
        "city_id",
        "merchant_id",
        "merchant_name",
    ).agg(F.sum("purchase_amount").alias("total_amount"), F.count(F.lit(1)).alias("attempt_count"))
    rank = Window.partitionBy("year_month", "city_id").orderBy(
        F.desc("total_amount"), F.asc_nulls_last("merchant_id")
    )
    return monthly.withColumn("rank", F.row_number().over(rank)).filter(F.col("rank") <= 5)


def q2_merchant_state(silver: DataFrame) -> DataFrame:
    return silver.groupBy("merchant_id", "merchant_name", "state_id").agg(
        F.avg("purchase_amount").alias("average_amount"),
        F.count(F.lit(1)).alias("attempt_count"),
    ).orderBy(F.desc("average_amount"), F.asc_nulls_last("merchant_id"), F.asc_nulls_last("state_id"))


def q3_category_hours(silver: DataFrame) -> DataFrame:
    hourly = silver.groupBy("category", F.hour("purchase_date").alias("hour")).agg(
        F.sum("purchase_amount").alias("total_amount"), F.count(F.lit(1)).alias("attempt_count")
    )
    rank = Window.partitionBy("category").orderBy(F.desc("total_amount"), F.asc("hour"))
    return hourly.withColumn("rank", F.row_number().over(rank)).filter(F.col("rank") <= 3)


def q4_popular_merchants(silver: DataFrame, global_limit: int = 5) -> DataFrame:
    merchant_totals = silver.groupBy("merchant_id", "merchant_name").agg(
        F.count(F.lit(1)).alias("global_attempt_count")
    )
    global_rank = Window.orderBy(F.desc("global_attempt_count"), F.asc_nulls_last("merchant_id"))
    popular = merchant_totals.withColumn("global_rank", F.row_number().over(global_rank)).filter(
        F.col("global_rank") <= global_limit
    )
    by_city = silver.groupBy("city_id", "merchant_id", "merchant_name").agg(
        F.count(F.lit(1)).alias("city_attempt_count")
    )
    city_rank = Window.partitionBy("city_id").orderBy(
        F.desc("city_attempt_count"), F.asc_nulls_last("merchant_id")
    )
    return (
        by_city.withColumn("city_rank", F.row_number().over(city_rank))
        .join(popular, ["merchant_id", "merchant_name"], "inner")
        .select(
            "city_id",
            "merchant_id",
            "merchant_name",
            "city_attempt_count",
            "city_rank",
            "global_attempt_count",
            "global_rank",
        )
    )


def q4_city_category(silver: DataFrame) -> DataFrame:
    return silver.groupBy("city_id", "category").agg(F.count(F.lit(1)).alias("attempt_count"))


def _q5_dimension(silver: DataFrame, *dimensions: F.Column | str) -> DataFrame:
    return silver.groupBy(*dimensions).agg(
        F.sum("purchase_amount").alias("all_attempt_amount"),
        F.count(F.lit(1)).alias("all_attempt_count"),
        F.sum(_approved_amount()).alias("approved_amount"),
        F.sum(F.when(F.col("authorized_flag") == "Y", 1).otherwise(0)).alias("approved_count"),
    )


def q5_cities(silver: DataFrame) -> DataFrame:
    return _q5_dimension(silver, "city_id")


def q5_categories(silver: DataFrame) -> DataFrame:
    return _q5_dimension(silver, "category")


def q5_months(silver: DataFrame) -> DataFrame:
    return _q5_dimension(
        silver,
        F.date_format("purchase_date", "yyyy-MM").alias("year_month"),
    ).join(
        silver.groupBy(F.date_format("purchase_date", "yyyy-MM").alias("year_month")).agg(
            F.min(F.to_date("purchase_date")).alias("first_observed_date"),
            F.max(F.to_date("purchase_date")).alias("last_observed_date"),
            F.countDistinct(F.to_date("purchase_date")).alias("observed_days"),
        ),
        "year_month",
    ).withColumn(
        "approved_amount_per_observed_day", F.col("approved_amount") / F.col("observed_days")
    )


def q5_hours(silver: DataFrame) -> DataFrame:
    return _q5_dimension(silver, F.hour("purchase_date").alias("hour"))


def q5_installments(silver: DataFrame) -> DataFrame:
    modeled = (
        silver.withColumn(
            "plan_installments",
            F.when(F.col("installments").isin(0, 1), F.lit(1))
            .when((F.col("installments") >= 2) & (F.col("installments") != 999), F.col("installments"))
            .otherwise(F.lit(None).cast("long")),
        )
        .withColumn(
            "installment_plan",
            F.when(F.col("plan_installments").isNull(), F.lit("Unknown"))
            .when(F.col("plan_installments") == 1, F.lit("Baseline (0/1)"))
            .otherwise(F.concat(F.col("plan_installments"), F.lit(" payments"))),
        )
    )
    aggregated = _q5_dimension(modeled, "plan_installments", "installment_plan")
    probability = F.lit(1.0) - F.pow(F.lit(0.771), F.col("plan_installments"))
    return (
        aggregated.withColumn("monthly_default_probability", probability)
        .withColumn("flat_lifetime_default_probability", F.when(F.col("plan_installments").isNotNull(), F.lit(0.229)))
        .withColumn(
            "expected_profit_monthly",
            F.when(
                F.col("plan_installments").isNotNull(),
                F.col("approved_amount") * (F.lit(0.25) - F.lit(0.5) * probability),
            ),
        )
        .withColumn(
            "expected_profit_flat_lifetime",
            F.when(
                F.col("plan_installments").isNotNull(),
                F.col("approved_amount") * F.lit(0.1355),
            ),
        )
    )


def gold_frames(silver: DataFrame) -> dict[str, DataFrame]:
    return {
        "q1_top_merchants": q1_top_merchants(silver),
        "q2_merchant_state": q2_merchant_state(silver),
        "q3_category_hours": q3_category_hours(silver),
        "q4_popular_merchants": q4_popular_merchants(silver),
        "q4_city_category": q4_city_category(silver),
        "q5_cities": q5_cities(silver),
        "q5_categories": q5_categories(silver),
        "q5_months": q5_months(silver),
        "q5_hours": q5_hours(silver),
        "q5_installments": q5_installments(silver),
    }
