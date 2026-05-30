import os
import pandas as pd
import streamlit as st

from sqlalchemy import create_engine


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Stillform Dashboard",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Stillform Inventory Dashboard")


# ==========================================
# DATABASE CONNECTION
# ==========================================

engine = create_engine(
    f"postgresql://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/"
    f"{os.getenv('POSTGRES_DB')}"
)


# ==========================================
# LOAD DATA
# ==========================================

query = """
SELECT *
FROM mart.product_dashboard
"""

df = pd.read_sql(query, engine)


# ==========================================
# KPI SECTION
# ==========================================

total_products = len(df)

in_stock = int(df["in_stock"].sum())

out_of_stock = int((~df["in_stock"]).sum())


col1, col2, col3 = st.columns(3)

col1.metric(
    "Total Products",
    total_products
)

col2.metric(
    "In Stock",
    in_stock
)

col3.metric(
    "Out of Stock",
    out_of_stock
)


# ==========================================
# INVENTORY STATUS
# ==========================================

st.subheader("Inventory Status")

status_counts = (
    df["inventory_status"]
    .value_counts()
)

st.bar_chart(status_counts)


# ==========================================
# TOP PRODUCTS
# ==========================================

st.subheader("Top Products by Stock Quantity")

top_products = (
    df.sort_values(
        "stock_quantity",
        ascending=False
    )
    .head(10)
)

st.bar_chart(
    top_products.set_index(
        "product_name"
    )["stock_quantity"]
)


# ==========================================
# PRODUCT TABLE
# ==========================================

st.subheader("Product Overview")

st.dataframe(
    df,
    use_container_width=True
)