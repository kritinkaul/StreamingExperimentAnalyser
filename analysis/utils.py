"""Statistical utility functions."""

import numpy as np
from scipy import stats
from typing import Dict, Tuple
import sys
from pathlib import Path

# Add project root to path to import config
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))
from analysis.config import CONFIDENCE_LEVEL


def calculate_cohens_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    
    return (np.mean(group2) - np.mean(group1)) / pooled_std


def perform_ttest(control: np.ndarray, variant: np.ndarray) -> Dict[str, float]:
    """Perform two-sample t-test."""
    t_stat, p_value = stats.ttest_ind(variant, control)
    control_mean = np.mean(control)
    variant_mean = np.mean(variant)
    control_se = stats.sem(control)
    variant_se = stats.sem(variant)
    
    control_ci = stats.t.interval(CONFIDENCE_LEVEL, len(control) - 1, loc=control_mean, scale=control_se)
    variant_ci = stats.t.interval(CONFIDENCE_LEVEL, len(variant) - 1, loc=variant_mean, scale=variant_se)
    
    cohens_d = calculate_cohens_d(control, variant)
    relative_lift = (variant_mean - control_mean) / control_mean if control_mean != 0 else 0
    
    return {
        "control_mean": control_mean,
        "variant_mean": variant_mean,
        "control_se": control_se,
        "variant_se": variant_se,
        "control_ci_lower": control_ci[0],
        "control_ci_upper": control_ci[1],
        "variant_ci_lower": variant_ci[0],
        "variant_ci_upper": variant_ci[1],
        "t_statistic": t_stat,
        "p_value": p_value,
        "cohens_d": cohens_d,
        "relative_lift": relative_lift,
        "sample_size_control": len(control),
        "sample_size_variant": len(variant),
    }


def calculate_minimum_detectable_effect(
    baseline_mean: float,
    baseline_std: float,
    sample_size: int,
    alpha: float = 0.05,
    power: float = 0.80
) -> float:
    """Calculate minimum detectable effect."""
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_beta = stats.norm.ppf(power)
    mde_absolute = (z_alpha + z_beta) * baseline_std * np.sqrt(2 / sample_size)
    return mde_absolute / baseline_mean if baseline_mean != 0 else 0


def format_p_value(p_value: float) -> str:
    """Format p-value for display."""
    if p_value < 0.001:
        return "< 0.001"
    return f"{p_value:.3f}"


def interpret_effect_size(cohens_d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(cohens_d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"
