CREATE SCHEMA IF NOT EXISTS quality;

DROP TABLE IF EXISTS quality.product_rule_results;
DROP TABLE IF EXISTS quality.product_issue_summary;

CREATE TABLE quality.product_rule_results AS

SELECT
    product_id,
    'missing_product_id' AS rule_name
FROM stg.products
WHERE product_id IS NULL

UNION ALL

SELECT
    product_id,
    'negative_stock'
FROM stg.products
WHERE stock_quantity < 0

UNION ALL

SELECT
    product_id,
    'invalid_product_status'
FROM stg.products
WHERE product_status NOT IN (
    'publish',
    'draft',
    'pending',
    'private'
)

UNION ALL

SELECT
    product_id,
    'invalid_stock_status'
FROM stg.products
WHERE stock_status NOT IN (
    'instock',
    'outofstock',
    'onbackorder'
)

UNION ALL

SELECT
    product_id,
    'duplicate_product_id'
FROM stg.products
GROUP BY product_id
HAVING COUNT(*) > 1;