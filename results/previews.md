# Bounded Gold previews

These deterministic samples come from the generated Gold Parquet outputs.

## Q1 - Monthly top merchants by city

| Year Month | City Id | Merchant Id | Merchant Name | Total Amount | Attempt Count | Rank |
|---|---|---|---|---|---|---|
| 2017-01 | 1 | M_ID_9139332ccc | Cesar Hall inc | 41693918.56 | 2076 | 1 |
| 2017-01 | 1 | M_ID_fc7d7969c3 | Mary Gray 7 inc | 24014489.66 | 1206 | 2 |
| 2017-01 | 1 | M_ID_e5374dabc0 | Kathie Sughrue inc | 22636281.61 | 1131 | 3 |
| 2017-01 | 1 | M_ID_86be58d7e0 | Steven Russell inc | 19316187.58 | 953 | 4 |
| 2017-01 | 1 | M_ID_57df19bf28 | Maxine Flores inc | 15509700.97 | 756 | 5 |

## Q2 - Largest merchant/state averages

| Merchant Id | Merchant Name | State Id | Average Amount | Attempt Count |
|---|---|---|---|---|
| M_ID_816942a7a5 | Martha Tyrrell inc | 7 | 39937.61 | 1 |
| M_ID_2528f59982 | Julie Mckelvey inc | 9 | 39727.59 | 1 |
| M_ID_80672f91d5 | Jennifer Pool inc | 24 | 39658.71 | 1 |
| M_ID_c53f25cd23 | Ileana Owens inc | 9 | 39649.56 | 1 |
| M_ID_e510c1c618 | Robert Mullins inc | 15 | 39642.69 | 1 |

## Q3 - Leading category hours

| Category | Hour | Total Amount | Attempt Count | Rank |
|---|---|---|---|---|
| A | 12 | 5731975337.46 | 285046 | 1 |
| A | 13 | 5648608300.81 | 281070 | 2 |
| A | 17 | 5473251727.35 | 272176 | 3 |
| B | 13 | 4303909949.93 | 214372 | 1 |
| B | 12 | 4154695164.46 | 206848 | 2 |
| B | 14 | 4088684407.39 | 203286 | 3 |
| C | 17 | 811964558.29 | 40359 | 1 |
| C | 16 | 806582348.55 | 40093 | 2 |
| C | 15 | 787244694.65 | 39183 | 3 |
| Unknown category | 0 | 229942343.47 | 11434 | 1 |
| Unknown category | 14 | 65060353.20 | 3226 | 2 |
| Unknown category | 13 | 64525934.04 | 3140 | 3 |

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

## Reconciliation

Silver and Gold reconcile at 7,274,367 rows and 146228071619.260000 total amount.
