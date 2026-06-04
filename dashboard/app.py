import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from sqlalchemy import create_engine


# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Stillform Dashboard",
    layout="wide"
)

st.title("Stillform Inventory Dashboard")


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

df["product_status"] = df["product_status"].fillna("unknown")
df["stock_status"] = df["stock_status"].fillna("unknown")
df["stock_quantity"] = pd.to_numeric(
    df["stock_quantity"],
    errors="coerce"
).fillna(0)

# ==========================================
# KPI SECTION
# ==========================================

total_products = len(df)

in_stock = int(
    (df["stock_status"] == "instock").sum()
)

out_of_stock = int(
    (df["stock_status"] == "outofstock").sum()
)

on_backorder = int(
    (df["stock_status"] == "onbackorder").sum()
)

published_products = int(
    (df["product_status"] == "publish").sum()
)

total_stock_units = int(
    df["stock_quantity"].sum()
)


col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Products", total_products)
col2.metric("In Stock", in_stock)
col3.metric("Out of Stock", out_of_stock)
col4.metric("On Backorder", on_backorder)
col5.metric("Total Stock Units", total_stock_units)


# ==========================================
# INVENTORY HEALTH GAUGE
# ==========================================

st.subheader("Inventory Health Score")

if total_products > 0:
    inventory_health = round(
        in_stock / total_products * 100,
        1
    )
else:
    inventory_health = 0

fig_gauge = go.Figure(
    go.Indicator(
        mode="gauge+number",
        value=inventory_health,
        title={"text": "Products Available (%)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "darkblue"},
            "steps": [
                {"range": [0, 40], "color": "#ffcccc"},
                {"range": [40, 70], "color": "#fff2cc"},
                {"range": [70, 100], "color": "#d9ead3"}
            ]
        }
    )
)

st.plotly_chart(
    fig_gauge,
    use_container_width=True
)


# ==========================================
# MAIN VISUALS
# ==========================================

col_left, col_right = st.columns(2)


# ==========================================
# STOCK STATUS DONUT
# ==========================================

with col_left:

    st.subheader("Stock Status Distribution")

    stock_status_counts = (
        df["stock_status"]
        .value_counts()
        .reset_index()
    )

    stock_status_counts.columns = [
        "stock_status",
        "count"
    ]

    fig_stock = px.pie(
        stock_status_counts,
        names="stock_status",
        values="count",
        hole=0.45
    )

    st.plotly_chart(
        fig_stock,
        use_container_width=True
    )


# ==========================================
# PRODUCT STATUS BAR CHART
# ==========================================

with col_right:

    st.subheader("Product Status Distribution")

    product_status_counts = (
        df["product_status"]
        .value_counts()
        .reset_index()
    )

    product_status_counts.columns = [
        "product_status",
        "count"
    ]

    fig_product_status = px.bar(
        product_status_counts,
        x="product_status",
        y="count",
        text="count"
    )

    fig_product_status.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig_product_status,
        use_container_width=True
    )


# ==========================================
# STOCK QUANTITY DISTRIBUTION
# ==========================================

st.subheader("Stock Quantity Distribution")

bins = [-1, 0, 5, 20, 50, float("inf")]
labels = [
    "0 units",
    "1-5 units",
    "6-20 units",
    "21-50 units",
    "50+ units"
]

df["stock_range"] = pd.cut(
    df["stock_quantity"],
    bins=bins,
    labels=labels
)

stock_range_counts = (
    df["stock_range"]
    .value_counts()
    .reindex(labels)
    .reset_index()
)

stock_range_counts.columns = [
    "stock_range",
    "count"
]

fig_stock_range = px.bar(
    stock_range_counts,
    x="stock_range",
    y="count",
    text="count"
)

fig_stock_range.update_traces(
    textposition="outside"
)

st.plotly_chart(
    fig_stock_range,
    use_container_width=True
)


# ==========================================
# PRODUCT STATUS VS STOCK STATUS MATRIX
# ==========================================

st.subheader("Product Status vs Stock Status")

status_matrix = pd.crosstab(
    df["product_status"],
    df["stock_status"]
)

fig_matrix = px.imshow(
    status_matrix,
    text_auto=True,
    aspect="auto"
)

st.plotly_chart(
    fig_matrix,
    use_container_width=True
)


# ==========================================
# TOP PRODUCTS BY STOCK QUANTITY
# ==========================================

st.subheader("Top 10 Products by Stock Quantity")

top_products = (
    df.sort_values(
        "stock_quantity",
        ascending=False
    )
    .head(10)
)

fig_top_products = px.bar(
    top_products,
    x="stock_quantity",
    y="product_name",
    orientation="h",
    text="stock_quantity"
)

fig_top_products.update_layout(
    yaxis={"categoryorder": "total ascending"}
)

st.plotly_chart(
    fig_top_products,
    use_container_width=True
)


# ==========================================
# LOW STOCK PRODUCTS
# ==========================================

st.subheader("Low Stock Products")

low_stock_threshold = st.slider(
    "Low stock threshold",
    min_value=1,
    max_value=50,
    value=5
)

low_stock_df = (
    df[
        (df["stock_quantity"] > 0)
        & (df["stock_quantity"] <= low_stock_threshold)
    ]
    .sort_values("stock_quantity")
)

st.dataframe(
    low_stock_df[
        [
            "product_name",
            "sku",
            "stock_quantity",
            "product_status",
            "stock_status"
        ]
    ],
    use_container_width=True
)


# ==========================================
# PRODUCT OVERVIEW TABLE
# ==========================================

st.subheader("Product Overview")

display_columns = [
    "product_id",
    "product_name",
    "sku",
    "stock_quantity",
    "product_status",
    "stock_status",
    "inventory_status",
    "in_stock",
    "loaded_at"
]

available_columns = [
    col for col in display_columns
    if col in df.columns
]

st.dataframe(
    df[available_columns],
    use_container_width=True
)