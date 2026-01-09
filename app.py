"""Streamlit dashboard for A/B test results."""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))

# Constants
DUCKDB_PATH = PROJECT_ROOT / "data" / "streaming.duckdb"
EXPERIMENT_ID = "exp_001"
PRIMARY_METRIC = "avg_session_duration"
GUARDRAIL_METRICS = ["skip_rate", "sessions_per_user", "retention_d1"]

st.set_page_config(
    page_title="Experiment Analyzer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main > div {padding-top: 1rem;}
    [data-testid="stSidebar"] {background-color: #191414;}
    .stRadio > label {color: #1DB954;}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_experiment_config():
    """Load experiment configuration."""
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    if results_path.exists():
        try:
            with open(results_path, 'r') as f:
                data = json.load(f)
            return {
                'experiment_id': data.get('experiment_id', EXPERIMENT_ID),
                'experiment_name': 'Enhanced Discovery Algorithm',
                'start_date': '2009-03-01',
                'end_date': '2009-04-30',
                'primary_metric': 'avg_session_duration',
                'guardrail_metrics': 'skip_rate,sessions_per_user,retention_d1',
                'control_allocation': 0.5,
                'variant_allocation': 0.5
            }
        except:
            pass
    
    return {
        'experiment_id': EXPERIMENT_ID,
        'experiment_name': 'Enhanced Discovery Algorithm',
        'start_date': '2009-03-01',
        'end_date': '2009-04-30',
        'primary_metric': 'avg_session_duration',
        'guardrail_metrics': 'skip_rate,sessions_per_user,retention_d1',
        'control_allocation': 0.5,
        'variant_allocation': 0.5
    }


@st.cache_data
def load_experiment_results():
    """Load pre-computed experiment results from JSON."""
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    
    if not results_path.exists():
        return None
    
    with open(results_path, 'r') as f:
        return json.load(f)


def check_data_availability():
    """Check if required data is available."""
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    
    if not results_path.exists():
        st.error("Analysis results not found!")
        return False
    
    return True


def main():
    """Main dashboard application."""
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Streaming Experiment Analyzer")
        st.markdown("A/B Testing Platform for Product Features")
    
    st.markdown("---")
    
    if not check_data_availability():
        return
    
    config = load_experiment_config()
    results = load_experiment_results()
    
    if config is None:
        st.error("Experiment configuration not found.")
        return
    
    # Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="#1DB954">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            <h2 style="color: #1DB954; margin-top: 10px;">Experiment Analyzer</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["Overview", "Metrics Analysis", "Ship Decision", "Data Explorer"]
        )
        
        st.markdown("---")
        st.markdown("**Experiment:** " + EXPERIMENT_ID)
        st.markdown(f"{config['start_date']} to {config['end_date']}")
        
        if results:
            st.markdown("---")
            primary = results['metrics'][PRIMARY_METRIC]
            st.metric(
                "Primary Lift",
                f"{primary['relative_lift']*100:+.2f}%"
            )
    
    # Main content
    if page == "Overview":
        display_overview_page(config, results)
    elif page == "Metrics Analysis":
        display_metrics_page(results)
    elif page == "Ship Decision":
        display_decision_page(results)
    elif page == "Data Explorer":
        display_explorer_page()


def display_overview_page(config, results):
    """Display overview page."""
    from dashboard.components.recommendation import display_experiment_info
    from dashboard.components.metric_cards import display_summary_metrics
    from dashboard.components.charts import plot_lift_summary
    
    st.header("Experiment Overview")
    display_experiment_info(EXPERIMENT_ID, config)
    
    if results is None:
        st.warning("Statistical analysis not yet run.")
        return
    
    display_summary_metrics(results['metrics'])
    
    st.markdown("## Decision Preview")
    decision = results['decision']['decision']
    
    if 'SHIP' in decision and '✅' in decision:
        st.success(f"**Recommendation:** {decision}")
    elif '❌' in decision:
        st.error(f"**Recommendation:** {decision}")
    else:
        st.warning(f"**Recommendation:** {decision}")
    
    st.markdown(f"**Confidence:** {results['decision']['confidence']}")
    st.markdown("## Metric Comparisons")
    plot_lift_summary(results['metrics'])


def display_metrics_page(results):
    """Display detailed metrics analysis page."""
    from dashboard.components.charts import (
        plot_metric_comparison,
        plot_confidence_intervals,
        plot_effect_sizes
    )
    from dashboard.components.metric_cards import display_metric_card
    
    st.header("Detailed Metrics Analysis")
    
    if results is None:
        st.warning("Statistical analysis not yet run.")
        return
    
    tab1, tab2, tab3 = st.tabs(["Comparison", "Confidence Intervals", "Effect Sizes"])
    
    with tab1:
        st.markdown("### Metric Comparison")
        plot_metric_comparison(results['metrics'])
        
        st.markdown("### Detailed Breakdown")
        primary_result = results['metrics'][PRIMARY_METRIC]
        display_metric_card(
            PRIMARY_METRIC.replace('_', ' ').title(),
            primary_result['control_mean'],
            primary_result['variant_mean'],
            primary_result['relative_lift'],
            primary_result['p_value'],
            primary_result['is_significant'],
            is_primary=True
        )
        
        st.markdown("### Guardrail Metrics")
        for metric in GUARDRAIL_METRICS:
            if metric in results['metrics']:
                result = results['metrics'][metric]
                display_metric_card(
                    metric.replace('_', ' ').title(),
                    result['control_mean'],
                    result['variant_mean'],
                    result['relative_lift'],
                    result['p_value'],
                    result['is_significant'],
                    is_primary=False
                )
    
    with tab2:
        st.markdown("### 95% Confidence Intervals")
        metric_options = list(results['metrics'].keys())
        selected_metric = st.selectbox(
            "Select metric to visualize:",
            metric_options,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        plot_confidence_intervals(results['metrics'], selected_metric)
    
    with tab3:
        st.markdown("### Effect Sizes (Cohen's d)")
        plot_effect_sizes(results['metrics'])


def display_decision_page(results):
    """Display ship decision page."""
    from dashboard.components.recommendation import (
        display_ship_decision,
        display_statistical_notes
    )
    
    st.header("Ship / Don't Ship Decision")
    
    if results is None:
        st.warning("Statistical analysis not yet run.")
        return
    
    display_ship_decision(results['decision'])
    display_statistical_notes()


def display_explorer_page():
    """Display raw data explorer page."""
    st.header("Data Explorer")
    st.info("Data Explorer is only available when running locally with the full database.")


if __name__ == "__main__":
    main()
