# Billups historical transaction analysis

This report answers the five questions in the supplied case. A recorded attempt is every source row regardless of authorization; an approved attempt is a row with `authorized_flag = Y` and is the closer proxy for realized sales. The source has no unique transaction ID, so counts are attempts rather than deduplicated purchases.

## Q1 - Monthly top merchants by city

The complete `q1_top_merchants` Gold table answers every observed year-month and city. It ranks total recorded purchase amount, uses merchant ID as the deterministic tie-break, and retains repeated source rows. The first month/city result is shown below; the dashboard provides selectors for the complete answer.

| Rank | Month | City | Merchant | Purchase Total | No of Sales |
|---:|---|---:|---|---:|---:|
| 1 | Jan 2017 | 1 | Cesar Hall inc | $41,693,918.56 | 2,076 |
| 2 | Jan 2017 | 1 | Mary Gray 7 inc | $24,014,489.66 | 1,206 |
| 3 | Jan 2017 | 1 | Kathie Sughrue inc | $22,636,281.61 | 1,131 |
| 4 | Jan 2017 | 1 | Steven Russell inc | $19,316,187.58 | 953 |
| 5 | Jan 2017 | 1 | Maxine Flores inc | $15,509,700.97 | 756 |

## Q2 - Average amount by merchant and state

The table reports the arithmetic mean of recorded purchase amounts at merchant and transaction-state grain, with the largest averages first. Merchant ID remains in the internal aggregation grain so merchants sharing a display name do not collapse, but the requested published result contains only Merchant, State ID and Average Amount.

| Merchant | State ID | Average Amount |
|---|---:|---:|
| Martha Tyrrell inc | 7 | $39,937.61 |
| Julie Mckelvey inc | 9 | $39,727.59 |
| Jennifer Pool inc | 24 | $39,658.71 |
| Ileana Owens inc | 9 | $39,649.56 |
| Robert Mullins inc | 15 | $39,642.69 |

## Q3 - Top hours by category

The table contains the three hours with the largest total recorded purchase amount for each category. Unknown category represents source rows with a null or blank category and is retained for visible identification. Hours use the requested HH00 format; ascending hour breaks equal-amount ties.

| Category | Hour |
|---|---:|
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

## Q4 - Popular merchants and city/category association

Popularity is the number of recorded transaction attempts for each merchant, as specified by the challenge. The table shows the five most popular merchants globally and the cities where their attempts occurred.

| Global Rank | Merchant | City ID | City Transactions | City Rank | Global Transactions |
|---:|---|---:|---:|---:|---:|
| 1 | M_ID_00a6ca8a8a | 69 | 264,587 | 1 | 279,377 |
| 1 | M_ID_00a6ca8a8a | 1 | 14,790 | 9 | 279,377 |
| 2 | Kathie Sughrue inc | 1 | 106,941 | 1 | 106,946 |
| 2 | Kathie Sughrue inc | 69 | 5 | 12,403 | 106,946 |
| 3 | Cesar Hall inc | 1 | 82,128 | 2 | 90,106 |
| 3 | Cesar Hall inc | 291 | 7,978 | 1 | 90,106 |
| 4 | Todd Turner 3 inc | 69 | 45,912 | 2 | 45,912 |
| 5 | Mary Gray 7 inc | 1 | 44,075 | 3 | 44,075 |

Cramer's V for known cities is **0.1810**. This is a descriptive association between anonymized city and category, not evidence that location causes category demand. Unknown categories remain in the calculation; null and -1 city values are reported in Gold but excluded from this statistic.

## Q5 - Advice for a new merchant

### a. Cities

Prioritize the leading cities below for further validation because they have the largest approved historical amount. City IDs are anonymized, so operational feasibility still needs local context.

| City ID | Approved amount | Approved attempts | All-attempt amount |
|---:|---:|---:|---:|
| 69 | $22,534,479,504.01 | 1,121,660 | $24,268,306,863.20 |
| 1 | $10,172,285,699.57 | 505,956 | $12,984,064,000.16 |
| 19 | $5,365,029,696.65 | 266,403 | $5,797,239,502.75 |
| 158 | $5,155,170,570.99 | 256,544 | $5,601,443,762.82 |
| 17 | $4,579,284,169.04 | 227,768 | $4,875,605,419.84 |

### b. Categories

Use the leading approved-exposure categories as candidates for market research; historical amount alone does not establish margin or future demand.

| Category | Approved amount | Approved attempts | All-attempt amount |
|---|---:|---:|---:|
| A | $71,840,172,871.85 | 3,573,935 | $77,420,316,951.29 |
| B | $53,218,487,410.68 | 2,647,964 | $58,660,266,753.49 |
| C | $7,735,444,205.17 | 384,736 | $9,248,234,549.30 |
| Unknown category | $797,522,909.61 | 39,558 | $899,253,365.18 |

