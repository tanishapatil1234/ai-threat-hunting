
"""
Evaluation 
- Precision, Recall, F1 Score
- Accuracy
- Result comparison with expected outcomes
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import json
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class EvaluationMetrics:
    """ single hypothesis evaluation"""
    hypothesis_id: str
    hypothesis_text: str
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    expected_count: int
    actual_count: int
    matched_rows: int
    unmatched_expected: int
    unmatched_actual: int


@dataclass
class OverallMetrics:
    """overall evaluation metrics across all hypotheses"""
    total_hypotheses: int
    average_precision: float
    average_recall: float
    average_f1: float
    average_accuracy: float
    weighted_f1: float
    per_hypothesis_metrics: List[EvaluationMetrics]


def load_expected_outcomes(outcomes_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load expected outcomes from JSON file.
    Args: path to hypotheses_outcomes.json
    Returns: dictionary mapping hypothesis_id to expected results
    """
    with open(outcomes_path, 'r') as f:
        outcomes = json.load(f)
    
    if isinstance(outcomes, list) and len(outcomes) > 0:
        return outcomes[0]
    return outcomes


def get_expected_row_indices(hypothesis_id: str, expected_outcomes: Dict[str, Dict[str, Any]]) -> set:
    """
    Extract expected row indices for a hypothesis.
    Args: hypothesis_id: ID of the hypothesis , expected_outcomes: Loaded outcomes dictionary
    Returns: set of expected row indices (as strings)
    """
    if hypothesis_id not in expected_outcomes:
        return set()
    
    hypothesis_data = expected_outcomes[hypothesis_id]
    
    row_indices = set()
    for field, values in hypothesis_data.items():
        if isinstance(values, dict):
            row_indices.update(values.keys())
    
    return row_indices


