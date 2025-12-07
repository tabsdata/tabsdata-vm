import tabsdata as td
import polars as pl
import requests
import io
import re
import datetime as dt


@td.transformer(
    input_tables=["claims_fact_master_enriched"],
    output_tables=[
        "open_pending_claims",
        "claims_last_90_days",
        "paid_amount_greater_10000",
    ],
)
def master_categorize_trf(claims_fact_master: td.TableFrame):
    open_pending_claims = claims_fact_master.filter(td.col("claim_status") == "Open")

    claims_last_90_days = claims_fact_master.with_columns(
        (td.lit(dt.date.today()).cast(td.Date) - td.col("date_reported").cast(td.Date))
        .dt.total_days()
        .alias("days_since_reported")
    )
    claims_last_90_days = claims_last_90_days.filter(
        td.col("days_since_reported") <= 90
    )
    paid_amount_greater_10000 = claims_fact_master.filter(td.col("paid_amount") > 10000)

    return open_pending_claims, claims_last_90_days, paid_amount_greater_10000
