import os
import json
import logging
import requests
import pandas as pd

from requests.auth import HTTPBasicAuth
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ==================================================
# LOGGING
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ==================================================
# ENV VARIABLES
# ==================================================

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")

WC_URL = os.getenv("WC_API_URL")
CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")


# ==================================================
# DATABASE CONNECTION
# ==================================================

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ==================================================
# FETCH PRODUCTS FROM WOOCOMMERCE API
# ==================================================

def fetch_products():

    logger.info("Fetching WooCommerce products")

    url = f"{WC_URL}/products"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(
            CONSUMER_KEY,
            CONSUMER_SECRET
        ),
        timeout=30
    )

    response.raise_for_status()

    products = response.json()

    logger.info(f"Fetched {len(products)} products")

    return products


# ==================================================
# LOAD RAW JSON
# ==================================================

def load_raw(products):

    logger.info("Loading RAW layer")

    with engine.begin() as conn:

        for product in products:

            conn.execute(
                text("""
                    INSERT INTO raw.products_raw (
                        loaded_at,
                        payload
                    )
                    VALUES (
                        NOW(),
                        CAST(:payload AS JSONB)
                    )
                """),
                {
                    "payload": json.dumps(product)
                }
            )

    logger.info("RAW layer loaded")


# ==================================================
# TRANSFORM TO STG
# ==================================================

def transform_stg(products):

    logger.info("Transforming STG layer")

    rows = []

    for product in products:

        rows.append({

            "product_id": product.get("id"),

            "product_name": product.get("name"),

            "sku": product.get("sku"),

            "stock_quantity": product.get("stock_quantity")

        })

    stg_df = pd.DataFrame(rows)

    stg_df["stock_quantity"] = (
        pd.to_numeric(
            stg_df["stock_quantity"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    stg_df["loaded_at"] = pd.Timestamp.now()

    return stg_df


# ==================================================
# LOAD STG
# ==================================================

def load_stg(stg_df):

    logger.info("Loading STG layer")

    stg_df.to_sql(
        "products",
        engine,
        schema="stg",
        if_exists="replace",
        index=False
    )

    logger.info("STG layer loaded")


# ==================================================
# BUILD MART
# ==================================================

def transform_mart(stg_df):

    logger.info("Building MART layer")

    mart_df = stg_df.copy()

    mart_df["in_stock"] = (
        mart_df["stock_quantity"] > 0
    )

    mart_df["inventory_status"] = mart_df[
        "stock_quantity"
    ].apply(
        lambda x: "Out of Stock"
        if x == 0
        else "In Stock"
    )

    return mart_df


# ==================================================
# LOAD MART
# ==================================================

def load_mart(mart_df):

    logger.info("Loading MART layer")

    mart_df.to_sql(
        "product_dashboard",
        engine,
        schema="mart",
        if_exists="replace",
        index=False
    )

    logger.info("MART layer loaded")


# ==================================================
# MAIN PIPELINE
# ==================================================

def main():

    try:

        logger.info("Pipeline started")

        # EXTRACT
        products = fetch_products()

        # RAW
        load_raw(products)

        # STG
        stg_df = transform_stg(products)
        load_stg(stg_df)

        # MART
        mart_df = transform_mart(stg_df)
        load_mart(mart_df)

        logger.info("Pipeline completed successfully")

    except requests.exceptions.RequestException as e:

        logger.error(f"API error: {e}")

    except SQLAlchemyError as e:

        logger.error(f"Database error: {e}")

    except Exception as e:

        logger.error(f"Unexpected error: {e}")


# ==================================================
# ENTRYPOINT
# ==================================================

if __name__ == "__main__":
    main()