import pandas as pd
from typing import List, Dict

class ExceptionEngine:
    """
    ExceptionEngine: Scans facts for business rule violations.
    Ported from legacy OperationalRiskOrchestrator logic.
    """
    
    @staticmethod
    def scan(fact_df: pd.DataFrame, branch_metadata: pd.DataFrame) -> pd.DataFrame:
        """
        Scans a batch of facts and returns a list of exceptions.
        """
        exceptions = []
        
        # Group by SOL and Date to check branch-level rules
        for (sol, date), group in fact_df.groupby(['sol', 'date']):
            metrics = group.set_index('metric')['value'].to_dict()
            
            # Rule 1: Cash over CRL
            crl = metrics.get('CASH_CRL', 0)
            total_cash = metrics.get('CASH_TOTAL', 0)
            if total_cash > crl and crl > 0:
                exceptions.append({
                    'sol': sol,
                    'date': date,
                    'type': 'CASH_EXCESS',
                    'severity': 'CRITICAL' if (total_cash - crl) > 10 else 'HIGH',
                    'message': f"Cash possession (₹{total_cash:,.2f}L) exceeds CRL (₹{crl:,.2f}L) by ₹{total_cash-crl:,.2f}L",
                    'metric_impact': total_cash - crl
                })
            
            # Rule 2: CD Ratio Threshold
            cd_ratio = metrics.get('CD_Ratio', 0)
            if cd_ratio > 75:
                exceptions.append({
                    'sol': sol,
                    'date': date,
                    'type': 'LIQUIDITY_RISK',
                    'severity': 'HIGH' if cd_ratio > 85 else 'MEDIUM',
                    'message': f"CD Ratio is at {cd_ratio}%, exceeding the 75% stability threshold",
                    'metric_impact': cd_ratio
                })

            # Rule 3: Negative Profit (Branch P&L)
            pl = metrics.get('Branch_PL', 0)
            if pl < 0:
                exceptions.append({
                    'sol': sol,
                    'date': date,
                    'type': 'PROFIT_DEFICIT',
                    'severity': 'HIGH',
                    'message': f"Branch is operating at a deficit of ₹{abs(pl):,.2f}L",
                    'metric_impact': abs(pl)
                })

            # Rule 4: CASA Erosion
            casa_pct = metrics.get('CASA_PCT', 0)
            if casa_pct < 30:
                exceptions.append({
                    'sol': sol,
                    'date': date,
                    'type': 'DEPOSIT_MIX',
                    'severity': 'MEDIUM',
                    'message': f"Low CASA mix at {casa_pct}% (Target > 40%)",
                    'metric_impact': casa_pct
                })

        return pd.DataFrame(exceptions)
