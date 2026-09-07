# Data specification — $dspec

## Contracts and grain
Bronze preserves both source datasets, with an input SHA-256 manifest. Silver is one row per input transaction attempt enriched through a many-to-one merchant-name lookup. Required transaction columns: merchant_id, purchase_date, purchase_amount, city_id, state_id, category, installments, authorized_flag. Required merchant columns: merchant_id, merchant_name.

Fail on absent columns, invalid/null timestamp or non-finite/uncastable amount, join fan-out, empty transaction input or failed reconciliation. Resolve conflicting merchant names to merchant_id and export the conflict lookup for inspection. Warn and measure missing merchant IDs, unmatched lookups, unknown categories, unknown geography, denied/unknown authorization, nonpositive amount and unknown installment counts. Preserve these records. Do not deduplicate transaction attempts. Money is decimal(28,6); identifiers keep their source values; -1 geography is an unknown sentinel.

## Gold acceptance criteria
| Output | Grain / criterion |
|---|---|
| q1_top_merchants | Month × transaction city × merchant; sum amount, count, exact top 5 per month/city; amount descending, merchant_id ascending ties |
| q2_merchant_state | Merchant × transaction state; arithmetic mean per attempt, count; mean descending |
| q3_category_hours | Category × hour; sum amount and count, exact top 3 hours per category; hour ascending ties |
| q4_popular_merchants | City × merchant; counts and city rank; top global merchants shown across their cities |
| q4_city_category | City × category counts, used for descriptive Cramer's V with unknown geography separately excluded from that statistic |
| q5_cities / categories / months / hours | Aggregate purchase totals, counts, approved totals and counts; compare all attempts vs approved |
| q5_installments | Installment count; aggregate exposure, default probability, expected profit under monthly and flat lifetime scenarios, unknown exclusions |

Use year-month to avoid combining different years. Month trends report exposure days and note partial boundary months. A recommended opening interval captures at least 80% of approved amount using a contiguous circular hour window; this describes observed demand, not optimal profitability. Q5 cities/categories use approved totals with all-record comparison; IDs are anonymized. Monetary recommendations and installment outcomes are illustrative given missing costs, causal uplift and true currency.

## Reproducibility
Each trigger is a deterministic local full refresh: raw inputs remain untouched while Bronze, Silver, Gold, report and previews are overwritten. Individual stage commands rebuild only their owned layer and require their upstream dataset paths. Identical inputs must yield identical business results. Commit Gold for direct dashboard review; keep raw, Bronze and Silver local and ignored.
