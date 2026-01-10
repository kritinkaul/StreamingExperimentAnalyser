"""Load Last.fm scrobbles into DuckDB."""

import os
import sys
from pathlib import Path
import duckdb
import pandas as pd
from datetime import datetime, timedelta
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DUCKDB_PATH = DATA_DIR / "streaming.duckdb"


def load_lastfm_data() -> pd.DataFrame:
    """Load Last.fm dataset from TSV file."""
    print("Loading Last.fm dataset...")
    
    data_file = RAW_DATA_DIR / "userid-timestamp-artid-artname-traid-traname.tsv"
    
    if not data_file.exists():
        print(f"\nError: Data file not found at {data_file}")
        print("Download from: http://ocelma.net/MusicRecommendationDataset/lastfm-1K.html")
        print(f"Place the TSV file in: {RAW_DATA_DIR}/")
        sys.exit(1)
    
    print(f"Reading {data_file.name}... (this takes ~30 seconds)")
    
    # Format: user_id, timestamp, artist_id, artist_name, track_id, track_name
    df = pd.read_csv(
        data_file,
        sep='\t',
        names=['user_id', 'timestamp', 'artist_id', 'artist', 'track_id', 'track'],
        encoding='utf-8',
        on_bad_lines='skip'
    )
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%dT%H:%M:%SZ', errors='coerce')
    df = df.dropna(subset=['timestamp'])
    df['album'] = ''  # Add empty album column for compatibility
    df = df[['user_id', 'timestamp', 'artist', 'album', 'track']]
    
    print(f"\nLoaded {len(df):,} scrobbles")
    print(f"  Unique users:  {df['user_id'].nunique():,}")
    print(f"  Date range:    {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    return df


def create_database_schema(conn: duckdb.DuckDBPyConnection):
    """Create the raw data schema in DuckDB."""
    print("\nCreating database schema...")
    
    conn.execute("""
        CREATE SCHEMA IF NOT EXISTS raw
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw.scrobbles_raw (
            user_id VARCHAR,
            timestamp TIMESTAMP,
            artist VARCHAR,
            album VARCHAR,
            track VARCHAR
        )
    """)
    
    print("Schema created")


def load_data_to_duckdb(df: pd.DataFrame):
    """Load scrobbles data into DuckDB."""
    print("\nLoading data into DuckDB...")
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Connect to DuckDB
    conn = duckdb.connect(str(DUCKDB_PATH))
    
    # Create schema
    create_database_schema(conn)
    
    # Clear existing data
    conn.execute("DELETE FROM raw.scrobbles_raw")
    
    # Insert data
    conn.execute("""
        INSERT INTO raw.scrobbles_raw 
        SELECT * FROM df
    """)
    
    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM raw.scrobbles_raw").fetchone()[0]
    
    print(f"Loaded {row_count:,} records into DuckDB")
    
    # Create indices for performance
    print("\nCreating indices...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON raw.scrobbles_raw(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON raw.scrobbles_raw(timestamp)")
    print("Indices created")
    
    # Show sample stats
    print("\nDataset Statistics:")
    stats = conn.execute("""
        SELECT 
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(*) as total_scrobbles,
            MIN(timestamp) as earliest_scrobble,
            MAX(timestamp) as latest_scrobble,
            COUNT(DISTINCT artist) as unique_artists,
            COUNT(DISTINCT track) as unique_tracks
        FROM raw.scrobbles_raw
    """).fetchdf()
    
    print(f"  Unique users:     {stats['unique_users'].iloc[0]:,}")
    print(f"  Total scrobbles:  {stats['total_scrobbles'].iloc[0]:,}")
    print(f"  Date range:       {stats['earliest_scrobble'].iloc[0]} to {stats['latest_scrobble'].iloc[0]}")
    print(f"  Unique artists:   {stats['unique_artists'].iloc[0]:,}")
    print(f"  Unique tracks:    {stats['unique_tracks'].iloc[0]:,}")
    
    conn.close()
    print(f"\nDatabase created at: {DUCKDB_PATH}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Last.fm Data Ingestion Script")
    print("=" * 60)
    
    # Ensure raw data directory exists
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = load_lastfm_data()
    
    # Load into DuckDB
    load_data_to_duckdb(df)
    
    print("\n" + "=" * 60)
    print("Data ingestion complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. cd dbt_project")
    print("  2. dbt seed")
    print("  3. dbt run")


if __name__ == "__main__":
    main()
