"""Ship decision recommendation component."""

import streamlit as st
from typing import Dict, List
import sys
from pathlib import Path

# Add project root to path to import config
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
from analysis.config import CONFIDENCE_LEVEL


def display_ship_decision(decision_data: Dict):
    """
    Display the final ship/don't ship recommendation.
    
    Args:
        decision_data: Dictionary with decision, confidence, and reasoning
    """
    decision = decision_data['decision']
    confidence = decision_data['confidence']
    reasoning = decision_data['reasoning']
    
    # Determine styling based on decision
    if decision == 'SHIP':
        bg_color = "#d4edda"
        border_color = "#c3e6cb"
        text_color = "#155724"
    elif 'DON\'T SHIP' in decision or 'DON'T SHIP' in decision:
        # Check if there are degraded guardrails (MEDIUM confidence) vs no success (HIGH confidence)
        if confidence == "MEDIUM":
            bg_color = "#fff3cd"
            border_color = "#ffeeba"
            text_color = "#856404"
        else:
            bg_color = "#f8d7da"
            border_color = "#f5c6cb"
            text_color = "#721c24"
    else:
        bg_color = "#fff3cd"
        border_color = "#ffeeba"
        text_color = "#856404"
    
    # Display decision box
    st.markdown(f"""
        <div style="
            background-color: {bg_color};
            border: 3px solid {border_color};
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            margin: 20px 0;
        ">
            <h1 style="color: {text_color}; margin: 0;">
                {decision}
            </h1>
            <h3 style="color: {text_color}; margin-top: 10px;">
                Confidence: {confidence}
            </h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Display reasoning
    st.markdown("### Reasoning")
    for i, reason in enumerate(reasoning, 1):
        st.markdown(f"{i}. {reason}")
    
    # Display key stats
    st.markdown("### Key Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(
            "Primary Metric Lift",
            f"{decision_data['primary_metric_lift']*100:+.2f}%"
        )
    
    with col2:
        pval = decision_data['primary_metric_pvalue']
        pval_display = f"{pval:.4f}" if pval >= 0.001 else "< 0.001"
        st.metric(
            "Primary Metric p-value",
            pval_display
        )
    
    # Degraded guardrails
    if decision_data['degraded_guardrails']:
        st.error("**Degraded Guardrails:** " + 
                ", ".join(decision_data['degraded_guardrails']))
    else:
        st.success("**All guardrail metrics passed**")


def display_experiment_info(experiment_id: str, config: Dict):
    """
    Display experiment configuration information.
    
    Args:
        experiment_id: Experiment identifier
        config: Experiment configuration dictionary
    """
    st.markdown("## Experiment Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Experiment ID:** `{experiment_id}`")
        st.markdown(f"**Name:** {config.get('experiment_name', 'N/A')}")
        st.markdown(f"**Primary Metric:** {config.get('primary_metric', 'N/A').replace('_', ' ').title()}")
    
    with col2:
        st.markdown(f"**Start Date:** {config.get('start_date', 'N/A')}")
        st.markdown(f"**End Date:** {config.get('end_date', 'N/A')}")
        st.markdown(f"**Allocation:** {config.get('control_allocation', 0.5)*100:.0f}% Control / "
                   f"{config.get('variant_allocation', 0.5)*100:.0f}% Variant")
    
    st.markdown(f"**Guardrail Metrics:** {config.get('guardrail_metrics', 'N/A')}")
    
    st.divider()


def display_statistical_notes():
    """Display notes about statistical methodology."""
    ci_percent = int(CONFIDENCE_LEVEL * 100)
    with st.expander("Statistical Methodology"):
        st.markdown(f"""
        ### Statistical Testing Approach
        
        **Hypothesis Testing:**
        - Two-sample t-tests for continuous metrics
        - Significance level: α = 0.05 for primary metrics
        - Significance level: α = 0.10 for guardrail metrics
        
        **Effect Size:**
        - Cohen's d used to measure practical significance
        - Minimum detectable effect: 2% for primary metric
        - Maximum acceptable degradation: 1% for guardrails
        
        **Decision Criteria:**
        
        Ship if:
        1. Primary metric shows significant positive lift (p < 0.05)
        2. Lift exceeds minimum threshold (> 2%)
        3. No guardrail metrics significantly degraded
        
        Don't Ship if:
        - Primary metric not significant
        - Primary metric shows negative lift
        - Any guardrail metric significantly degraded
        
        **Confidence Intervals:**
        - {ci_percent}% confidence intervals displayed for all metrics
        - Non-overlapping CIs indicate likely significant difference
        """)
