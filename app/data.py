"""Data layer: every page gets its data from here.

DATA_SOURCE = "databricks" -> live rpt_* tables through a SQL warehouse (Databricks App)
DATA_SOURCE = "files"      -> Parquet exports in app/data/ (Streamlit Community Cloud)
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

GOLD_SCHEMA = "workspace.sme_risk_gold"
DATA_DIR = Path(__file__).parent / "data"
DATA_SOURCE = os.getenv("DATA_SOURCE", "files")
# the 4M-row lookup is exported as several Parquet parts (each under GitHub's 100 MB limit)
LOOKUP_FILES = (DATA_DIR / "rpt_company_lookup" / "*.parquet").as_posix()


@st.cache_resource
def _duck():
    """DuckDB queries the Parquet files directly, so the 4M rows are never loaded into memory."""
    import duckdb

    return duckdb.connect()


@st.cache_resource
def _connection():
    """One SQL warehouse connection per app, using the app's service principal."""
    from databricks import sql
    from databricks.sdk.core import Config

    cfg = Config()
    host = cfg.host.replace("https://", "").replace("http://", "")
    return sql.connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
        credentials_provider=lambda: cfg.authenticate,
    )


def _query(sql_text: str, params: dict | None = None) -> pd.DataFrame:
    import pyarrow as pa

    with _connection().cursor() as cursor:
        cursor.execute(sql_text, params or {})
        table = cursor.fetchall_arrow()
    # ROUND() in Spark SQL returns DECIMAL, which pandas would hold as decimal.Decimal objects
    # (they don't mix with floats in arithmetic) -> convert every decimal column to float.
    for i, field in enumerate(table.schema):
        if pa.types.is_decimal(field.type):
            table = table.set_column(i, field.name, table.column(i).cast(pa.float64()))
    return table.to_pandas()


@st.cache_data(ttl=3600, show_spinner="Loading data...")
def load_report(name: str) -> pd.DataFrame:
    """Read a whole (small) report table, e.g. load_report("rpt_key_metrics")."""
    if DATA_SOURCE == "databricks":
        return _query(f"SELECT * FROM {GOLD_SCHEMA}.{name}")
    return pd.read_parquet(DATA_DIR / f"{name}.parquet")


@st.cache_data(ttl=3600, show_spinner="Looking up company...")
def lookup_company(acn: str) -> pd.DataFrame:
    """One company from rpt_company_lookup (ACN as 9-digit text)."""
    if DATA_SOURCE == "databricks":
        return _query(
            f"SELECT * FROM {GOLD_SCHEMA}.rpt_company_lookup WHERE acn = :acn",
            {"acn": acn},
        )
    return _duck().execute(
        f"SELECT * FROM read_parquet('{LOOKUP_FILES}') WHERE acn = ?", [acn]
    ).df()


@st.cache_data(ttl=3600, show_spinner="Loading data...")
def lending_tier_counts() -> pd.DataFrame:
    """Companies per lending tier and red flag (summary of rpt_company_lookup, ~10 rows)."""
    if DATA_SOURCE == "databricks":
        return _query(f"""
            SELECT lending_tier, lending_tier_order, red_flag,
                   borrower_segment = 'Trading company' AS is_trading,
                   COUNT(*) AS companies
            FROM {GOLD_SCHEMA}.rpt_company_lookup
            GROUP BY ALL
        """)
    return pd.read_parquet(DATA_DIR / "lending_tier_counts.parquet")


@st.cache_data(ttl=3600, show_spinner="Searching...")
def search_companies(name: str, limit: int = 25) -> pd.DataFrame:
    """Companies whose name contains the text (case-insensitive), current companies first."""
    cols = "acn, company_name, status_label, borrower_segment, lending_tier"
    if DATA_SOURCE == "databricks":
        return _query(
            f"""SELECT {cols} FROM {GOLD_SCHEMA}.rpt_company_lookup
                WHERE upper(company_name) LIKE '%' || upper(:name) || '%'
                ORDER BY status_label = 'Deregistered', company_name
                LIMIT {int(limit)}""",
            {"name": name},
        )
    return _duck().execute(
        f"""SELECT {cols} FROM read_parquet('{LOOKUP_FILES}')
            WHERE company_name ILIKE '%' || ? || '%'
            ORDER BY status_label = 'Deregistered', company_name
            LIMIT {int(limit)}""",
        [name],
    ).df()
