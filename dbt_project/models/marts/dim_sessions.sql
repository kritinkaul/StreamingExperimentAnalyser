{{ config(materialized='table') }}

WITH scrobbles AS (
    SELECT
        user_id,
        played_at,
        artist_name,
        track_name,
        play_duration_minutes,
        is_skip
    FROM {{ ref('stg_scrobbles') }}
),

experiment_assignment AS (
    SELECT
        user_id,
        experiment_variant,
        experiment_start,
        experiment_end
    FROM {{ ref('stg_experiment_assignment') }}
),

scrobbles_with_variant AS (
    SELECT
        s.*,
        e.experiment_variant,
        e.experiment_start,
        e.experiment_end,
        CASE 
            WHEN s.played_at::DATE BETWEEN e.experiment_start AND e.experiment_end
            THEN TRUE
            ELSE FALSE
        END AS in_experiment_period
    FROM scrobbles s
    LEFT JOIN experiment_assignment e
        ON s.user_id = e.user_id
),

session_breaks AS (
    SELECT
        *,
        played_at - LAG(played_at) OVER (PARTITION BY user_id ORDER BY played_at) AS time_since_last_play,
        CASE 
            WHEN LAG(played_at) OVER (PARTITION BY user_id ORDER BY played_at) IS NULL 
            THEN 1
            WHEN played_at - LAG(played_at) OVER (PARTITION BY user_id ORDER BY played_at) > INTERVAL '30 minutes'
            THEN 1
            ELSE 0
        END AS is_session_start
    FROM scrobbles_with_variant
),

session_ids AS (
    SELECT
        *,
        user_id || '_' || 
        SUM(is_session_start) OVER (
            PARTITION BY user_id 
            ORDER BY played_at
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )::VARCHAR AS session_id
    FROM session_breaks
),

sessions_aggregated AS (
    SELECT
        session_id,
        user_id,
        experiment_variant,
        MIN(played_at) AS session_start,
        MAX(played_at) AS session_end,
        COUNT(*) AS tracks_played,
        COUNT(DISTINCT artist_name) AS unique_artists,
        SUM(play_duration_minutes) AS session_duration_minutes,
        SUM(CASE WHEN is_skip THEN 1 ELSE 0 END) AS tracks_skipped,
        MAX(CASE WHEN in_experiment_period THEN 1 ELSE 0 END) AS in_experiment_period
    FROM session_ids
    GROUP BY 1, 2, 3
)

SELECT
    session_id,
    user_id,
    experiment_variant,
    session_start,
    session_end,
    tracks_played,
    unique_artists,
    session_duration_minutes,
    tracks_skipped,
    CASE 
        WHEN tracks_played > 0 
        THEN tracks_skipped::FLOAT / tracks_played::FLOAT
        ELSE 0.0
    END AS session_skip_rate,
    in_experiment_period::BOOLEAN AS in_experiment_period
FROM sessions_aggregated
WHERE tracks_played >= 2
