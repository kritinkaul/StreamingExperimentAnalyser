"""Chart components for dashboard."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List


def plot_metric_comparison(metrics_data: Dict):
    """
    Create bar chart comparing control vs variant across all metrics.
    
    Args:
        metrics_data: Dictionary of metric results
    """
    # Prepare data
    data = []
    for metric_name, result in metrics_data.items():
        data.append({
            'Metric': metric_name.replace('_', ' ').title(),
            'Group': 'Control',
            'Value': result['control_mean'],
            'Error': result['control_se']
        })
        data.append({
            'Metric': metric_name.replace('_', ' ').title(),
            'Group': 'Variant B',
            'Value': result['variant_mean'],
            'Error': result['variant_se']
        })
    
    df = pd.DataFrame(data)
    
    # Create grouped bar chart
    fig = px.bar(
        df,
        x='Metric',
        y='Value',
        color='Group',
        barmode='group',
        error_y='Error',
        title='Metric Comparison: Control vs Variant B',
        color_discrete_map={'Control': '#636EFA', 'Variant B': '#EF553B'}
    )
    
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Metric Value",
        legend_title="Group",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_confidence_intervals(metrics_data: Dict, metric_name: str):
    """
    Plot confidence intervals for a specific metric.
    
    Args:
        metrics_data: Dictionary of metric results
        metric_name: Name of metric to plot
    """
    if metric_name not in metrics_data:
        st.error(f"Metric {metric_name} not found")
        return
    
    result = metrics_data[metric_name]
    
    # Prepare data
    groups = ['Control', 'Variant B']
    means = [result['control_mean'], result['variant_mean']]
    ci_lower = [result['control_ci_lower'], result['variant_ci_lower']]
    ci_upper = [result['control_ci_upper'], result['variant_ci_upper']]
    
    # Create figure
    fig = go.Figure()
    
    # Add points for means
    fig.add_trace(go.Scatter(
        x=groups,
        y=means,
        mode='markers',
        marker=dict(size=15, color=['#636EFA', '#EF553B']),
        name='Mean',
        error_y=dict(
            type='data',
            symmetric=False,
            array=[ci_upper[i] - means[i] for i in range(len(means))],
            arrayminus=[means[i] - ci_lower[i] for i in range(len(means))],
            color='gray',
            thickness=2,
            width=10
        )
    ))
    
    # Update layout
    fig.update_layout(
        title=f"95% Confidence Intervals: {metric_name.replace('_', ' ').title()}",
        xaxis_title="Group",
        yaxis_title="Metric Value",
        showlegend=False,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_lift_summary(metrics_data: Dict):
    """
    Create waterfall chart showing lift across all metrics.
    
    Args:
        metrics_data: Dictionary of metric results
    """
    # Prepare data
    metrics = []
    lifts = []
    colors = []
    
    for metric_name, result in metrics_data.items():
        metrics.append(metric_name.replace('_', ' ').title())
        lift_pct = result['relative_lift'] * 100
        lifts.append(lift_pct)
        
        # Color based on significance and direction
        if result['is_significant']:
            colors.append('green' if lift_pct > 0 else 'red')
        else:
            colors.append('gray')
    
    # Create bar chart
    fig = go.Figure(go.Bar(
        x=lifts,
        y=metrics,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{lift:+.2f}%" for lift in lifts],
        textposition='outside'
    ))
    
    # Add vertical line at 0
    fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
    
    fig.update_layout(
        title="Relative Lift by Metric (% Change)",
        xaxis_title="Relative Lift (%)",
        yaxis_title="",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_effect_sizes(metrics_data: Dict):
    """
    Plot Cohen's d effect sizes for all metrics.
    
    Args:
        metrics_data: Dictionary of metric results
    """
    # Prepare data
    data = []
    for metric_name, result in metrics_data.items():
        data.append({
            'Metric': metric_name.replace('_', ' ').title(),
            'Cohen\'s d': result['cohens_d'],
            'Interpretation': interpret_cohens_d(result['cohens_d'])
        })
    
    df = pd.DataFrame(data)
    
    # Create bar chart
    fig = px.bar(
        df,
        x='Cohen\'s d',
        y='Metric',
        orientation='h',
        color='Interpretation',
        title='Effect Sizes (Cohen\'s d)',
        color_discrete_map={
            'negligible': '#FFA500',
            'small': '#FFFF00',
            'medium': '#90EE90',
            'large': '#008000'
        }
    )
    
    # Add reference lines
    for threshold, label in [(0.2, 'Small'), (0.5, 'Medium'), (0.8, 'Large')]:
        fig.add_vline(x=threshold, line_dash="dash", opacity=0.3,
                     annotation_text=label, annotation_position="top")
        fig.add_vline(x=-threshold, line_dash="dash", opacity=0.3)
    
    fig.update_layout(
        xaxis_title="Cohen's d",
        yaxis_title="",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def interpret_cohens_d(d: float) -> str:
    """Interpret Cohen's d effect size."""
    abs_d = abs(d)
    if abs_d < 0.2:
        return 'negligible'
    elif abs_d < 0.5:
        return 'small'
    elif abs_d < 0.8:
        return 'medium'
    else:
        return 'large'
