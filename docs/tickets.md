# Tickets — $dtickets

Implement in order with `$dimplement T2`, then T3–T5. Use the spec as the source of truth. Each ticket is bounded enough for a smaller implementation model; escalate an unresolved business decision rather than inventing it.

## T1 — Skills and contracts [DONE]
Ten local skills validate with quick_validate.py. Discovery inspected the actual PDF, dictionary, source schema and full-column counts. User confirmed all attempts plus approved sensitivity; English-only repository and uv dependency management.

## T2 — Reliable Silver [DONE]
Depends on T1. Implement scripts/download_data.py, billups/transforms.py (Silver functions) and focused tests.
- Download the two official files into ignored data/raw using temporary files before rename.
- Require named columns; preserve source grain. Parse timestamps explicitly and purchase_amount as decimal(28,6).
- Collapse merchant metadata to one row per merchant_id. If more than one distinct nonblank name exists, use merchant_id and export ambiguity evidence. If none exists or join misses, use merchant_id; null IDs use Unknown merchant.
- Preserve all authorization statuses, unknown category and unknown geography.
- Evidence: hand-written fixtures for known/missing/ambiguous names, null category, repeated events, invalid amount/date, missing column and join row conservation.

Evidence: `tests/test_silver.py` passes all listed cases. The official Silver retained 7,274,367 attempts and exported 41 ambiguous merchant IDs.

## T3 — Exact Q1–Q3 [DONE]
Depends on T2. Add Gold transformations and tests.
- Q1 sums and counts per year-month/city/merchant, row_number top 5 with merchant ID tie-break. Group by ID as well as display name.
- Q2 arithmetic mean at merchant/state grain, descending mean.
- Q3 sum by category/hour, top 3 with ascending hour tie-break.
- Evidence: hand-computed amounts, averages, counts, six tied merchants and four tied hours; year boundary; two merchant IDs sharing a name remain separate.

Evidence: `tests/test_gold.py` passes the hand-computed sums, mean, counts, tie, year-boundary and shared-name cases. Official bounded rows are in `results/previews.md`.

## T4 — Q4/Q5 and analytical report [DONE]
Depends on T3. Implement remaining aggregates and billups/report.py.
- Q4 city/merchant popularity counts and city/category contingency; descriptive Cramer's V over known cities, unknown categories retained. Guard a zero denominator.
- Q5 city/category/month/hour aggregates contain all-attempt and approved counts/totals. Month output includes observed dates and exposure-normalized totals; do not infer repeated annual seasonality from 14 months.
- Use a deterministic smallest circular interval covering 80% of approved hourly amount; explain source timezone uncertainty and lack of operating-cost data.
- Installments: n>=2 and n!=999 are installment plans; 0/1 baseline; other invalid values unknown. p(n)=1-0.771^n. Expected profit=amount*(0.25-0.5*p); alternative lifetime p=0.229. Apply scenarios to approved exposure and show all-attempt exposure separately. For odd n, half payment means 50% value, not rounded payment count.
- Evidence: independent/associated contingency examples, a window crossing midnight, n=2 numeric example, negative expected profit at longer durations and unknown installment exclusion.

Evidence: `tests/test_report.py` and `tests/test_gold.py` pass these cases. The official report records Cramer's V 0.1810 and the 09:00-22:00 interval covering 81.8% of approved amount.

## T5 — Run, verify, document and publish [DONE]
Depends on T4. Add billups/pipeline.py and README.md.
- One documented uv run command overwrites Bronze/Silver/Gold, SHA-256 provenance, DQ JSON, report and bounded previews. Separate commands rebuild only Bronze, Silver or Gold.
- Validate nonempty input, date/amount casts, lookup uniqueness, row conservation and whole-population Gold count/amount reconciliation.
- Run synthetic end-to-end twice and compare business outputs; confirm the second trigger overwrites the first. Run the full official dataset.
- Apply spark-review, pipeline-review and simplify; record actual commands/results in docs/verification.md.
- Commit report and small previews under results/; exclude raw data and large generated data. Keep all text and commits in English. Push to the private GitHub remote and verify visibility.

Evidence: `docs/verification.md` records focused tests, two equal synthetic runs, standalone Bronze/Silver/Gold execution, failed-run marker behavior, the full official run, dashboard validation and all three review passes. Gold is 9.5 MB and committed for the dashboard; raw, Bronze, Silver and run outputs remain ignored. README documents download, full-pipeline and staged execution, and both dashboard paths.
