import json
import os
from datetime import datetime

class ReferenceService:
    """
    ReferenceService: Manages unique reference sequences for letters.
    Similar to ReferenceGenerator.ts.
    """
    
    REGISTRY_PATH = 'data/reference_registry.json'

    @classmethod
    def generate(cls, letter_type: str, dept_code: str = "PLAN") -> str:
        """
        Generates a unique reference number.
        Format: IOB/RO/{dept}/{year}/{seq}
        """
        if not os.path.exists('data'):
            os.makedirs('data')
            
        registry = {}
        if os.path.exists(cls.REGISTRY_PATH):
            with open(cls.REGISTRY_PATH, 'r') as f:
                registry = json.load(f)
        
        year = datetime.now().year
        key = f"{letter_type}_{year}"
        
        seq = registry.get(key, 0) + 1
        registry[key] = seq
        
        with open(cls.REGISTRY_PATH, 'w') as f:
            json.dump(registry, f)
            
        return f"IOB/RO/{dept_code}/{year}/{seq:03d}"
