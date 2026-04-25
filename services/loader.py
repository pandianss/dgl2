import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from .mapper import MetricMapper

class MISLoader:
    """
    MISLoader: Handles Excel/CSV ingestion and normalization.
    Ported aliases and robust date parsing from dindigul project.
    """
    
    SOL_HEADER_ALIASES = {'sol', 'sol id', 'solid', 'branch code', 'branchcode', 'branch'}
    DATE_HEADER_ALIASES = {'date', 'business date', 'businessdate', 'as on', 'ason'}

    @staticmethod
    def clean_amount(val: Any) -> float:
        """Normalizes an amount by removing commas and handling non-numeric values."""
        if pd.isna(val) or val == '':
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        
        # Remove symbols but keep decimals and signs
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def parse_business_date(raw: Any) -> Optional[datetime]:
        """Robust date parsing for Excel/CSV formats."""
        if pd.isna(raw):
            return None
            
        if isinstance(raw, datetime):
            return raw
            
        if isinstance(raw, (int, float)):
            # Handle YYYYMMDD
            if 19000000 < raw < 21000000:
                s = str(int(raw))
                return datetime.strptime(s, '%Y%m%d')
            # Handle Excel serial dates (approximate)
            if 36000 < raw < 73000:
                return datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(raw))

        str_val = str(raw).strip()
        # Common formats
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y', '%Y%m%d'):
            try:
                return datetime.strptime(str_val, fmt)
            except ValueError:
                continue
                
        return None

    @classmethod
    def find_key(cls, columns: List[str], aliases: set) -> Optional[str]:
        """Finds a column name that matches one of the aliases."""
        for col in columns:
            if col.strip().lower() in aliases:
                return col
        return None

    @classmethod
    def process_file(cls, file_path_or_buffer) -> Tuple[pd.DataFrame, List[str]]:
        """
        Processes an uploaded file into a standardized Fact DataFrame.
        Returns (DataFrame, Errors)
        """
        errors = []
        try:
            # Read first sheet
            if hasattr(file_path_or_buffer, 'name') and file_path_or_buffer.name.endswith('.csv'):
                df = pd.read_csv(file_path_or_buffer)
            else:
                df = pd.read_excel(file_path_or_buffer)
        except Exception as e:
            return pd.DataFrame(), [f"Failed to read file: {str(e)}"]

        if df.empty:
            return pd.DataFrame(), ["File is empty"]

        sol_col = cls.find_key(df.columns, cls.SOL_HEADER_ALIASES)
        date_col = cls.find_key(df.columns, cls.DATE_HEADER_ALIASES)

        if not sol_col:
            errors.append("Could not find SOL column (aliases: sol, branch code, etc.)")
        if not date_col:
            errors.append("Could not find Date column (aliases: business date, as on, etc.)")

        if errors:
            return pd.DataFrame(), errors

        # Standardize SOL and Date
        df['sol_standard'] = df[sol_col].apply(lambda x: str(x).strip().zfill(4) if pd.notna(x) else None)
        df['date_standard'] = df[date_col].apply(cls.parse_business_date)
        
        # Drop rows with missing keys
        initial_count = len(df)
        df = df.dropna(subset=['sol_standard', 'date_standard'])
        if len(df) < initial_count:
            errors.append(f"Dropped {initial_count - len(df)} rows due to invalid SOL or Date")

        # Melt to Fact Format: sol, date, metric, value
        metric_cols = [c for c in df.columns if c not in [sol_col, date_col, 'sol_standard', 'date_standard']]
        
        facts = []
        for _, row in df.iterrows():
            sol = row['sol_standard']
            dt = row['date_standard']
            
            row_facts = {}
            for col in metric_cols:
                metric_code = MetricMapper.normalize_header(col)
                if metric_code:
                    val = cls.clean_amount(row[col])
                    if val != 0:
                        row_facts[metric_code] = row_facts.get(metric_code, 0.0) + val
            
            # Add calculated metrics
            calculated = MetricMapper.get_calculated_metrics(row_facts)
            row_facts.update(calculated)
            
            for m, v in row_facts.items():
                facts.append({
                    'sol': sol,
                    'date': dt,
                    'metric': m,
                    'value': v
                })

        fact_df = pd.DataFrame(facts)
        return fact_df, errors
