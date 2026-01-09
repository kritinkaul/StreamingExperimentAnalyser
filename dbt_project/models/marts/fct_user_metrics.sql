{{
    config(
        materialized='table'
    )
}}

WITH sessions AS (
    SELECT
        user_id,
        experiment_variant,
        session_start,
        tracks_played,
        unique_artists,
        session_duration_minutes,
        session_skip_rate,
        in_experiment_period
    FROM {{ ref('dim_sessions') }}
),

experiment_sessions AS (
    SELECT
        user_id,
        experiment_variant,
        session_start,
        tracks_played,
        unique_artists,
        session_duration_minutes,
        session_skip_rate
    FROM sessions
    WHERE in_experiment_period = TRUE
),

user_aggregates AS (
    SELECT
        user_id,
        experiment_variant,
        -- Session counts
        COUNT(*) AS total_sessions,
        COUNT(DISTINCT session_start::DATE) AS active_days,
        
        -- Track metrics
        SUM(tracks_played) AS total_tracks,
        AVG(tracks_played) AS avg_tracks_per_session,
        
        -- Duration metrics
        SUM(session_duration_minutes) AS total_listening_minutes,
        AVG(session_duration_minutes) AS avg_session_duration,
        
        -- Skip metrics
        AVG(session_skip_rate) AS avg_skip_rate,
        
        -- Diversity
        AVG(unique_artists) AS avg_unique_artists_per_session,
        
        -- Dates for retention calculation
        MIN(session_start::DATE) AS first_session_date,
        MAX(session_start::DATE) AS last_session_date
    FROM experiment_sessions
    GROUP BY 1, 2
),

retention_calc AS (
    SELECT
        u.*,
        -- D1 Retention: user active the day after first session
        CASE 
            WHEN EXISTS (
                SELECT 1 
                FROM experiment_sessions s
                WHERE s.user_id = u.user_id
                    AND s.session_start::DATE = u.first_session_date + INTERVAL '1 day'
            )
            THEN TRUE
            ELSE FALSE
        END AS retention_d1
    FROM user_aggregates u
)

SELECT
    user_id,
    experiment_variant,
    total_sessions,
    active_days,
    total_tracks,
    avg_tracks_per_session,
    total_listening_minutes,
    avg_session_duration,
    avg_skip_rate,
    avg_unique_artists_per_session,
    retention_d1,
    first_session_date,
    last_session_date
FROM retention_calc
-- Only include users with meaningful engagement (at least 3 sessions)
WHERE total_sessions >= 3
