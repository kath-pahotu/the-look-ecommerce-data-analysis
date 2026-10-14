-- =====================================================================
-- 00_raw_quality.sql
-- Source-level quality gate. Runs immediately after ingestion and BEFORE
-- any staging, dimension, fact or mart is built.
--
-- Why this file exists separately from 07:
--   Every check in 07 needs a modelled table to compare against, so it
--   cannot run until the warehouse is built. These checks need nothing but
--   the raw tables, so there is no reason to build 26 marts on data that
--   has not passed them. A failure here stops the build before any
--   downstream object exists, and before anything is exported.
--
-- Scope rule: a check belongs here only if it can be answered from the
-- `raw` schema alone. Anything that compares layers belongs in 07 or 09.
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS qa;

CREATE OR REPLACE TABLE qa.raw_test_results AS
WITH checks AS (
    -- ---------------------------------------------------------------
    -- Primary keys. A duplicate here multiplies rows through every join
    -- downstream, so it has to be caught before any join happens.
    -- ---------------------------------------------------------------
    SELECT 'users_primary_key_unique' AS check_name, 'raw' AS layer, 'CRITICAL' AS severity,
           COUNT(*)::BIGINT AS failure_count, (SELECT COUNT(*) FROM raw.users)::BIGINT AS denominator,
           1 AS blocking, 'users.id must be unique' AS notes
    FROM (SELECT id FROM raw.users GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'products_primary_key_unique', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM raw.products), 1, 'products.id must be unique'
    FROM (SELECT id FROM raw.products GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'orders_primary_key_unique', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM raw.orders), 1, 'orders.order_id must be unique'
    FROM (SELECT order_id FROM raw.orders GROUP BY order_id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'order_items_primary_key_unique', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM raw.order_items), 1, 'order_items.id must be unique'
    FROM (SELECT id FROM raw.order_items GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    SELECT 'events_primary_key_unique', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM raw.events), 1, 'events.id must be unique'
    FROM (SELECT id FROM raw.events GROUP BY id HAVING COUNT(*) > 1)
    UNION ALL
    -- ---------------------------------------------------------------
    -- The session grain is derived by grouping on session_id. A blank one
    -- would silently create a phantom session, so the column has to be
    -- populated before sessionization is attempted at all.
    -- ---------------------------------------------------------------
    SELECT 'events_session_id_present', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(*) FROM raw.events), 1,
           'Every event must have a nonblank session_id before sessionization'
    FROM raw.events
    WHERE session_id IS NULL OR TRIM(CAST(session_id AS VARCHAR)) = ''
    UNION ALL
    -- ---------------------------------------------------------------
    -- Reference-data coverage. These two catch the condition that would
    -- otherwise appear as a silently missing market or an unconverted
    -- plan row: a value in the source that the seed does not know about.
    -- ---------------------------------------------------------------
    SELECT 'country_master_covers_source', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(DISTINCT country) FROM raw.users WHERE country IS NOT NULL), 1,
           'Every country spelling in users.csv must map to a canonical market'
    FROM (SELECT DISTINCT country FROM raw.users WHERE country IS NOT NULL) u
    LEFT JOIN raw.country_master m ON u.country = m.source_country_value
    WHERE m.source_country_value IS NULL
    UNION ALL
    SELECT 'fx_rates_cover_plan_currencies', 'raw', 'CRITICAL', COUNT(*),
           (SELECT COUNT(DISTINCT currency_code) FROM raw.plan_submissions), 1,
           'Every currency in the plan file must have a budget FX rate'
    FROM (SELECT DISTINCT UPPER(TRIM(currency_code)) AS currency_code
          FROM raw.plan_submissions) p
    LEFT JOIN raw.fx_budget_rates f ON p.currency_code = f.currency_code
    WHERE f.currency_code IS NULL
    UNION ALL
    -- ---------------------------------------------------------------
    -- Known source conditions. Reported every build, never blocking.
    -- ---------------------------------------------------------------
    SELECT 'events_user_id_missing', 'raw', 'INFO', COUNT(*),
           (SELECT COUNT(*) FROM raw.events), 0,
           'Event user_id is sparse; session customer_id uses the one nonnull ID available within a session'
    FROM raw.events WHERE user_id IS NULL
)
SELECT
    check_name,
    layer,
    severity,
    failure_count,
    denominator,
    failure_count::DOUBLE / NULLIF(denominator, 0) AS failure_rate,
    CASE
        WHEN failure_count = 0 THEN 'PASS'
        WHEN blocking = 1 THEN 'FAIL'
        ELSE 'WARN'
    END AS status,
    notes
FROM checks;