def calculate_metrics(
    actual_df: pd.DataFrame,
    expected_indices: set,
    df_index_col: Optional[str] = None,
    total_dataset_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate precision, recall, F1, and accuracy metrics.
    
    Args:
        actual_df: DataFrame with actual query results
        expected_indices: Set of expected row indices (as strings)
        df_index_col: Column name that contains the index (if different from DataFrame index)
        total_dataset_size: Total number of rows in the full dataset (needed for true_negatives)
    
    Returns:
        Dictionary with metrics
    """
    
    if df_index_col and df_index_col in actual_df.columns:
        actual_indices = set(actual_df[df_index_col].astype(str))
    else:
        actual_indices = set(actual_df.index.astype(str))
    
    expected_indices = {str(idx) for idx in expected_indices}
    
    # operations
    true_positives = len(actual_indices & expected_indices)
    false_positives = len(actual_indices - expected_indices)
    false_negatives = len(expected_indices - actual_indices)
    
    # Calculate true negatives : TN = Total Dataset Size - (TP + FP + FN)
    if total_dataset_size is not None:
        true_negatives = total_dataset_size - (true_positives + false_positives + false_negatives)
        true_negatives = max(0, true_negatives)
    else:
        true_negatives = 0
    
    # calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    # Calculate accuracy
    if total_dataset_size is not None and total_dataset_size > 0:
        accuracy = (true_positives + true_negatives) / total_dataset_size
    else:
        # Approximate accuracy when total size unknown
        total_relevant = len(expected_indices)
        total_retrieved = len(actual_indices)
        accuracy = true_positives / max(total_relevant, total_retrieved) if max(total_relevant, total_retrieved) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'accuracy': accuracy,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'true_negatives': true_negatives,
        'expected_count': len(expected_indices),
        'actual_count': len(actual_indices),
        'matched_rows': true_positives,
        'unmatched_expected': false_negatives,
        'unmatched_actual': false_positives
    }


def evaluate_hypothesis(
    hypothesis_id: str,
    hypothesis_text: str,
    actual_df: pd.DataFrame,
    expected_outcomes: Dict[str, Dict[str, Any]],
    df_index_col: Optional[str] = None,
    total_dataset_size: Optional[int] = None
) -> EvaluationMetrics:
    """
    Evaluate a single hypothesis query result.
    
    Args:
        hypothesis_id: ID of the hypothesis
        hypothesis_text: Text of the hypothesis
        actual_df: DataFrame with actual query results
        expected_outcomes: Loaded outcomes dictionary
        df_index_col: Column name for row index matching
        total_dataset_size: Total number of rows in the full dataset (needed for true_negatives)
    
    Returns:
        EvaluationMetrics object
    """
    expected_indices = get_expected_row_indices(hypothesis_id, expected_outcomes)
    
    # Calculate metrics
    metrics_dict = calculate_metrics(actual_df, expected_indices, df_index_col, total_dataset_size)
    
    return EvaluationMetrics(
        hypothesis_id=hypothesis_id,
        hypothesis_text=hypothesis_text,
        **metrics_dict
    )


def evaluate_all(
    results: List[Dict[str, Any]],
    expected_outcomes_path: str,
    df_index_col: Optional[str] = None,
    total_dataset_size: Optional[int] = None
) -> OverallMetrics:
    """
    Evaluate all hypotheses and compute overall metrics.
    
    Args:
        results: List of dicts with keys: hypothesis_id, hypothesis_text, result_df
        expected_outcomes_path: Path to hypotheses_outcomes.json
        df_index_col: Column name for row index matching
        total_dataset_size: Total number of rows in the full dataset (needed for true_negatives)
    
    Returns:
        OverallMetrics object
    """
    expected_outcomes = load_expected_outcomes(expected_outcomes_path)
    
    per_hypothesis_metrics = []
    for result in results:
        metrics = evaluate_hypothesis(
            hypothesis_id=result['hypothesis_id'],
            hypothesis_text=result['hypothesis_text'],
            actual_df=result['result_df'],
            expected_outcomes=expected_outcomes,
            df_index_col=df_index_col,
            total_dataset_size=total_dataset_size
        )
        per_hypothesis_metrics.append(metrics)
    
    # calculate overall metrics
    precisions = [m.precision for m in per_hypothesis_metrics]
    recalls = [m.recall for m in per_hypothesis_metrics]
    f1_scores = [m.f1_score for m in per_hypothesis_metrics]
    accuracies = [m.accuracy for m in per_hypothesis_metrics]
    
    # weighted F1 (by expected count)
    total_expected = sum(m.expected_count for m in per_hypothesis_metrics)
    if total_expected > 0:
        weighted_f1 = sum(m.f1_score * m.expected_count for m in per_hypothesis_metrics) / total_expected
    else:
        weighted_f1 = np.mean(f1_scores) if f1_scores else 0.0
    
    return OverallMetrics(
        total_hypotheses=len(per_hypothesis_metrics),
        average_precision=np.mean(precisions) if precisions else 0.0,
        average_recall=np.mean(recalls) if recalls else 0.0,
        average_f1=np.mean(f1_scores) if f1_scores else 0.0,
        average_accuracy=np.mean(accuracies) if accuracies else 0.0,
        weighted_f1=weighted_f1,
        per_hypothesis_metrics=per_hypothesis_metrics
    )


def save_evaluation_results(metrics: OverallMetrics, output_path: str):
    """
    Save evaluation results to JSON file.
    
    Args:
        metrics: OverallMetrics object
        output_path: Path to save JSON file
    """
    results_dict = {
        'overall': {
            'total_hypotheses': metrics.total_hypotheses,
            'average_precision': metrics.average_precision,
            'average_recall': metrics.average_recall,
            'average_f1': metrics.average_f1,
            'average_accuracy': metrics.average_accuracy,
            'weighted_f1': metrics.weighted_f1
        },
        'per_hypothesis': [asdict(m) for m in metrics.per_hypothesis_metrics]
    }
    
    with open(output_path, 'w') as f:
        json.dump(results_dict, f, indent=2, default=str)

