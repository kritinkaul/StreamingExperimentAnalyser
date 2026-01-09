# Architecture

Data pipeline that transforms listening events into experiment results.

## Flow

```
Last.fm TSV (~19M events)
  ↓
load_data.py → DuckDB (raw.scrobbles_raw)
  ↓
dbt staging:
  - stg_scrobbles (clean, detect skips)
  - stg_experiment_assignment (hash-based 50/50 split)
  ↓
dbt marts:
  - dim_sessions (30-min threshold sessionization)
  - fct_user_metrics (aggregated metrics per user)
  - fct_experiment_results (control vs variant stats)
  ↓
experiment_analysis.py:
  - t-tests, effect sizes, confidence intervals
  - Ship/Don't Ship decision logic
  - Output: experiment_results.json
  ↓
Streamlit Dashboard (4 pages):
  - Overview, Metrics Analysis, Ship Decision, Data Explorer
```

## Component Details

### 1. Data Ingestion (`scripts/load_data.py`)

**Purpose:** Load Last.fm TSV files into DuckDB

**Process:**
1. Scan `data/raw/` for userid-*.tsv files
2. Parse TSV format (artist, album, track, timestamp)
3. Combine all users into single DataFrame
4. Create DuckDB database and raw schema
5. Insert data with indices for performance

**Output:** `data/streaming.duckdb` with `raw.scrobbles_raw` table

### 2. dbt Staging Layer

#### stg_scrobbles

**Purpose:** Clean and enrich raw scrobbles

**Transformations:**
- Trim whitespace from text fields
- Calculate play duration (time to next track)
- Cap duration at 10 minutes (outlier handling)
- Flag skips (< 30 seconds between plays)
- Filter null/empty records

**Key Logic:**
```sql
LEAD(played_at) OVER (PARTITION BY user_id ORDER BY played_at) AS next_play_at
play_duration = MIN(next_play_at - played_at, 10 minutes)
is_skip = (next_play_at - played_at < 30 seconds)
```

#### stg_experiment_assignment

**Purpose:** Assign users to experiment variants

**Transformations:**
- Hash user_id for deterministic assignment
- 50/50 split using modulo 100
- Join with experiment config seed
- Add experiment metadata (dates, metrics)

**Key Logic:**
```sql
variant = CASE 
  WHEN ABS(HASH(user_id)) % 100 < 50 THEN 'control'
  ELSE 'variant_b'
END
```

### 3. dbt Marts Layer

#### dim_sessions

**Purpose:** Sessionize listening events

**Business Logic:**
- New session if gap > 30 minutes
- Aggregate tracks, duration, skips per session
- Calculate session-level skip rate
- Filter experiment period (start_date to end_date)
- Remove sessions < 2 tracks (noise)

**Key Metrics:**
- tracks_played
- unique_artists
- session_duration_minutes
- session_skip_rate

#### fct_user_metrics

**Purpose:** User-level engagement metrics

**Aggregations:**
- Total sessions, tracks, listening minutes
- Average session duration (PRIMARY METRIC)
- Average tracks per session
- Average skip rate (GUARDRAIL)
- Average unique artists (GUARDRAIL)
- D1 retention calculation (GUARDRAIL)

**Filter:** Minimum 3 sessions (engagement threshold)

#### fct_experiment_results

**Purpose:** Variant-level statistics

**Aggregations:**
- Mean and stddev for each metric
- Sample sizes (control vs variant)
- Unpivoted format (one row per metric per variant)

### 4. Statistical Analysis (`analysis/experiment_analysis.py`)

**Purpose:** Test experiment hypotheses

**ExperimentAnalyzer Class:**

**Methods:**
1. `load_user_metrics()` - Read from fct_user_metrics
2. `analyze_metric()` - Run t-test for single metric
3. `analyze_all_metrics()` - Test primary + guardrails
4. `make_ship_decision()` - Apply decision criteria
5. `save_results()` - Export to JSON

**Statistical Tests (utils.py):**
- `perform_ttest()` - Two-sample t-test
- `calculate_cohens_d()` - Effect size
- `calculate_minimum_detectable_effect()` - Power analysis

**Decision Logic:**

```python
Ship if:
  primary_metric.lift > 2% AND
  primary_metric.p_value < 0.05 AND
  primary_metric.relative_lift > 0 AND
  no guardrail degraded > 1% (p < 0.10)

Don't Ship otherwise
```

### 5. Dashboard (`dashboard/app.py`)

**Purpose:** Interactive experiment results viewer

**Architecture:**
- **Main App:** Page routing, data loading
- **Components:**
  - `metric_cards.py` - Metric display components
  - `charts.py` - Plotly visualizations
  - `recommendation.py` - Decision display

**Pages:**
1. **Overview** - High-level summary + quick decision
2. **Metrics Analysis** - Detailed comparisons with tabs
3. **Ship Decision** - Final recommendation + reasoning
4. **Data Explorer** - Raw data + CSV download

**Caching:**
- `@st.cache_data` on database queries
- Loads results from JSON (fast)

## Data Flow Summary

```
Raw Events (19M rows)
  ↓ [load_data.py]
Raw Table (19M rows)
  ↓ [stg_scrobbles]
Staging Table (19M rows, enriched)
  ↓ [dim_sessions]
Sessions Table (~400K sessions)
  ↓ [fct_user_metrics]
User Metrics (~800 users with 3+ sessions)
  ↓ [experiment_analysis.py]
Statistical Results (JSON)
  ↓ [Streamlit]
Dashboard Visualization
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Storage | DuckDB | In-process analytics database |
| Transformation | dbt | SQL-based data modeling |
| Analysis | Python + scipy | Statistical testing |
| Visualization | Streamlit + Plotly | Interactive dashboard |
| Data Manipulation | pandas | DataFrames |

## Key Design Decisions

### Why DuckDB?
- **No server required** (embedded database)
- **Fast analytics** (columnar storage)
- **SQL interface** (dbt compatible)
- **Lightweight** (single file)

### Why dbt?
- **Industry standard** for data transformations
- **Version control** for SQL
- **Documentation** built-in
- **Testing framework** included

### Why Hash-Based Assignment?
- **Deterministic** (repeatable results)
- **No storage needed** (compute on-the-fly)
- **Uniform distribution** (balanced variants)

### Why 30-Minute Session Threshold?
- **Industry standard** (Spotify, YouTube use 30 min)
- **Balances** granularity vs. continuity
- **Research-backed** (Nielsen, comScore)

## Performance Characteristics

This project is optimized for local development and analysis:

| Operation | Time | Notes |
|-----------|------|-------|
| Data Load | ~2 min | 19M records from TSV |
| dbt Run | ~30 sec | All models |
| Analysis | ~10 sec | Statistical tests |
| Dashboard Load | <1 sec | Cached queries |

## Local Development

This project runs entirely locally with no external dependencies:

- **No cloud services required**
- **Embedded database** (DuckDB)
- **Local file storage**
- **Anonymized dataset** (Last.fm userids are hashed)
- **No PII** in dataset

## Testing Strategy

### dbt Tests
- Schema tests (not_null, unique, accepted_values)
- Referential integrity
- Business logic validation

### Python Tests
- Statistical functions (test_utils.py - would add)
- Decision logic edge cases
- Data quality checks

### Manual Testing
- End-to-end pipeline
- Dashboard functionality
- Edge case handling

---

**Next:** See README.md for setup instructions and usage guide.
