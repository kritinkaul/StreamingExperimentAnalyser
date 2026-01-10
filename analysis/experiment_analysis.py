"""Statistical analysis for A/B experiments."""

import sys
from pathlib import Path
import duckdb
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import json

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from analysis.config import (
    DUCKDB_PATH, EXPERIMENT_ID, PRIMARY_METRIC,
    GUARDRAIL_METRICS, SIGNIFICANCE_LEVEL,
    GUARDRAIL_SIGNIFICANCE, MIN_EFFECT_SIZE,
    MAX_GUARDRAIL_DEGRADATION, CONFIDENCE_LEVEL
)
from analysis.utils import perform_ttest, format_p_value, interpret_effect_size


class ExperimentAnalyzer:
    """A/B experiment analyzer."""
    
    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        self.results = {}
        
    def load_user_metrics(self) -> pd.DataFrame:
        """Load user metrics from database."""
        query = """
            SELECT
                user_id,
                experiment_variant,
                avg_session_duration,
                avg_tracks_per_session,
                avg_skip_rate,
                total_sessions AS sessions_per_user,
                retention_d1,
                avg_unique_artists_per_session AS artists_per_session
            FROM main_marts.fct_user_metrics
        """
        return self.conn.execute(query).fetchdf()
    
    def analyze_metric(
        self,
        df: pd.DataFrame,
        metric_name: str,
        is_primary: bool = False
    ) -> Dict:
        """Analyze single metric between control and variant."""
        # Split by variant
        control = df[df['experiment_variant'] == 'control'][metric_name].dropna()
        variant = df[df['experiment_variant'] == 'variant_b'][metric_name].dropna()
        
        if metric_name == 'retention_d1':
            control = control.astype(float)
            variant = variant.astype(float)
        
        test_results = perform_ttest(control.values, variant.values)
        
        sig_level = SIGNIFICANCE_LEVEL if is_primary else GUARDRAIL_SIGNIFICANCE
        is_significant = test_results['p_value'] < sig_level
        meets_threshold = abs(test_results['relative_lift']) >= MIN_EFFECT_SIZE
        
        if not is_primary:
            if metric_name == 'avg_skip_rate':
                is_degraded = (test_results['relative_lift'] > MAX_GUARDRAIL_DEGRADATION 
                              and is_significant)
            else:
                is_degraded = (test_results['relative_lift'] < -MAX_GUARDRAIL_DEGRADATION 
                              and is_significant)
        else:
            is_degraded = False
        
        return {
            'metric_name': metric_name,
            'is_primary': is_primary,
            'is_significant': is_significant,
            'meets_threshold': meets_threshold,
            'is_degraded': is_degraded,
            **test_results
        }
    
    def analyze_all_metrics(self) -> Dict[str, Dict]:
        """Analyze all metrics (primary and guardrails)."""
        df = self.load_user_metrics()
        
        print(f"\n{'='*60}")
        print(f"Experiment Analysis: {self.experiment_id}")
        print(f"{'='*60}\n")
        
        print(f"Sample sizes:")
        print(f"  Control:   {len(df[df['experiment_variant'] == 'control']):,} users")
        print(f"  Variant B: {len(df[df['experiment_variant'] == 'variant_b']):,} users")
        
        results = {}
        
        # Analyze primary metric
        print(f"\n{'='*60}")
        print("PRIMARY METRIC ANALYSIS")
        print(f"{'='*60}")
        primary_result = self.analyze_metric(
            df, 
            PRIMARY_METRIC, 
            is_primary=True
        )
        results[PRIMARY_METRIC] = primary_result
        self._print_metric_results(primary_result)
        
        # Analyze guardrail metrics
        print(f"\n{'='*60}")
        print("GUARDRAIL METRICS ANALYSIS")
        print(f"{'='*60}")
        for metric in GUARDRAIL_METRICS:
            # Map config names to actual column names
            if metric == 'skip_rate':
                metric_col = 'avg_skip_rate'
            elif metric == 'retention_d1':
                metric_col = 'retention_d1'
            elif metric == 'sessions_per_user':
                metric_col = 'sessions_per_user'
            else:
                metric_col = metric
            
            guardrail_result = self.analyze_metric(
                df,
                metric_col,
                is_primary=False
            )
            results[metric] = guardrail_result
            self._print_metric_results(guardrail_result)
        
        self.results = results
        return results
    
    def _print_metric_results(self, result: Dict):
        """Pretty print metric analysis results."""
        ci_percent = int(CONFIDENCE_LEVEL * 100)
        print(f"\n{result['metric_name'].replace('_', ' ').title()}")
        print("-" * 40)
        print(f"  Control Mean:     {result['control_mean']:.4f}")
        print(f"  Variant Mean:     {result['variant_mean']:.4f}")
        print(f"  Relative Lift:    {result['relative_lift']*100:+.2f}%")
        print(f"  Absolute Diff:    {result['variant_mean'] - result['control_mean']:+.4f}")
        print(f"  p-value:          {format_p_value(result['p_value'])}")
        print(f"  Cohen's d:        {result['cohens_d']:.3f} ({interpret_effect_size(result['cohens_d'])})")
        print(f"  {ci_percent}% CI Control:   [{result['control_ci_lower']:.4f}, {result['control_ci_upper']:.4f}]")
        print(f"  {ci_percent}% CI Variant:   [{result['variant_ci_lower']:.4f}, {result['variant_ci_upper']:.4f}]")
        
        if result['is_primary']:
            sig_status = "YES" if result['is_significant'] else "NO"
            threshold_status = "YES" if result['meets_threshold'] else "NO"
            print(f"  Significant:      {sig_status} (p < {SIGNIFICANCE_LEVEL})")
            print(f"  Meets Threshold:  {threshold_status} (|lift| > {MIN_EFFECT_SIZE*100}%)")
        else:
            degraded_status = "YES" if result['is_degraded'] else "NO"
            print(f"  Degraded:         {degraded_status}")
    
    def make_ship_decision(self) -> Dict:
        """Make Ship/Don't Ship recommendation."""
        if not self.results:
            self.analyze_all_metrics()
        
        primary = self.results[PRIMARY_METRIC]
        
        # Check primary metric criteria
        primary_success = (
            primary['is_significant'] and
            primary['meets_threshold'] and
            primary['relative_lift'] > 0  # Must be positive lift
        )
        
        # Check guardrail metrics
        degraded_guardrails = [
            metric for metric, result in self.results.items()
            if not result['is_primary'] and result['is_degraded']
        ]
        
        # Make decision
        if primary_success and not degraded_guardrails:
            decision = "SHIP"
            confidence = "HIGH"
            reasoning = [
                f"Primary metric ({PRIMARY_METRIC}) shows significant positive lift of {primary['relative_lift']*100:.2f}%",
                f"Statistical significance achieved (p = {format_p_value(primary['p_value'])})",
                f"Effect size is {interpret_effect_size(primary['cohens_d'])} (Cohen's d = {primary['cohens_d']:.3f})",
                "No guardrail metrics degraded"
            ]
        elif primary_success and degraded_guardrails:
            decision = "DON'T SHIP"
            confidence = "MEDIUM"
            reasoning = [
                f"Primary metric shows positive lift of {primary['relative_lift']*100:.2f}%",
                f"BUT guardrail metric(s) degraded: {', '.join(degraded_guardrails)}",
                "Risk of harming user experience outweighs primary metric gains"
            ]
        elif primary['is_significant'] and primary['relative_lift'] < 0:
            decision = "DON'T SHIP"
            confidence = "HIGH"
            reasoning = [
                f"Primary metric shows NEGATIVE lift of {primary['relative_lift']*100:.2f}%",
                "Variant is worse than control"
            ]
        else:
            decision = "DON'T SHIP"
            confidence = "MEDIUM"
            reasoning = [
                f"Primary metric lift ({primary['relative_lift']*100:.2f}%) is not statistically significant",
                f"p-value = {format_p_value(primary['p_value'])} (threshold: {SIGNIFICANCE_LEVEL})",
                "Insufficient evidence to conclude variant is better"
            ]
            
            if not primary['meets_threshold']:
                reasoning.append(
                    f"Lift does not meet minimum threshold of {MIN_EFFECT_SIZE*100}%"
                )
        
        print(f"\n{'='*60}")
        print("SHIP DECISION")
        print(f"{'='*60}")
        print(f"\nDecision: {decision}")
        print(f"Confidence: {confidence}")
        print("\nReasoning:")
        for i, reason in enumerate(reasoning, 1):
            print(f"  {i}. {reason}")
        print(f"\n{'='*60}\n")
        
        return {
            'decision': decision,
            'confidence': confidence,
            'reasoning': reasoning,
            'primary_metric_lift': primary['relative_lift'],
            'primary_metric_pvalue': primary['p_value'],
            'degraded_guardrails': degraded_guardrails
        }
    
    def save_results(self, output_path: Path):
        """Save analysis results to JSON file."""
        output = {
            'experiment_id': self.experiment_id,
            'metrics': self.results,
            'decision': self.make_ship_decision()
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"Results saved to: {output_path}")
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("STREAMING EXPERIMENT ANALYZER")
    print("Statistical Analysis Module")
    print("="*60)
    
    # Check if database exists
    if not DUCKDB_PATH.exists():
        print(f"\nWARNING: Database not found at: {DUCKDB_PATH}")
        print("\nSetup required:")
        print("   1. Run: python scripts/load_data.py")
        print("   2. Run: cd dbt_project && dbt seed && dbt run")
        print("   3. Then run this script again")
        sys.exit(1)
    
    # Run analysis
    analyzer = ExperimentAnalyzer(EXPERIMENT_ID)
    
    try:
        # Analyze all metrics
        analyzer.analyze_all_metrics()
        
        # Make ship decision
        decision = analyzer.make_ship_decision()
        
        # Save results
        output_path = PROJECT_ROOT / "data" / "experiment_results.json"
        analyzer.save_results(output_path)
        
    finally:
        analyzer.close()
    
    print("\nAnalysis complete!")
    print("\nNext step:")
    print("  streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
