{{
    config(
        materialized='table'
    )
}}

WITH user_metrics AS (
    SELECT * FROM {{ ref('fct_user_metrics') }}
),

experiment_config AS (
    SELECT * FROM {{ ref('experiment_config') }}
),

-- Aggregate metrics by variant
variant_aggregates AS (
    SELECT
        e.experiment_id,
        e.experiment_name,
        u.experiment_variant,
        
        -- Sample sizes
        COUNT(*) AS sample_size,
        
        -- Session duration (primary metric)
        AVG(u.avg_session_duration) AS avg_session_duration,
        STDDEV(u.avg_session_duration) AS stddev_session_duration,
        
        -- Tracks per session
        AVG(u.avg_tracks_per_session) AS avg_tracks_per_session,
        STDDEV(u.avg_tracks_per_session) AS stddev_tracks_per_session,
        
        -- Skip rate (guardrail)
        AVG(u.avg_skip_rate) AS avg_skip_rate,
        STDDEV(u.avg_skip_rate) AS stddev_skip_rate,
        
        -- Sessions per user (guardrail)
        AVG(u.total_sessions) AS avg_sessions_per_user,
        STDDEV(u.total_sessions) AS stddev_sessions_per_user,
        
        -- Retention (guardrail)
        AVG(CASE WHEN u.retention_d1 THEN 1.0 ELSE 0.0 END) AS retention_d1_rate,
        STDDEV(CASE WHEN u.retention_d1 THEN 1.0 ELSE 0.0 END) AS stddev_retention_d1,
        
        -- Artist diversity (guardrail)
        AVG(u.avg_unique_artists_per_session) AS avg_artists_per_session,
        STDDEV(u.avg_unique_artists_per_session) AS stddev_artists_per_session
        
    FROM user_metrics u
    CROSS JOIN experiment_config e
    GROUP BY 1, 2, 3
),

-- Unpivot to get one row per metric per variant
metrics_unpivoted AS (
    SELECT experiment_id, experiment_name, experiment_variant, 'sample_size' AS metric_name, sample_size AS metric_value, NULL AS metric_stddev FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'avg_session_duration', avg_session_duration, stddev_session_duration FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'avg_tracks_per_session', avg_tracks_per_session, stddev_tracks_per_session FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'avg_skip_rate', avg_skip_rate, stddev_skip_rate FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'avg_sessions_per_user', avg_sessions_per_user, stddev_sessions_per_user FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'retention_d1_rate', retention_d1_rate, stddev_retention_d1 FROM variant_aggregates
    UNION ALL
    SELECT experiment_id, experiment_name, experiment_variant, 'avg_artists_per_session', avg_artists_per_session, stddev_artists_per_session FROM variant_aggregates
)

SELECT * FROM metrics_unpivoted
ORDER BY metric_name, experiment_variant
