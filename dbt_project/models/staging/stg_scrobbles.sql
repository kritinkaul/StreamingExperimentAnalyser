{{ config(materialized='view') }}

WITH source AS (
    SELECT
        user_id,
        timestamp AS played_at,
        artist,
        album,
        track
    FROM {{ source('raw', 'scrobbles_raw') }}
),

cleaned AS (
    SELECT
        user_id,
        played_at,
        TRIM(artist) AS artist_name,
        TRIM(album) AS album_name,
        TRIM(track) AS track_name,
        LEAD(played_at) OVER (PARTITION BY user_id ORDER BY played_at) AS next_play_at
    FROM source
    WHERE
        artist IS NOT NULL 
        AND artist != ''
        AND track IS NOT NULL 
        AND track != ''
        AND played_at IS NOT NULL
),

with_play_duration AS (
    SELECT
        *,
        CASE 
            WHEN next_play_at IS NOT NULL 
            THEN LEAST(EXTRACT(EPOCH FROM (next_play_at - played_at)) / 60.0, 10.0)
            ELSE 3.5
        END AS play_duration_minutes,
        CASE 
            WHEN next_play_at IS NOT NULL 
                AND EXTRACT(EPOCH FROM (next_play_at - played_at)) < 30
            THEN TRUE
            ELSE FALSE
        END AS is_skip
    FROM cleaned
)

SELECT
    user_id,
    played_at,
    artist_name,
    album_name,
    track_name,
    play_duration_minutes,
    is_skip
FROM with_play_duration
