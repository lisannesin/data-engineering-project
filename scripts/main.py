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

    all_products = []

    for product in products:

        # Add normal product
        all_products.append(product)

        # Fetch variations if variable product
        if product.get("type") == "variable":

            variation_url = (
                f"{WC_URL}/products/{product['id']}/variations"
            )

            variation_response = requests.get(
                variation_url,
                auth=HTTPBasicAuth(
                    CONSUMER_KEY,
                    CONSUMER_SECRET
                ),
                timeout=30
            )

            variation_response.raise_for_status()

            variations = variation_response.json()

            for variation in variations:

                # Build variation name
                attributes = [
                    attr["option"]
                    for attr in variation.get("attributes", [])
                ]

                variation["name"] = (
                    f"{product['name']} - {' / '.join(attributes)}"
                )

                all_products.append(variation)

    logger.info(
        f"Fetched {len(all_products)} products and variations"
    )

    return all_products


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

            "stock_quantity": product.get("stock_quantity"),

            "product_status": product.get("status"),

            "stock_status": product.get("stock_status")

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

    mart_df["in_stock"] = mart_df["stock_status"].eq("instock")

    mart_df["inventory_status"] = mart_df["stock_status"].map({
        "instock": "In Stock",
        "outofstock": "Out of Stock",
        "onbackorder": "On Backorder"
    }).fillna("Unknown")

    return mart_df



def run_quality():

    logger.info("Running quality checks")

    with engine.begin() as conn:

        sql_path = "scripts/quality.sql"
        try:
            with open(sql_path, "r", encoding="utf-8") as file:
                sql = file.read()
        except FileNotFoundError:
            logger.error(f"Quality SQL file not found: {sql_path}")
            return

        # Split into statements and execute non-empty statements to avoid
        # database errors like "can't execute an empty query" when the file
        # contains trailing semicolons or blank lines.
        statements = [s.strip() for s in sql.split(";")]

        for stmt in statements:
            if not stmt:
                continue
            conn.execute(text(stmt))

        # Check that the results table was created before querying it.
        exists = conn.execute(
            text("SELECT to_regclass('quality.product_rule_results')")
        ).scalar()

        if not exists:
            logger.warning(
                "quality.product_rule_results does not exist after running quality SQL; skipping issues count."
            )
            issues = 0
        else:
            try:
                issues = conn.execute(
                    text("SELECT COUNT(*) FROM quality.product_rule_results")
                ).scalar()
            except Exception as e:
                logger.error(f"Error counting quality issues: {e}")
                issues = 0

    logger.info(
        f"Quality checks completed. "
        f"Found {issues} issues."
    )


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

        products = fetch_products()

        # RAW
        load_raw(products)

        # STG
        stg_df = transform_stg(products)
        load_stg(stg_df)

        # QUALITY
        run_quality()

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