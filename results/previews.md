# Bounded Gold previews

These rows are deterministic, bounded examples from the official Gold outputs. The complete tables are under `data/gold` and available in the Streamlit dashboard.

## Q1 - Top merchants for city 1 in January 2017

| Rank | Merchant ID | Merchant | Purchase total | Attempts |
|---:|---|---|---:|---:|
| 1 | M_ID_9139332ccc | Cesar Hall inc | 41,693,918.56 | 2,076 |
| 2 | M_ID_fc7d7969c3 | Mary Gray 7 inc | 24,014,489.66 | 1,206 |
| 3 | M_ID_e5374dabc0 | Kathie Sughrue inc | 22,636,281.61 | 1,131 |
| 4 | M_ID_86be58d7e0 | Steven Russell inc | 19,316,187.58 | 953 |
| 5 | M_ID_57df19bf28 | Maxine Flores inc | 15,509,700.97 | 756 |

## Q2 - Largest merchant/state arithmetic means

Each leading row has one attempt, so these values should not be interpreted as stable merchant performance.

| Merchant | State | Average amount | Attempts |
|---|---:|---:|---:|
| Martha Tyrrell inc | 7 | 39,937.61 | 1 |
| Julie Mckelvey inc | 9 | 39,727.59 | 1 |
| Jennifer Pool inc | 24 | 39,658.71 | 1 |
| Ileana Owens inc | 9 | 39,649.56 | 1 |
| Robert Mullins inc | 15 | 39,642.69 | 1 |

## Q3 - Top hours for categories A and B

| Category | Rank | Hour | Purchase total | Attempts |
|---|---:|---:|---:|---:|
| A | 1 | 12 | 5,731,975,337.46 | 285,046 |
| A | 2 | 13 | 5,648,608,300.81 | 281,070 |
| A | 3 | 17 | 5,473,251,727.35 | 272,176 |
| B | 1 | 13 | 4,303,909,949.93 | 214,372 |
| B | 2 | 12 | 4,154,695,164.46 | 206,848 |
| B | 3 | 14 | 4,088,684,407.39 | 203,286 |

## Q4 - Most popular merchants and observed cities

| Global rank | Merchant | City | City attempts | City rank | Global attempts |
|---:|---|---:|---:|---:|---:|
| 1 | M_ID_00a6ca8a8a | 69 | 264,587 | 1 | 279,377 |
| 1 | M_ID_00a6ca8a8a | 1 | 14,790 | 9 | 279,377 |
| 2 | Kathie Sughrue inc | 1 | 106,941 | 1 | 106,946 |
| 2 | Kathie Sughrue inc | 69 | 5 | 12,403 | 106,946 |
| 3 | Cesar Hall inc | 1 | 82,128 | 2 | 90,106 |
| 3 | Cesar Hall inc | 291 | 7,978 | 1 | 90,106 |

The full contingency table gives Cramer's V = 0.1810 for known cities and all retained categories.

## Official-run quality evidence

| Check | Result |
|---|---:|
| Silver rows | 7,274,367 |
| Reconciled Gold rows | 7,274,367 |
| Silver amount | 146,228,071,619.260000 |
| Reconciled Gold amount | 146,228,071,619.260000 |
| Ambiguous merchant IDs | 41 |
| Missing merchant IDs / unmatched lookups | 34,570 |
| Unknown categories retained | 44,625 |
| Denied attempts retained | 628,174 |
| Unknown installment values retained | 50 |
