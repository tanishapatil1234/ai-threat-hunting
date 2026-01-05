# AI Threat Hunting Query Generation & Evaluation System

An AI-powered system that translates threat hunting hypotheses into executable queries against security log datasets. This system generates accurate queries from natural language hypotheses and provides a robust evaluation framework to measure query quality and result accuracy.

## Overview

This project implements a complete pipeline for:
1. **Query Generation**: Parses natural language threat hunting hypotheses , turning them into executable pandas DataFrame queries

Example hypothesis :  CloudTrail logs contain failed console login attempts that could indicate brute force or bot attacks

Example HypothesisIntent Object : 

<code>
HypothesisIntent(
    event_name="ConsoleLogin",
    event_source="signin.amazonaws.com",
    error_code="FailedAuthentication",
    user_identity_type=None,
    filters={
        "has_error": True,
        "multiple_attempts": True
    },
    time_range=None,
    description="CloudTrail logs contain failed console login attempts that could indicate brute force or bot attacks"
)
</code>

  
2. **Query Execution**: Runs queries against CloudTrail log data
3. **Evaluation**: Compares results against expected outcomes using precision, recall, F1 score, and accuracy metrics
4. **Explainability**: Provides detailed explanations of how hypotheses were interpreted and why queries were structured the way they were

Example: 
=== Query Reasoning ===
This hypothesis is asking for: CloudTrail logs contain failed console login attempts that could indicate brute force or bot attacks. I structured the query to filter by eventName='ConsoleLogin' and eventSource='cloudtrail.amazonaws.com' with error conditions (FailedAuthentication).

## Architecture

```
┌─────────────────┐
│  Hypotheses     │
│  (JSON)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Generator │ ◄─── Rule-based parsing + Intent extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Query Execution │ ◄─── Pandas DataFrame operations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Evaluator     │ ◄─── Compare with expected outcomes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Explainability  │ ◄─── Generate explanations & confidence scores
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Reports        │
│  (JSON + MD)    │
└─────────────────┘
```

### Components

- **`query_generator.py`**:  query generation logic using rule-based parsing
- **`evaluator.py`**: evaluation framework with precision, recall, F1, and accuracy metrics
- **`explainability.py`**: explainability for hypothesis interpretation and query reasoning
- **`main.py`**: entry point that runs the full pipeline
- **`utils.py`**: utility functions for loading data and hypotheses

## Setup Instructions


### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd ai-threat-hunting
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify data files are present:**
   - `data/nineteenFeaturesDf.csv` - CloudTrail dataset
   - `data/hypotheses.json` - Threat hunting hypotheses
   - `data/hypotheses_outcomes.json` - Expected outcomes for evaluation

### Running the System

1. **Run the complete evaluation pipeline:**
   ```bash
   python src/main.py
   ```

2. **View results:**
   - Evaluation results: `reports/evaluation_results.json`
   - Explanations: `reports/explanations.json`
   - Console output will show summary metrics and per-hypothesis breakdown

### Expected Output

The system will:
1. Load CloudTrail data and hypotheses
2. Generate queries for each hypothesis
3. Execute queries and collect results
4. Evaluate results against expected outcomes
5. Generate explanations with confidence scores
6. Save all results to the `reports/` directory

Example console output:
```
================================================================================
AI Threat Hunting Query Generation & Evaluation System
================================================================================

Step 1: Loading data...
--------------------------------------------------------------------------------
Loading CloudTrail data from data/nineteenFeaturesDf.csv...
Loaded 200000 rows, 19 columns
Loading hypotheses from data/hypotheses.json...
Loaded 10 hypotheses

Step 2: Generating queries...
--------------------------------------------------------------------------------
Generating queries: 100%|████████████| 10/10 [00:05<00:00,  1.89it/s]
Generated 10 queries

Step 3: Generating explanations...
--------------------------------------------------------------------------------
...

Evaluation Summary:
================================================================================
Total Hypotheses: 10
Average Precision: 0.8234
Average Recall: 0.7891
Average F1 Score: 0.8056
Average Accuracy: 0.8123
Weighted F1 Score: 0.8012
```

## Design Decisions and Trade-offs

### Query Generation 

