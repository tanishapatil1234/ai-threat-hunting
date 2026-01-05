"""
Utility functions for loading data and hypotheses.
"""

import pandas as pd
import json
from typing import List, Dict, Any


def load_cloudtrail_dataframe(csv_path: str) -> pd.DataFrame:
    """
    Load CloudTrail data as pandas DataFrame.
    """
    print(f"Loading CloudTrail data from {csv_path}...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def load_hypotheses(hypotheses_path: str) -> List[Dict[str, Any]]:
    """
    Load hypotheses from JSON file.
    Returns:
        List of hypothesis dictionaries
    """
    with open(hypotheses_path, 'r') as f:
        hypotheses = json.load(f)
    return hypotheses


def load_hypotheses_outcomes(outcomes_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load expected outcomes from JSON file.
    Returns: Dictionary mapping hypothesis_id to expected results
    """
    with open(outcomes_path, 'r') as f:
        outcomes = json.load(f)
    
    # a list with a single dict containing all hypotheses
    if isinstance(outcomes, list) and len(outcomes) > 0:
        return outcomes[0]
    return outcomes
