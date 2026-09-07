# Discovery — $grill-me and $model

## Evidence
The original Billups PDF requires five analytical answers, Python/PySpark functions, code and a report. Source links are recorded in the download script. The dictionary defines merchant_id, merchant_name, category, installments and authorized_flag (Y approved, N denied). Transaction Parquet has 7,274,367 rows, 12 columns and no unique event ID. Merchant CSV has 22 columns.

## Decisions and recommendations
- Use local batch full refresh, Python 3.12, Java 17 and PySpark 3.5.6. Spark is a requirement, not a scale-driven technology choice.
- Simulate Bronze/Silver/Gold with Parquet, as requested. No Databricks deployment is needed.
- One source row is one recorded transaction attempt; preserve repeated rows because no event identifier supports deduplication.
- User confirmed: main answers include all authorization statuses; Q5 also compares approved records. Recorded purchase amounts are not realized revenue.
- Use transaction city/state for where activity happened. Merchant metadata enriches only the name; a merchant can appear in several cities.
- Resolve identical merchant ID/name duplicates to one lookup entry; use the ID as display name for conflicting nonempty names and export the conflicting lookup records. This prevents join fan-out without arbitrarily choosing a name.
- Normalize blank/null category to Unknown category. Retain missing merchants and fallback to merchant_id; a null merchant ID gets Unknown merchant.
- Treat naive timestamps as source wall time with a UTC Spark session to avoid machine-specific behavior; the dictionary provides no business timezone.
- Treat purchase_amount as the supplied monetary units, preserving six decimal places for aggregation; do not infer a currency.
- Rank exact top N with deterministic ID/hour ties. Rank Q1 by sum, Q2 by mean, Q3 by sum.
- For Q4 use transaction count, a city/category contingency table and Cramer's V, not Pearson correlation between arbitrary IDs. This is descriptive association, not causation.
- Q5 installment scenario: monthly independent default hazard 0.229 over n payments, lifetime probability 1-(1-0.229)^n, recovery 50%, cost 75%, expected profit rate 0.25-0.5*p. Show alternative flat 22.9% lifetime assumption to expose ambiguity. Zero/one payments are non-installment baseline; negative, null and 999 are unknown/sentinel, excluded only from the model. No causal claim about incremental sales.
- Keep the repository private as explicitly requested, although the brief asks for public submission. User can change visibility before submission. No recruiter message is authorized.

## Scope control
Two days: data contracts and one batch pipeline, focused tests, measured quality, five answers and a readable report. No orchestration service, generic framework, streaming, cloud provisioning, dashboards or predictive model.

## Profile-driven adjustment before implementation
Merchant source: 334,696 rows, 334,633 distinct IDs, 41 IDs with conflicting names. Fail-on-conflict would block this real dataset; use ID fallback for ambiguity, expose the conflict table and warn. Transactions include 34,570 null merchant IDs, 44,625 null categories, 628,174 denied attempts and 50 installment=999 records. Date coverage is 2017-01-01 through 2018-02-28. These are preserved with measured caveats. Dependency management uses uv and uv.lock, as requested.