### c. Months

The dataset covers 14 months, with partial boundary months possible. Ranking below uses approved amount per observed date to avoid favoring months with more observed days. It does not establish recurring annual seasonality.

| Month | Observed dates | Days | Approved amount/day |
|---|---|---:|---:|
| 2017-12 | 2017-12-01 to 2017-12-31 | 31 | $504,976,522.32 |
| 2017-11 | 2017-11-01 to 2017-11-30 | 30 | $433,825,116.54 |
| 2018-01 | 2018-01-01 to 2018-01-31 | 31 | $426,211,985.46 |
| 2018-02 | 2018-02-01 to 2018-02-28 | 28 | $402,194,639.11 |
| 2017-10 | 2017-10-01 to 2017-10-31 | 31 | $373,270,755.42 |

### d. Hours

A deterministic smallest circular interval covering at least 80% of approved amount starts at **09:00** and closes at **22:00** after 13 hours (observed share 81.8%). This describes recorded demand. The source does not specify a timezone or operating costs, so it is not a profit-optimal schedule.

### e. Installments

The model treats values 0 and 1 as a one-payment baseline, n >= 2 except 999 as installment plans, and other values as unknown. Unknown values stay in Gold and are excluded from modeled profit. For n payments, cumulative default probability is 1 - 0.771^n. With 25% gross margin and 50% of value paid before default, expected profit is approved amount x (0.25 - 0.5 x probability). The flat-lifetime scenario applies 22.9% once. Half payment means half the transaction value, including odd installment counts.

| Plan | Approved exposure | All-attempt exposure | Monthly-default expected profit | Flat-lifetime expected profit |
|---|---:|---:|---:|---:|
| Unknown | $0.00 | $944,204.20 | Excluded | Excluded |
| Baseline (0/1) | $125,856,183,192.14 | $136,979,837,069.96 | $17,053,512,822.53 | $17,053,512,822.53 |
| 2 payments | $2,959,078,037.61 | $3,349,604,814.97 | $139,729,144.47 | $400,955,074.10 |
| 3 payments | $2,332,834,986.12 | $2,707,520,300.01 | -$48,623,266.79 | $316,099,140.62 |
| 4 payments | $737,696,053.20 | $898,203,620.32 | -$54,087,836.82 | $99,957,815.21 |
| 5 payments | $471,636,169.60 | $584,764,330.16 | -$53,662,612.69 | $63,906,700.98 |
| 6 payments | $514,149,799.99 | $660,874,202.89 | -$74,538,421.83 | $69,667,297.90 |
| 7 payments | $38,537,647.96 | $55,153,412.37 | -$6,513,828.15 | $5,221,851.30 |
| 8 payments | $70,452,447.16 | $100,143,943.63 | -$13,214,647.08 | $9,546,306.59 |
| 9 payments | $17,307,882.83 | $26,402,580.43 | -$3,493,858.78 | $2,345,218.12 |
| 10 payments | $413,231,105.28 | $588,215,815.88 | -$87,971,963.83 | $55,992,814.77 |
| 11 payments | $2,615,710.59 | $3,939,376.32 | -$579,083.50 | $354,428.78 |
| 12 payments | $177,904,364.83 | $272,467,948.12 | -$40,551,367.00 | $24,106,041.43 |

Under the requested monthly independent-default interpretation, two payments retain positive modeled expected profit while plans of three or more payments turn negative. Recommend at most two payments under these assumptions, then validate with actual repayment data. The flat-lifetime alternative remains positive and is shown because the wording can also be read as applying 22.9% once over the plan lifetime.

## Assumptions and data quality

Recommendations use approved attempts as the sales proxy and are based strictly on the historical transactions. Timestamps are interpreted as source wall time in a UTC-configured Spark session; the business timezone is unknown. Silver standardizes amounts to the supplied monetary units at decimal(28,2); dollar signs are presentation formatting because the true currency is unspecified. Layer load timestamps are technical metadata and are omitted from this report. The 14-month period cannot establish recurring annual seasonality. City and category IDs are anonymized. All authorization statuses, repeated attempts, unknown geography, nonpositive amounts and unknown installment counts are retained. Missing merchant names fall back to merchant ID; null merchant IDs use `Unknown merchant`; ambiguous merchant IDs also fall back to ID and are exported for review. The installment model assumes equal payments, a 25% gross margin, independent monthly 22.9% default probability, and 50% of transaction value paid before default; operating costs, repayment history and causal sales uplift are unavailable.
