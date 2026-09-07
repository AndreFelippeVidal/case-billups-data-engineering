# Implementation plan — $dplan

Day 1 (up to 8 hours): inspect source data and settle contracts (1h); build explicit Silver and Gold transformations with hand-computable tests (3h); add a local batch runner and measured DQ (2h); run all real data and inspect results (2h).

Day 2 (up to 8 hours): answer Q4/Q5 with limitations (2h); verify rerun and failure cases (2h); simplify and document setup/report (2h); final review and private GitHub delivery with contingency (2h).

Files: billups/transforms.py owns Silver and Gold logic; billups/pipeline.py owns local reads, persistence and quality evidence; billups/report.py renders bounded aggregate findings; scripts/download_data.py fetches the official inputs; tests/ verifies semantics and reruns. Dependencies are PySpark for required processing and pytest for test execution. Use the standard library for downloads, manifests and reports.

Sequence: preserve raw → Bronze → validate/normalize Silver → Gold for Q1–Q5 → reconcile → report and SUCCESS marker. Review joins, windows, nulls and installment formulas before full execution. Reuse persisted Silver for repeated Gold queries. No additional platform or generic abstractions.
