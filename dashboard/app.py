"""
Streamlit dashboard for A/B experiment analysis.
Built for analyzing music streaming feature experiments.
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Lazy imports - only load when needed
DUCKDB_PATH = PROJECT_ROOT / "data" / "streaming.duckdb"
EXPERIMENT_ID = "exp_001"
PRIMARY_METRIC = "avg_session_duration"
GUARDRAIL_METRICS = ["skip_rate", "sessions_per_user", "retention_d1"]

st.set_page_config(
    page_title="Streaming Experiment Analyzer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Spotify-inspired styling
st.markdown("""
<style>
.stApp {
    background-color: #121212;
    color: #FFFFFF;
}
.stSidebar {
    background-color: #191414;
}
.stSidebar .stButton > button {
    color: #FFFFFF;
    background-color: #1DB954;
    border-radius: 20px;
    border: none;
}
.stSidebar .stButton > button:hover {
    background-color: #1ED760;
}
.metric-card {
    background-color: #282828;
    padding: 20px;
    border-radius: 10px;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_experiment_config():
    """Load experiment configuration."""
    # Try loading from results JSON first (for deployment)
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
        except Exception as e:
            pass
    
    # Fallback config (no database needed for deployment)
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


@st.cache_data
def load_user_metrics_from_db():
    """Load user metrics directly from database."""
    import duckdb
    
    if not DUCKDB_PATH.exists():
        # For demo/deployment without database
        return pd.DataFrame({
            'experiment_variant': ['Demo mode - database not available'],
            'user_id': [''],
            'avg_session_duration': [0],
            'avg_tracks_per_session': [0],
            'avg_skip_rate': [0],
            'sessions_per_user': [0],
            'retention_d1': [False],
            'artists_per_session': [0]
        })
    
    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    
    df = conn.execute("""
        SELECT
            experiment_variant,
            user_id,
            avg_session_duration,
            avg_tracks_per_session,
            avg_skip_rate,
            total_sessions as sessions_per_user,
            retention_d1,
            avg_unique_artists_per_session as artists_per_session
        FROM main_marts.fct_user_metrics
    """).fetchdf()
    
    conn.close()
    return df


def check_data_availability():
    """Check if required data is available."""
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    
    if not results_path.exists():
        st.error("Analysis results not found!")
        st.markdown("""
        ### Setup Required
        Run the analysis pipeline:
        1. `python scripts/load_data.py`
        2. `cd dbt_project && dbt seed && dbt run`
        3. `python analysis/experiment_analysis.py`
        """)
        return False
    
    return True


def main():
    """Main application entry point."""
    
    # Header
    st.title("🎵 Streaming Experiment Analyzer")
    st.markdown("**A/B Testing Platform for Music Product Features**")
    st.markdown("---")
    
    # Check data availability
    if not check_data_availability():
        return
    
    # Load data
    config = load_experiment_config()
    results = load_experiment_results()
    
    if config is None:
        st.error("⚠️ Experiment configuration not found. Please run `dbt seed`.")
        return
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <img src="https://www.scdn.co/i/_global/favicon.png" style="width: 40px; height: 40px;">
            <h2 style="color: #1DB954; margin-top: 10px;">Analytics Dashboard</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigate to:",
            ["📊 Overview", "📈 Metrics Analysis", "🚀 Ship Decision", "🔍 Data Explorer"],
            format_func=lambda x: x.split(" ", 1)[1]
        )
        
        st.markdown("---")
        st.info(f"**Experiment:** {EXPERIMENT_ID}")
        st.info(f"**Period:** {config['start_date']} to {config['end_date']}")
        
        if results:
            st.markdown("---")
            primary = results['metrics'][PRIMARY_METRIC]
            lift_pct = primary['relative_lift'] * 100
            st.metric(
                "Primary Metric Lift",
                f"{lift_pct:+.2f}%",
                delta=f"p-value: {primary['p_value']:.4f}"
            )
    
    # Main content area
    page_clean = page.split(" ", 1)[1] if " " in page else page
    
    if "Overview" in page:
        show_overview_page(config, results)
    elif "Metrics" in page:
        show_metrics_page(results)
    elif "Ship" in page:
        show_decision_page(results)
    elif "Data" in page:
        show_data_explorer()


