# Streaming Experiment Analyzer

An A/B testing platform for analyzing music streaming experiments using real user data.

## Overview

This project analyzes whether product changes improve user engagement without harming key metrics. It processes ~19M listening events from Last.fm, computes session-level metrics, and runs statistical tests to provide a clear recommendation on whether to ship a feature.

Built with Python, dbt, DuckDB, and Streamlit.

### What it does

- Loads and processes listening event data
- Sessionizes user activity (30-minute inactivity threshold)
- Computes engagement metrics (session duration, skip rate, retention)
- Assigns users to control/variant groups
- Runs statistical tests (t-tests, effect sizes, confidence intervals)
- Provides Ship/Don't Ship recommendations  

## Architecture

```
┌─────────────┐
│  Last.fm    │
│  Dataset    │──┐
└─────────────┘  │
                 ▼
            ┌──────────┐
            │  DuckDB  │
            │ (storage)│
            └──────────┘
                 │
                 ▼
          ┌──────────────┐
          │  dbt Models  │
          │  - Staging   │
          │  - Marts     │
          └──────────────┘
                 │
                 ▼
       ┌──────────────────┐
       │  Python Analysis │
       │  - T-tests       │
       │  - Effect sizes  │
       │  - Decision logic│
       └──────────────────┘
                 │
                 ▼
          ┌─────────────┐
          │  Streamlit  │
          │  Dashboard  │
          └─────────────┘
```

### Data Flow

Raw Events → Staging (clean, assign variants) → Marts (sessions, user metrics) → Statistical Analysis → Dashboard

## Metrics

**Primary:** Average Session Duration (minutes)

**Guardrails:** Skip Rate, Sessions per User, D1 Retention, Artist Diversity

## Setup

### Requirements

- Python 3.9+
- ~500 MB disk space

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd StreamingExperimentAnalyser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get the Data

Download the Last.fm 1K dataset from http://ocelma.net/MusicRecommendationDataset/lastfm-1K.html

Extract and copy the `userid-timestamp-artid-artname-traid-traname.tsv` file to `data/raw/`

### 3. Load Data

```bash
python scripts/load_data.py
```

Creates `data/streaming.duckdb` with ~19M records.

### 4. Run Transformations

```bash
cd dbt_project
dbt seed
dbt run
cd ..
```

### 5. Analyze Results

```bash
python analysis/experiment_analysis.py
```

### 6. View Dashboard

```bash
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`

## Project Structure

```
streaming-experiment-analyzer/
├── data/
│   ├── raw/                    # Last.fm TSV file
│   └── streaming.duckdb        # DuckDB database
├── dbt_project/
│   ├── models/
│   │   ├── staging/           # Data cleaning
│   │   └── marts/             # Business logic
│   └── seeds/
│       └── experiment_config.csv
├── analysis/
│   ├── config.py
│   ├── utils.py
│   └── experiment_analysis.py
└── dashboard/
    └── app.py
```

## How It Works

### Experiment Design

Users are assigned via hash: `hash(user_id) % 100 < 50` → Control, else Variant B.

Experiment period: March-April 2009 (2 months, high activity period).

Sessions use 30-minute inactivity threshold.

### Statistical Methodology

Uses two-sample t-tests with α=0.05 for primary metric and α=0.10 for guardrails. Also computes Cohen's d for effect size and 95% confidence intervals.

**Ship Decision:**
- Primary metric must show >2% lift with p<0.05
- No guardrail can degrade >1%

## Dashboard

Four pages:

1. **Overview** - Experiment config, summary metrics, quick decision
2. **Metrics Analysis** - Detailed comparisons, confidence intervals, effect sizes
3. **Ship Decision** - Recommendation with reasoning
4. **Data Explorer** - Raw data viewer with CSV export

## Configuration

Experiment config: `dbt_project/seeds/experiment_config.csv`

Statistical thresholds: `analysis/config.py`

## Troubleshooting

### Issue: "No Last.fm data files found"

**Solution:**
1. Download dataset from [http://ocelma.net/MusicRecommendationDataset/lastfm-1K.html](http://ocelma.net/MusicRecommendationDataset/lastfm-1K.html)
2. Extract and copy `userid-*.tsv` files to `data/raw/`

### Issue: "Database not found" in dashboard

**Solution:**
Run the full pipeline:
```bash
python scripts/load_data.py
cd dbt_project && dbt seed && dbt run && cd ..
python analysis/experiment_analysis.py
```

### Issue: dbt connection error

**Solution:**
Ensure `dbt_project/profiles.yml` path is correct (relative to dbt_project/)

### Issue: Import errors

**Solution:**
Activate virtual environment and reinstall dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Key Assumptions

- Skip detection: tracks played < 30 seconds
- Session boundary: 30-minute inactivity
- Minimum engagement: 3+ sessions for inclusion
- D1 retention: user active next day

## Tech Stack

Python, dbt, DuckDB, Streamlit, pandas, scipy

Dataset: Last.fm 1K Users by Òscar Celma

## Quick Start

```bash
# Full pipeline
python scripts/load_data.py
cd dbt_project && dbt seed && dbt run && cd ..
python analysis/experiment_analysis.py
streamlit run dashboard/app.py

# Or run the dashboard directly (uses pre-computed results)
streamlit run dashboard/app.py
```
