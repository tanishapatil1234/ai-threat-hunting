"""
Explainability 

This provides explainable outputs for query generation:
- Hypothesis interpretation
- Query reasoning
- Assumptions made
- Confidence scoring with explanations
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class Explanation:
    """ explanation for a generated query"""
    hypothesis_id: str
    hypothesis_text: str
    interpretation: str
    query_reasoning: str
    assumptions: List[str]
    confidence: float
    confidence_explanation: str
    query_description: str
    result_summary: Dict[str, Any] = None


def generate_explanation(
    hypothesis_id: str,
    hypothesis_text: str,
    query_description: str,
    reasoning: str,
    assumptions: List[str],
    confidence: float,
    result_df=None
) -> Explanation:
    """
    Generate a complete explanation for a query.
    Returns:
        Explanation object
    """
    
    interpretation = f"This hypothesis is asking for: {hypothesis_text}"
    
    # confidence explanation
    if confidence >= 0.9:
        conf_explanation = f"I'm {int(confidence*100)}% confident this query is correct because I found clear matching patterns for event names, sources, and error conditions."
    elif confidence >= 0.7:
        conf_explanation = f"I'm {int(confidence*100)}% confident this query is correct because I matched most key patterns, though some assumptions were needed."
    else:
        conf_explanation = f"I'm {int(confidence*100)}% confident this query is correct, but the hypothesis was ambiguous and required significant interpretation."
    
    # result summary if result_df is provided
    result_summary = None
    if result_df is not None:
        result_summary = {
            'row_count': len(result_df),
            'unique_ips': result_df['sourceIPAddress'].nunique() if 'sourceIPAddress' in result_df.columns else 0,
            'unique_users': result_df['userIdentityuserName'].nunique() if 'userIdentityuserName' in result_df.columns else 0,
            'date_range': {
                'min': str(result_df['eventTime'].min()) if 'eventTime' in result_df.columns else None,
                'max': str(result_df['eventTime'].max()) if 'eventTime' in result_df.columns else None
            } if 'eventTime' in result_df.columns else None
        }
    
    return Explanation(
        hypothesis_id=hypothesis_id,
        hypothesis_text=hypothesis_text,
        interpretation=interpretation,
        query_reasoning=reasoning,
        assumptions=assumptions,
        confidence=confidence,
        confidence_explanation=conf_explanation,
        query_description=query_description,
        result_summary=result_summary
    )


def format_explanation(explanation: Explanation) -> str:
    """    
    Args: explanation: Explanation object
    Returns: Formatted string
    """
    lines = [
        f"Hypothesis ID: {explanation.hypothesis_id}",
        f"Hypothesis: {explanation.hypothesis_text}",
        "",
        "=== Interpretation ===",
        explanation.interpretation,
        "",
        "=== Query Reasoning ===",
        explanation.query_reasoning,
        "",
        "=== Assumptions Made ===",
    ]
    
    if explanation.assumptions:
        for i, assumption in enumerate(explanation.assumptions, 1):
            lines.append(f"{i}. {assumption}")
    else:
        lines.append("No explicit assumptions were made.")
    
    lines.extend([
        "",
        "=== Confidence Score ===",
        f"Confidence: {explanation.confidence:.2%}",
        explanation.confidence_explanation,
        "",
        "=== Query Description ===",
        explanation.query_description,
    ])
    
    if explanation.result_summary:
        lines.extend([
            "",
            "=== Result Summary ===",
            f"Rows returned: {explanation.result_summary['row_count']}",
            f"Unique source IPs: {explanation.result_summary['unique_ips']}",
            f"Unique users: {explanation.result_summary['unique_users']}",
        ])
        if explanation.result_summary.get('date_range'):
            dr = explanation.result_summary['date_range']
            if dr.get('min') and dr.get('max'):
                lines.append(f"Date range: {dr['min']} to {dr['max']}")
    
    return "\n".join(lines)


def save_explanations(explanations: List[Explanation], output_path: str):
    """
    Save explanations to JSON file.
    
    Args: explanations: List of Explanation objects, output_path
    """
    explanations_dict = []
    for exp in explanations:
        exp_dict = {
            'hypothesis_id': exp.hypothesis_id,
            'hypothesis_text': exp.hypothesis_text,
            'interpretation': exp.interpretation,
            'query_reasoning': exp.query_reasoning,
            'assumptions': exp.assumptions,
            'confidence': exp.confidence,
            'confidence_explanation': exp.confidence_explanation,
            'query_description': exp.query_description,
            'result_summary': exp.result_summary
        }
        explanations_dict.append(exp_dict)
    
    with open(output_path, 'w') as f:
        json.dump(explanations_dict, f, indent=2, default=str)

