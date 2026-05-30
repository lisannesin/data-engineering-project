import os
import requests
import psycopg2
from requests.auth import HTTPBasicAuth

WC_URL = os.environ["WC_API_URL"]
WC_KEY = os.environ["WC_CONSUMER_KEY"]
WC_SECRET = os.environ["WC_CONSUMER_SECRET"]

conn = psycopg2.connect(
    host=os.environ["DB_HOST"],
    port=os.environ["DB_PORT"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    dbname=os.environ["DB_NAME"]
)

response = requests.get(
    f"{WC_URL}/products",
    auth=HTTPBasicAuth(WC_KEY, WC_SECRET),
    timeout=30
)

products = response.json()

UPSERT_SQL = """
INSERT INTO raw.products (
    id,
    name,
    sku,
    price,
    stock_quantity,
    stock_status,
    manage_stock,
    created_at
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)

ON CONFLICT (id)
DO UPDATE SET
    name = EXCLUDED.name,
    sku = EXCLUDED.sku,
    price = EXCLUDED.price,
    stock_quantity = EXCLUDED.stock_quantity,
    stock_status = EXCLUDED.stock_status,
    manage_stock = EXCLUDED.manage_stock;
"""

with conn.cursor() as cur:

    for product in products:

        cur.execute(
            UPSERT_SQL,
            (
                product["id"],
                product["name"],
                product.get("sku"),
                product.get("price") or 0,
                product.get("stock_quantity"),
                product.get("stock_status"),
                product.get("manage_stock"),
                product.get("date_created"),
            )
        )

conn.commit()

print(f"Loaded {len(products)} products")