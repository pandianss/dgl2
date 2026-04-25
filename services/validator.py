import pandas as pd
from typing import List, Dict, Tuple

class DataValidator:
    """
    DataValidator: Enforces business rules and data integrity.
    """
    
    REQUIRED_METRICS = [
        'SB', 'CD', 'TD', 'CASH_HAND', 'CASH_ATM', 'Adv', 'Bus'
    ]

    @classmethod
    def validate_ingestion(cls, fact_df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validates the ingested Fact DataFrame.
        """
        issues = []
        if fact_df.empty:
            return False, ["No data found in file"]

        # Check for missing branches
        unique_sols = fact_df['sol'].unique()
        if len(unique_sols) == 0:
            issues.append("No valid SOL IDs found")

        # Check for missing metrics across the entire batch
        present_metrics = set(fact_df['metric'].unique())
        missing_critical = [m for m in cls.REQUIRED_METRICS if m not in present_metrics]
        if missing_critical:
            issues.append(f"Missing critical metrics in file: {', '.join(missing_critical)}")

        # Check for potential duplicates (same SOL, Date, Metric)
        dupes = fact_df.duplicated(subset=['sol', 'date', 'metric']).sum()
        if dupes > 0:
            issues.append(f"Found {dupes} duplicate entries. These will be aggregated.")

        return len(issues) == 0, issues

    @classmethod
    def get_summary_stats(cls, fact_df: pd.DataFrame) -> Dict:
        """Returns high-level statistics for the ingestion report."""
        if fact_df.empty:
            return {}
            
        return {
            'total_rows': len(fact_df),
            'unique_branches': int(fact_df['sol'].nunique()),
            'dates': [d.strftime('%Y-%m-%d') for d in fact_df['date'].unique()],
            'metrics_captured': int(fact_df['metric'].nunique()),
            'total_business': float(fact_df[fact_df['metric'] == 'Bus']['value'].sum())
        }
