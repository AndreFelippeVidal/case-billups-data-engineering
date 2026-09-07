# Source references

The original challenge was recovered from the user-provided PDF, `BIL-006 · Sr Data Engineer – Python Spark (7).pdf`. The links below are embedded in that PDF. Accessed September 7, 2026.

- [Data dictionary](https://docs.google.com/spreadsheets/d/1k05tl92SY5CvEwa0-nFOQMOjkLgZOL9qTXsDsh0F-_Q/edit)
- [Historical transactions Parquet](https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/interview_historical_transactions.parquet/part-00000-tid-860771939793626614-979f966a-6d53-4896-9692-f81194d27b99-109986-1-c000.snappy.parquet)
- [Merchant CSV](https://billups-tech-interview.s3.us-west-2.amazonaws.com/engineering/data-engineering-task/merchants-subset.csv)
- [PySpark 3.5.6 installation and Java compatibility](https://spark.apache.org/docs/3.5.6/api/python/getting_started/install.html)

## Dictionary fields used
merchant_id is the merchant identifier; merchant_name is an anonymized display name. city_id and state_id identify anonymized geography. purchase_date is the purchase date; purchase_amount is the purchase amount with no specified currency. category is an anonymized product category, distinct from merchant_category_id. installments is the number of purchase installments. authorized_flag is Y for approved and N for denied. customer_id identifies a customer, not a unique transaction.

## Required questions
1. Top five merchants by total purchase_amount per month and city, with number of sales.
2. Average purchase_amount by merchant and state, largest averages first.
3. Top three hours by total purchase_amount for each category.
4. Cities of popular merchants, defining popularity by transaction count, and association between city and category.
5. Advice for a new merchant: cities, categories, interesting months, opening/closing hours and installment acceptance. For installments use a 22.9% monthly default rate, equal installments, 25% gross margin and 50% payment before default; state assumptions.

Missing merchant names must fall back to merchant_id. Null categories must be retained. Use Python with the PySpark interface, preferably DataFrame functions over Spark SQL. Deliver code and an analytical report. The PDF sets a 96-hour deadline from receipt; the user's remaining delivery budget is two days.
