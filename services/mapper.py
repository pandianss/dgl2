import re
import pandas as pd
from typing import Dict, Optional, List

class MetricMapper:
    """
    MetricMapper: Ported from dindigul legacy project.
    Centralized mapping between external Excel headers and internal Registry Codes.
    """
    
    SKIP_PATTERNS = [
        r'^s\s*no\.?$',
        r'^sol$',
        r'^date$',
        r'^branch$',
        r'^total$',
        r'^remark.*$'
    ]
    
    MAPPING = {
        # Advance Products
        'agri jl': 'Agri_JL',
        'retail jl': 'RETAIL_JL',
        'gold': 'Gold',
        'housing': 'HL',
        'vehicle': 'VL',
        'personal': 'PersonalLoan',
        'mortgage': 'Mort',
        'education': 'EL',
        'liquirent': 'Liq',
        'other retail': 'OthRet',
        'total retail': 'Core Ret',
        'core retail': 'Core Ret',
        'retail total': 'Core Ret',
        'msme': 'MSME',
        'shg': 'SHG',
        'kcc': 'KCC',
        'govt spon': 'Gov',
        'got spon': 'Gov',
        'oth schematic': 'OthSch',
        'core agri': 'Core_Agri',
        'adv': 'Adv',
        'advances': 'Adv',
        'total advances': 'Adv',
        'npa': 'NPA',
        'mudra': 'Mudra',
        'retail td': 'Ret_TD',

        # Deposits
        'sb': 'SB',
        'savings': 'SB',
        'sb deposits': 'SB',
        'cd': 'CD',
        'current': 'CD',
        'cd deposits': 'CD',
        'td': 'TD',
        'term': 'TD',
        'td deposits': 'TD',
        'total dep': 'Dep',
        'total deposits': 'Dep',
        'dep': 'Dep',
        'deposits': 'Dep',
        'bulk dep': 'Bulk_Dep',

        # Cash Holdings
        'cash on hand': 'CASH_HAND',
        'atm cash': 'CASH_ATM',
        'bc cash': 'CASH_BC',
        'bna cash': 'CASH_BNA',
        'total cash': 'CASH_TOTAL',
        'crl': 'CASH_CRL',
        'excess': 'CASH_EXCESS',

        # Profitability & Recovery
        'pl': 'Branch_PL',
        'profit': 'Branch_PL',
        'loss': 'Branch_PL',
        'rec q1': 'REC_Q1',
        'rec q2': 'REC_Q2',
        'rec q3': 'REC_Q3',
        'rec q4': 'REC_Q4',

        # Business
        'bus': 'Bus',
        'business': 'Bus',
        'total business': 'Bus'
    }

    @classmethod
    def normalize_header(cls, header: str) -> Optional[str]:
        """Normalizes an Excel header to a Registry Code."""
        if not header:
            return None
            
        # Aggressive normalization: remove non-alphanumeric/space, trim, lowercase
        normalized = re.sub(r'[^\w\s]', '', str(header))
        normalized = re.sub(r'\s+', ' ', normalized).strip().lower()
        
        # Check skip patterns
        for pattern in cls.SKIP_PATTERNS:
            if re.match(pattern, normalized, re.IGNORECASE):
                return None
        
        code = cls.MAPPING.get(normalized)
        if code:
            return code
            
        # Fallback for unmapped columns
        return normalized.upper().replace(' ', '_')

    @classmethod
    def get_calculated_metrics(cls, fact_map: Dict[str, float]) -> Dict[str, float]:
        """Identifies special metrics that need post-ingestion calculation."""
        calculated = {}
        
        def get_val(m: str) -> float:
            return fact_map.get(m, 0.0)

        # 1. Core Agri = SHG + KCC + Gov + OthSch (Fallback to original if sum is zero)
        core_agri_comp = get_val('SHG') + get_val('KCC') + get_val('Gov') + get_val('OthSch')
        core_agri = core_agri_comp if core_agri_comp > 0 else get_val('Core_Agri')
        calculated['Core_Agri'] = core_agri

        # 2. MSME = Mudra
        msme = get_val('Mudra') if get_val('Mudra') > 0 else get_val('MSME')
        calculated['MSME'] = msme

        # 3. Gold = Agri_JL + RETAIL_JL
        gold_comp = get_val('Agri_JL') + get_val('RETAIL_JL')
        gold = gold_comp if gold_comp > 0 else get_val('Gold')
        calculated['Gold'] = gold

        # 4. Core Ret = PersonalLoan + Mort + EL + Liq + OthRet + HL + VL
        core_ret_comp = (get_val('PersonalLoan') + get_val('Mort') + get_val('EL') + 
                        get_val('Liq') + get_val('OthRet') + get_val('HL') + get_val('VL'))
        core_ret = core_ret_comp if core_ret_comp > 0 else get_val('Core Ret')
        calculated['Core Ret'] = core_ret

        # 5. Adv = Core_Agri + Core Ret + MSME + Gold
        adv_comp = core_agri + core_ret + msme + gold
        adv = adv_comp if adv_comp > 0 else get_val('Adv')
        calculated['Adv'] = adv

        # 6. CASA = SB + CD
        casa_comp = get_val('SB') + get_val('CD')
        casa = casa_comp if casa_comp > 0 else get_val('CASA')
        calculated['CASA'] = casa

        # 7. TD = Ret_TD + Bulk_Dep
        td_comp = get_val('Ret_TD') + get_val('Bulk_Dep')
        td = td_comp if td_comp > 0 else get_val('TD')
        calculated['TD'] = td

        # 8. Deposits = SB + CD + TD
        dep_comp = get_val('SB') + get_val('CD') + td
        dep = dep_comp if dep_comp > 0 else get_val('Dep')
        calculated['Dep'] = dep

        # 9. Business = Adv + Deposits
        calculated['Bus'] = adv + dep

        # 10. CASH_TOTAL = CASH_HAND + CASH_ATM + CASH_BC + CASH_BNA
        cash_comp = get_val('CASH_HAND') + get_val('CASH_ATM') + get_val('CASH_BC') + get_val('CASH_BNA')
        calculated['CASH_TOTAL'] = cash_comp if cash_comp > 0 else get_val('CASH_TOTAL')

        # 11. Recovery = REC_Q1 + REC_Q2 + REC_Q3 + REC_Q4
        rec_comp = get_val('REC_Q1') + get_val('REC_Q2') + get_val('REC_Q3') + get_val('REC_Q4')
        calculated['Recovery'] = rec_comp if rec_comp > 0 else get_val('Recovery')

        # 12. Ratios
        calculated['CD_Ratio'] = 0.0 if total_dep == 0 else round((adv / total_dep * 100), 2)
        calculated['CASA_PCT'] = 0.0 if total_dep == 0 else round((casa / total_dep * 100), 2)

        return calculated
