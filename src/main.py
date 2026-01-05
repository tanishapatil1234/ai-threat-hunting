"""
Main Entry Point for AI Threat Hunting Query Generation & Evaluation System

This script runs the complete evaluation pipeline:
1. Loads hypotheses and CloudTrail data
2. Generates queries for each hypothesis
3. Executes queries and collects results
4. Evaluates results against expected outcomes
5. Generates explanations and reports
"""

import os
import sys
import pandas as pd
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query_generator import generate_query
from evaluator import evaluate_all, save_evaluation_results
from explainability import generate_explanation, format_explanation, save_explanations
from utils import load_cloudtrail_dataframe, load_hypotheses, load_hypotheses_outcomes


def main():
    """Main execution function"""
    # Configuration
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    REPORTS_DIR = BASE_DIR / "reports"
    
    CSV_PATH = DATA_DIR / "nineteenFeaturesDf.csv"
    HYPOTHESES_PATH = DATA_DIR / "hypotheses.json"
    OUTCOMES_PATH = DATA_DIR / "hypotheses_outcomes.json"
    
    REPORTS_DIR.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("AI Threat Hunting Query Generation & Evaluation System")
    print("=" * 80)
    print()
    
    # Step 1: Load data
    print("Step 1: Loading data...")
    print("-" * 80)
    
    if not CSV_PATH.exists():
        print(f"ERROR: CloudTrail CSV not found at {CSV_PATH}")
        return 1
    
    if not HYPOTHESES_PATH.exists():
        print(f"ERROR: Hypotheses file not found at {HYPOTHESES_PATH}")
        return 1
    
    if not OUTCOMES_PATH.exists():
        print(f"ERROR: Outcomes file not found at {OUTCOMES_PATH}")
        return 1
    
    # CloudTrail data
    print(f"Loading CloudTrail data from {CSV_PATH}...")
    df = load_cloudtrail_dataframe(str(CSV_PATH))
    
    # Preserve original index for matching with expected outcomes
    # The expected outcomes use row indices that match pandas DataFrame index after CSV read
    df['original_index'] = df.index.astype(str)
    
    # Hypotheses data
    print(f"Loading hypotheses from {HYPOTHESES_PATH}...")
    hypotheses = load_hypotheses(str(HYPOTHESES_PATH))
    print(f"Loaded {len(hypotheses)} hypotheses")
    
    print()
    
    # Step 2: Generate queries
    print("Step 2: Generating queries...")
    print("-" * 80)
    
    query_outputs = []
    for hypothesis in tqdm(hypotheses, desc="Generating queries"):
        hypothesis_id = hypothesis['id']
        hypothesis_text = hypothesis['hypothesis']
        
        query_output = generate_query(
            hypothesis_id=hypothesis_id,
            hypothesis_text=hypothesis_text,
            df_sample=df.head(100)  # sample for validation
        )
        
        try:
            result_df = query_output.query_function(df)
            query_output.result_df = result_df
        except Exception as e:
            print(f"Warning: Error executing query for hypothesis {hypothesis_id}: {e}")
            query_output.result_df = pd.DataFrame()  # Empty result
        
        query_outputs.append(query_output)
    
    print(f"Generated {len(query_outputs)} queries")
    print()
    
    # Step 3: Generate explanations
    print("Step 3: Generating explanations...")
    print("-" * 80)
    
    explanations = []
    for query_output in tqdm(query_outputs, desc="Generating explanations"):
        explanation = generate_explanation(
            hypothesis_id=query_output.hypothesis_id,
            hypothesis_text=query_output.hypothesis_text,
            query_description=query_output.query_description,
            reasoning=query_output.reasoning,
            assumptions=query_output.assumptions,
            confidence=query_output.confidence,
            result_df=query_output.result_df
        )
        explanations.append(explanation)
    
    
    explanations_path = REPORTS_DIR / "explanations.json"
    save_explanations(explanations, str(explanations_path))
    print(f"Saved explanations to {explanations_path}")
    
    if explanations:
        print("\nSample Explanation:")
        print("=" * 80)
        print(format_explanation(explanations[0]))
        print()
    
    # Step 4: Evaluate results
    print("Step 4: Evaluating results...")
    print("-" * 80)
    
    results = []
    for query_output in query_outputs:
        results.append({
            'hypothesis_id': query_output.hypothesis_id,
            'hypothesis_text': query_output.hypothesis_text,
            'result_df': query_output.result_df
        })
    
    # Pass total dataset size for accurate true_negatives calculation (see evaluator.py)
    total_dataset_size = len(df)
    overall_metrics = evaluate_all(
        results=results,
        expected_outcomes_path=str(OUTCOMES_PATH),
        df_index_col='original_index',
        total_dataset_size=total_dataset_size
    )
    
  
    eval_results_path = REPORTS_DIR / "evaluation_results.json"
    save_evaluation_results(overall_metrics, str(eval_results_path))
    print(f"Saved evaluation results to {eval_results_path}")
    
    #summary 
    print("\nEvaluation Summary:")
    print("=" * 80)
    print(f"Total Hypotheses: {overall_metrics.total_hypotheses}")
    print(f"Average Precision: {overall_metrics.average_precision:.4f}")
    print(f"Average Recall: {overall_metrics.average_recall:.4f}")
    print(f"Average F1 Score: {overall_metrics.average_f1:.4f}")
    print(f"Average Accuracy: {overall_metrics.average_accuracy:.4f}")
    print(f"Weighted F1 Score: {overall_metrics.weighted_f1:.4f}")
    print()
    
    # per-hypothesis breakdown
    print("Per-Hypothesis Breakdown:")
    print("-" * 80)
    for metric in overall_metrics.per_hypothesis_metrics:
        print(f"\nHypothesis {metric.hypothesis_id}: {metric.hypothesis_text[:60]}...")
        print(f"  Precision: {metric.precision:.4f}, Recall: {metric.recall:.4f}, F1: {metric.f1_score:.4f}")
        print(f"  Expected: {metric.expected_count}, Actual: {metric.actual_count}, Matched: {metric.matched_rows}")
        print(f"  False Positives: {metric.false_positives}, False Negatives: {metric.false_negatives}")
    
    print()
    print("=" * 80)
    print("Evaluation complete!")
    print(f"Results saved to {REPORTS_DIR}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())