def show_overview_page(config, results):
    """Display overview page."""
    from dashboard.components.recommendation import display_experiment_info
    from dashboard.components.metric_cards import display_summary_metrics
    from dashboard.components.charts import plot_lift_summary
    
    st.header("Experiment Overview")
    
    # Experiment info
    display_experiment_info(EXPERIMENT_ID, config)
    
    # Check if results exist
    if results is None:
        st.warning("Statistical analysis not yet run. Please run: `python analysis/experiment_analysis.py`")
        return
    
    # Summary metrics
    display_summary_metrics(results['metrics'])
    
    # Quick decision preview
    st.markdown("## Decision Preview")
    decision = results['decision']['decision']
    
    if 'SHIP' in decision and '✅' in decision:
        st.success(f"**Recommendation:** {decision}")
    elif '❌' in decision:
        st.error(f"**Recommendation:** {decision}")
    else:
        st.warning(f"**Recommendation:** {decision}")
    
    st.markdown(f"**Confidence:** {results['decision']['confidence']}")
    
    # Visualizations
    st.markdown("## Metric Comparisons")
    plot_lift_summary(results['metrics'])


def show_metrics_page(results):
    """Display detailed metrics analysis page."""
    from dashboard.components.charts import (
        plot_metric_comparison,
        plot_confidence_intervals,
        plot_effect_sizes
    )
    from dashboard.components.metric_cards import display_metric_card
    
    st.header("Detailed Metrics Analysis")
    
    if results is None:
        st.warning("Statistical analysis not yet run. Please run: `python analysis/experiment_analysis.py`")
        return
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Comparison", "Confidence Intervals", "Effect Sizes"])
    
    with tab1:
        st.markdown("### Metric Comparison")
        plot_metric_comparison(results['metrics'])
        
        # Detailed cards
        st.markdown("### Detailed Breakdown")
        
        # Primary metric first
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
        
        # Guardrail metrics
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
        
        # Metric selector
        metric_options = list(results['metrics'].keys())
        selected_metric = st.selectbox(
            "Select metric to visualize:",
            metric_options,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        plot_confidence_intervals(results['metrics'], selected_metric)
        
        # Interpretation
        result = results['metrics'][selected_metric]
        st.markdown("#### Interpretation")
        if result['variant_ci_lower'] > result['control_ci_upper']:
            st.success("✅ Confidence intervals don't overlap - strong evidence of difference")
        elif result['variant_ci_upper'] < result['control_ci_lower']:
            st.error("❌ Variant is significantly worse than control")
        else:
            st.info("ℹ️ Confidence intervals overlap - difference may not be significant")
    
    with tab3:
        st.markdown("### Effect Sizes (Cohen's d)")
        plot_effect_sizes(results['metrics'])
        
        st.markdown("""
        **Cohen's d Interpretation:**
        - < 0.2: Negligible effect
        - 0.2 - 0.5: Small effect
        - 0.5 - 0.8: Medium effect
        - > 0.8: Large effect
        """)


def show_decision_page(results):
    """Display ship decision page."""
    from dashboard.components.recommendation import (
        display_ship_decision,
        display_statistical_notes
    )
    
    st.header("Ship / Don't Ship Decision")
    
    if results is None:
        st.warning("Statistical analysis not yet run. Please run: `python analysis/experiment_analysis.py`")
        return
    
    # Display decision
    display_ship_decision(results['decision'])
    
    # Statistical notes
    display_statistical_notes()


def show_data_explorer():
    """Display raw data explorer page."""
    st.header("Data Explorer")
    
    if not DUCKDB_PATH.exists():
        st.info("📊 Data Explorer is only available when running locally with the full database.")
        st.markdown("""
        This demo uses pre-computed results. To explore the raw data:
        
        1. Clone the repository
        2. Follow the setup instructions in README
        3. Run the full pipeline locally
        """)
        return
    
    # Load data
    df = load_user_metrics_from_db()
    
    st.markdown(f"**Total Users:** {len(df):,}")
    
    # Group selector
    group = st.selectbox(
        "Select group:",
        ["All", "Control", "Variant B"]
    )
    
    if group == "Control":
        df_filtered = df[df['experiment_variant'] == 'control']
    elif group == "Variant B":
        df_filtered = df[df['experiment_variant'] == 'variant_b']
    else:
        df_filtered = df
    
    # Display statistics
    st.markdown("### Summary Statistics")
    st.dataframe(df_filtered.describe())
    
    # Display raw data
    st.markdown("### Raw Data")
    st.dataframe(
        df_filtered.head(100),
        use_container_width=True
    )
    
    # Download button
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Download Full Data (CSV)",
        data=csv,
        file_name=f"experiment_data_{group.lower().replace(' ', '_')}.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main()
