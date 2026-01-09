{{ config(materialized='table') }}

WITH experiment_config AS (
    SELECT * FROM {{ ref('experiment_config') }}
),

all_users AS (
    SELECT DISTINCT user_id
    FROM {{ ref('stg_scrobbles') }}
),

user_with_variant AS (
    SELECT
        u.user_id,
        e.experiment_id,
        e.experiment_name,
        e.start_date::DATE AS experiment_start,
        e.end_date::DATE AS experiment_end,
        CASE
            WHEN (ABS(HASH(u.user_id)) % 100) < (e.control_allocation * 100)::INT
                THEN 'control'
            ELSE 'variant_b'
        END AS experiment_variant,
        e.primary_metric,
        e.guardrail_metrics
    FROM all_users u
    CROSS JOIN experiment_config e
)

SELECT * FROM user_with_variant
