"""Metric card components for dashboard."""

import streamlit as st
from typing import Dict


def display_metric_card(
    metric_name: str,
    control_value: float,
    variant_value: float,
    relative_lift: float,
    p_value: float,
    is_significant: bool,
    is_primary: bool = False
):
    """
    Display a metric comparison card.
    
    Args:
        metric_name: Display name of the metric
        control_value: Control group value
        variant_value: Variant group value
        relative_lift: Relative lift percentage
        p_value: Statistical p-value
        is_significant: Whether result is significant
        is_primary: Whether this is the primary metric
    """
    with st.container():
        # Header
        if is_primary:
            st.markdown(f"### {metric_name} (Primary)")
        else:
            st.markdown(f"### {metric_name}")
        
        # Metrics in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="Control",
                value=f"{control_value:.3f}",
            )
        
        with col2:
            delta_color = "normal" if relative_lift > 0 else "inverse"
            st.metric(
                label="Variant B",
                value=f"{variant_value:.3f}",
                delta=f"{relative_lift*100:+.2f}%",
                delta_color=delta_color
            )
        
        with col3:
            sig_status = "YES" if is_significant else "NO"
            st.metric(
                label="Significant?",
                value=sig_status,
                help=f"p-value: {p_value:.4f}"
            )
        
        st.divider()


def display_summary_metrics(metrics_data: Dict):
    """
    Display high-level summary metrics.
    
    Args:
        metrics_data: Dictionary of metric results
    """
    st.markdown("## Key Metrics Summary")
    
    cols = st.columns(4)
    
    # Count significant improvements
    improvements = sum(
        1 for m in metrics_data.values() 
        if m['is_significant'] and m['relative_lift'] > 0
    )
    
    # Count degradations
    degradations = sum(
        1 for m in metrics_data.values() 
        if m.get('is_degraded', False)
    )
    
    # Get primary metric lift
    primary_lift = None
    for m in metrics_data.values():
        if m.get('is_primary'):
            primary_lift = m['relative_lift'] * 100
            break
    
    with cols[0]:
        st.metric("Metrics Improved", improvements)
    
    with cols[1]:
        st.metric("Guardrails Degraded", degradations)
    
    with cols[2]:
        if primary_lift is not None:
            st.metric("Primary Metric Lift", f"{primary_lift:+.2f}%")
    
    with cols[3]:
        total_users = sum(
            m['sample_size_control'] + m['sample_size_variant']
            for m in metrics_data.values()
        ) // len(metrics_data)
        st.metric("Total Users", f"{total_users:,}")
    
    st.divider()