**Decision**: Rule-based parsing with keyword matching
- **Rationale**: Provides deterministic, explainable results without requiring API keys or external services
- **Trade-off**: Less flexible than LLM-based approaches, but more reliable and faster
- **Future improvement**: Can be extended with LLM fallback for complex hypotheses
- Note: I also didn’t have API tokens available to use an LLM, so rule-based parsing was the practical option

### Evaluation Metrics

**Decision**: Precision, Recall, F1 Score, and Accuracy
- **Rationale**: Standard information metrics that measure correctness. Precision measures correctness (how many retrieved rows are relevant), recall measures completeness (how many relevant rows were retrieved), F1 balances the two, and accuracy gives an overall correctness measure. Results are also compared against expected outcomes for validation.
- **Trade-off**: Accuracy can be approximate if the total dataset size is unknown, but precision, recall, and F1 are exact.
- **Future improvement**: Metrics could be extended with weighted scores, or visualizations 

### Data Structure

**Decision**: Pandas DataFrame operations
- **Rationale**: Flexible, in-memory operations suitable for the dataset size
- **Trade-off**: May not scale to very large datasets (>10GB), but works well for this use case
- **Alternative**: Could use DuckDB , SQL, or Polars for better performance on larger datasets

### Explainability

**Decision**: Structured explanations with confidence scores
- **Rationale**: Provides transparency into query generation process
- **Trade-off**: Confidence scores are heuristic-based, not learned from data

## Extending to Other Datasets

To extend this system to other security log datasets:

1. **Update schema mapping** in `query_generator.py`:
   - Modify `CLOUDTRAIL_COLUMNS` to match your dataset
   - Update `parse_hypothesis()` to recognize dataset-specific patterns
   - Adjust `build_query_function()` to use correct column names

2. **Update data loading** in `utils.py`:
   - Modify `load_cloudtrail_dataframe()` to handle your data format
   - Ensure index column is preserved for evaluation

3. **Update evaluation** in `evaluator.py`:
   - Adjust `get_expected_row_indices()` if outcome format differs
   - Modify `calculate_metrics()` if row matching logic needs changes

4. **Create new hypotheses**:
   - Add hypotheses in JSON format matching the structure in `data/hypotheses.json`
   - Create corresponding expected outcomes in `data/hypotheses_outcomes.json`

## Project Structure

```
ai-threat-hunting/
├── data/
│   ├── nineteenFeaturesDf.csv          # CloudTrail dataset
│   ├── hypotheses.json                 # Threat hunting hypotheses
│   └── hypotheses_outcomes.json        # Expected outcomes
├── src/
│   ├── query_generator.py              # Query generation logic
│   ├── evaluator.py                    # Evaluation framework
│   ├── explainability.py               # Explainability module
│   ├── main.py                         # Entry point
│   └── utils.py                        # Utility functions
├── reports/                            # Generated reports (created at run main.py)
│   ├── evaluation_results.json         
│   └── explanations.json
├── requirements.txt                    # Python dependencies
├── README.md                           # This file
└── APPROACH.md                         # Detailed approach documentation
```

## Dependencies

- **pandas**: DataFrame operations and data manipulation
- **numpy**: Numerical operations
- **scikit-learn**: Metrics calculation (precision, recall, F1)
- **tqdm**: Progress bars
- **python-dateutil**: Date parsing utilities

## Limitations and Future Work

### Current Limitations

1. **Rule-based parsing**: Limited to predefined patterns and keywords, may miss nuanced or ambiguous hypotheses. LLM-based parsing could handle more complex hypotheses, but tokens/API access were not available for this project.
2. **Approximate accuracy**:True negatives calculation requires knowledge of total dataset size; otherwise, accuracy is only approximate.
3. **No query optimization**: Queries are generated but not optimized for performance , especially on larger datasets

### Future Improvements

1. **LLM Integration**: Add OpenAI/Anthropic API support for complex hypothesis parsing
2. **Query Optimization**: Analyze query performance and suggest optimizations
3. **Multi-step Reasoning**: Support hypotheses requiring multiple sequential queries
4. **Interactive Demo**: Create Streamlit web UI for interactive query generation
5. **Automated Prompt Improvement**: Learn from evaluation failures to improve parsing
6. **Performance Benchmarks**: Add latency and throughput measurements
