import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import json

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from analysis.config import CONFIDENCE_LEVEL

DUCKDB_PATH = PROJECT_ROOT / "data" / "streaming.duckdb"
EXPERIMENT_ID = "exp_001"
PRIMARY_METRIC = "avg_session_duration"
GUARDRAIL_METRICS = ["skip_rate", "sessions_per_user", "retention_d1"]

st.set_page_config(
    page_title="Streaming Experiment Analyzer",
    layout="wide"
)

st.markdown("""<style>
.stApp { background-color: #121212; color: #FFFFFF; }
.stSidebar { background-color: #191414; }
</style>""", unsafe_allow_html=True)


@st.cache_data
def load_experiment_config():
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
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    if not results_path.exists():
        return None
    with open(results_path) as f:
        return json.load(f)


@st.cache_data
def load_user_metrics_from_db():
    import duckdb
    if not DUCKDB_PATH.exists():
        return None
    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    df = conn.execute("""
        SELECT experiment_variant, user_id, avg_session_duration,
               avg_tracks_per_session, avg_skip_rate,
               total_sessions as sessions_per_user, retention_d1,
               avg_unique_artists_per_session as artists_per_session
        FROM main_marts.fct_user_metrics
    """).fetchdf()
    conn.close()
    return df


def check_data_availability():
    results_path = PROJECT_ROOT / "data" / "experiment_results.json"
    if not results_path.exists():
        st.error("Analysis results not found. Run: `python analysis/experiment_analysis.py`")
        return False
    return True


def main():
    st.title("Streaming Experiment Analyzer")
    st.markdown("**A/B Testing Platform for Music Product Features**")
    st.markdown("---")
    
    if not check_data_availability():
        return
    
    config = load_experiment_config()
    results = load_experiment_results()
    
    if not config:
        st.error("Configuration not found.")
        return
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="12" fill="#1DB954"/>
                <path d="M17.5 10.4C14.4 8.5 9.4 8.3 6.7 9.2C6.3 9.3 5.9 9.1 5.8 8.7C5.7 8.3 5.9 7.9 6.3 7.8C9.4 6.8 14.8 7 18.3 9.1C18.7 9.3 18.8 9.8 18.6 10.2C18.4 10.5 17.9 10.6 17.5 10.4ZM17.4 13.1C17.2 13.4 16.8 13.5 16.5 13.3C13.9 11.7 10.1 11.3 6.8 12.3C6.4 12.4 6 12.2 5.9 11.8C5.8 11.4 6 11 6.4 10.9C10.1 9.8 14.3 10.3 17.2 12.1C17.5 12.3 17.6 12.7 17.4 13.1ZM16.4 15.7C16.2 16 15.9 16.1 15.6 15.9C13.4 14.5 10.6 14.2 6.9 15C6.6 15.1 6.3 14.9 6.2 14.6C6.1 14.3 6.3 14 6.6 13.9C10.6 13.1 13.7 13.4 16.1 15C16.4 15.2 16.5 15.5 16.4 15.7Z" fill="white"/>
            </svg>
            <h2 style="color: #1DB954; margin-top: 10px;">Analytics Dashboard</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigate to:",
            ["Overview", "Metrics Analysis", "Ship Decision", "Data Explorer"]
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
    
    if "Overview" in page:
        show_overview_page(config, results)
    elif "Metrics" in page:
        show_metrics_page(results)
    elif "Ship" in page:
        show_decision_page(results)
    elif "Data" in page:
        show_data_explorer()


def show_overview_page(config, results):
    from dashboard.components.recommendation import display_experiment_info
    from dashboard.components.metric_cards import display_summary_metrics
    from dashboard.components.charts import plot_lift_summary
    
    st.header("Experiment Overview")
    display_experiment_info(EXPERIMENT_ID, config)
    
    if not results:
        st.warning("Run analysis first: `python analysis/experiment_analysis.py`")
        return
    
    display_summary_metrics(results['metrics'])
    
    st.markdown("## Decision Preview")
    decision = results['decision']['decision']
    if decision == 'SHIP':
        st.success(f"**Recommendation:** {decision}")
    elif 'DON\'T SHIP' in decision or "DON'T SHIP" in decision:
        if results['decision']['confidence'] == 'HIGH':
            st.error(f"**Recommendation:** {decision}")
        else:
            st.warning(f"**Recommendation:** {decision}")
    else:
        st.warning(f"**Recommendation:** {decision}")
    
    st.markdown(f"**Confidence:** {results['decision']['confidence']}")
    st.markdown("## Metric Comparisons")
    plot_lift_summary(results['metrics'])


def show_metrics_page(results):
    from dashboard.components.charts import (
        plot_metric_comparison,
        plot_confidence_intervals,
        plot_effect_sizes
    )
    from dashboard.components.metric_cards import display_metric_card
    
    st.header("Detailed Metrics Analysis")
    
    if not results:
        st.warning("Run analysis first: `python analysis/experiment_analysis.py`")
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
        ci_percent = int(CONFIDENCE_LEVEL * 100)
        st.markdown(f"### {ci_percent}% Confidence Intervals")
        metric_options = list(results['metrics'].keys())
        selected_metric = st.selectbox(
            "Select metric:",
            metric_options,
            format_func=lambda x: x.replace('_', ' ').title()
        )
        plot_confidence_intervals(results['metrics'], selected_metric)
    
    with tab3:
        st.markdown("### Effect Sizes (Cohen's d)")
        plot_effect_sizes(results['metrics'])


def show_decision_page(results):
    from dashboard.components.recommendation import display_ship_decision, display_statistical_notes
    
    st.header("Ship / Don't Ship Decision")
    
    if not results:
        st.warning("Run analysis first: `python analysis/experiment_analysis.py`")
        return
    
    display_ship_decision(results['decision'])
    display_statistical_notes()


def show_data_explorer():
    st.header("Data Explorer")
    
    df = load_user_metrics_from_db()
    
    if df is not None:
        st.markdown(f"**Total Users:** {len(df):,}")
        
        group = st.selectbox("Select group:", ["All", "Control", "Variant B"])
        
        if group == "Control":
            df_filtered = df[df['experiment_variant'] == 'control']
        elif group == "Variant B":
            df_filtered = df[df['experiment_variant'] == 'variant_b']
        else:
            df_filtered = df
        
        st.markdown("### Summary Statistics")
        st.dataframe(df_filtered.describe(), use_container_width=True)
        
        st.markdown("### Raw Data")
        st.dataframe(df_filtered.head(100), use_container_width=True)
        
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"experiment_data_{group.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        results = load_experiment_results()
        if not results:
            st.error("No data available.")
            return
        
        metrics_data = results['metrics']
        summary_rows = []
        
        for metric_name, metric_data in metrics_data.items():
            summary_rows.append({
                'Metric': metric_name.replace('_', ' ').title(),
                'Control Mean': f"{metric_data['control_mean']:.2f}",
                'Variant Mean': f"{metric_data['variant_mean']:.2f}",
                'Relative Lift': f"{metric_data['relative_lift']*100:+.2f}%",
                'P-Value': f"{metric_data['p_value']:.4f}",
                'Significant': metric_data['is_significant'],
                'Control N': metric_data['sample_size_control'],
                'Variant N': metric_data['sample_size_variant']
            })
        
        df = pd.DataFrame(summary_rows)
        
        st.markdown("### Metrics Summary")
        st.dataframe(df, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Control Users", df['Control N'].iloc[0])
        with col2:
            st.metric("Variant Users", df['Variant N'].iloc[0])
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Summary CSV",
            data=csv,
            file_name="experiment_summary.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
