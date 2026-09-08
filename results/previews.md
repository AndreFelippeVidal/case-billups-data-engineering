# Bounded Gold previews

These deterministic samples come from the generated Gold Parquet outputs.

## Q1 - Monthly top merchants by city

| Rank | Year Month | City Id | Merchant Id | Merchant Name | Total Amount | Attempt Count |
|---|---|---|---|---|---|---|
| 1 | 2017-01 | 1 | M_ID_9139332ccc | Cesar Hall inc | 41693918.56 | 2076 |
| 2 | 2017-01 | 1 | M_ID_fc7d7969c3 | Mary Gray 7 inc | 24014489.66 | 1206 |
| 3 | 2017-01 | 1 | M_ID_e5374dabc0 | Kathie Sughrue inc | 22636281.61 | 1131 |
| 4 | 2017-01 | 1 | M_ID_86be58d7e0 | Steven Russell inc | 19316187.58 | 953 |
| 5 | 2017-01 | 1 | M_ID_57df19bf28 | Maxine Flores inc | 15509700.97 | 756 |

## Q2 - Largest merchant/state averages

| Merchant | State Id | Average Amount |
|---|---|---|
| Martha Tyrrell inc | 7 | 39937.61 |
| Julie Mckelvey inc | 9 | 39727.59 |
| Jennifer Pool inc | 24 | 39658.71 |
| Ileana Owens inc | 9 | 39649.56 |
| Robert Mullins inc | 15 | 39642.69 |

## Q3 - Leading category hours

| Category | Hour |
|---|---|
| A | 1200 |
| A | 1300 |
| A | 1700 |
| B | 1300 |
| B | 1200 |
| B | 1400 |
| C | 1700 |
| C | 1600 |
| C | 1500 |
| Unknown category | 0000 |
| Unknown category | 1400 |
| Unknown category | 1300 |

## Q4 - Popular merchants across cities

| City Id | Merchant Id | Merchant Name | City Attempt Count | City Rank | Global Attempt Count | Global Rank |
|---|---|---|---|---|---|---|
| 69 | M_ID_00a6ca8a8a | M_ID_00a6ca8a8a | 264587 | 1 | 279377 | 1 |
| 1 | M_ID_00a6ca8a8a | M_ID_00a6ca8a8a | 14790 | 9 | 279377 | 1 |
| 1 | M_ID_e5374dabc0 | Kathie Sughrue inc | 106941 | 1 | 106946 | 2 |
| 69 | M_ID_e5374dabc0 | Kathie Sughrue inc | 5 | 12403 | 106946 | 2 |
| 1 | M_ID_9139332ccc | Cesar Hall inc | 82128 | 2 | 90106 | 3 |
| 291 | M_ID_9139332ccc | Cesar Hall inc | 7978 | 1 | 90106 | 3 |
| 69 | M_ID_50f575c681 | Todd Turner 3 inc | 45912 | 2 | 45912 | 4 |
| 1 | M_ID_fc7d7969c3 | Mary Gray 7 inc | 44075 | 3 | 44075 | 5 |

## Q4 - City and category association

| Population | City Count | Category Count | Chi Square | Cramers V |
|---|---|---|---|---|
| 7274367 | 307 | 4 | 715162.1252112323 | 0.18102727824466436 |

## Q5 - Business overview

| Recorded Amount | Recorded Attempts | Approved Amount | Approved Attempts | Approval Rate |
|---|---|---|---|---|
| 146228071619.26 | 7274367 | 133591627397.31 | 6646193 | 0.91364554469138 |

## Q5 - Recommended opening interval

| Start Hour | End Hour | Hours | Covered Amount | Share | Target Share |
|---|---|---|---|---|---|
| 9 | 22 | 13 | 109325799014.88 | 0.818358164690502 | 0.8 |

## Reconciliation

Silver and Gold reconcile at 7,274,367 rows and 146228071619.26 total amount.
