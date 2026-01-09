"""Configuration settings for experiment analysis."""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DUCKDB_PATH = DATA_DIR / "streaming.duckdb"

# Statistical thresholds
SIGNIFICANCE_LEVEL = 0.05  # p-value threshold for primary metrics
GUARDRAIL_SIGNIFICANCE = 0.10  # More lenient for guardrails
MIN_EFFECT_SIZE = 0.02  # Minimum 2% lift for primary metric
MAX_GUARDRAIL_DEGRADATION = 0.01  # Max 1% degradation for guardrails

# Experiment parameters
EXPERIMENT_ID = "exp_001"
PRIMARY_METRIC = "avg_session_duration"
GUARDRAIL_METRICS = ["skip_rate", "sessions_per_user", "retention_d1"]
