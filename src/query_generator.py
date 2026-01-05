"""
Query Generator Module

This module generates executable pandas df queries from interpretations of the threat hunting hypotheses.
using rule-based logic
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Dict, Any
import pandas as pd



CLOUDTRAIL_COLUMNS = [
    "eventID", "eventTime", "sourceIPAddress", "userAgent", "eventName",
    "eventSource", "awsRegion", "eventVersion", "userIdentitytype", "eventType",
    "requestID", "userIdentityaccountId", "userIdentityprincipalId", "userIdentityarn",
    "userIdentityaccessKeyId", "userIdentityuserName", "errorCode", "errorMessage",
    "requestParametersinstanceType"
]


@dataclass
class HypothesisIntent:
    """structured representation of a threat hunting hypothesis"""
    event_name: Optional[str] = None  # e.g., "ConsoleLogin", "GetCallerIdentity"
    event_source: Optional[str] = None  # e.g., "signin.amazonaws.com", "sts.amazonaws.com"
    error_code: Optional[str] = None  # e.g., "AccessDenied", "UnauthorizedOperation"
    user_identity_type: Optional[str] = None  # e.g., "Root", "IAMUser"
    filters: Dict[str, Any] = None  # Additional filters
    time_range: Optional[str] = None  # e.g., "last_7_days"
    description: str = ""


@dataclass
class QueryOutput:
    """output of query generation and execution"""
    hypothesis_id: str
    hypothesis_text: str
    query_description: str
    query_function: Callable[[pd.DataFrame], pd.DataFrame]
    reasoning: str
    assumptions: List[str]
    confidence: float
    result_df: Optional[pd.DataFrame] = None


def parse_hypothesis(hypothesis_text: str) -> HypothesisIntent:
    """ parses the hypothesis text and returns a HypothesisIntent object, uses rule-based parsing with keyword matching.
    """
    text = hypothesis_text.lower()
    intent = HypothesisIntent(description=hypothesis_text)
    intent.filters = {}

    # Parse event names
    if "consolelogin" in text or "console login" in text or "sign-in" in text or "signin" in text:
        intent.event_name = "ConsoleLogin"
        intent.event_source = "signin.amazonaws.com"
    
    if "getcalleridentity" in text or "whoami" in text:
        intent.event_name = "GetCallerIdentity"
        intent.event_source = "sts.amazonaws.com"
    
    if "createaccesskey" in text or "access key" in text:
        intent.event_name = "CreateAccessKey"
        intent.event_source = "iam.amazonaws.com"
    
    if "getbucketacl" in text or "bucket acl" in text:
        intent.event_name = "GetBucketAcl"
        intent.event_source = "s3.amazonaws.com"
    
    if "runinstances" in text or "ec2 instance" in text:
        intent.event_name = "RunInstances"
        intent.event_source = "ec2.amazonaws.com"
    
    if "getsecretvalue" in text or "secrets manager" in text:
        intent.event_name = "GetSecretValue"
        intent.event_source = "secretsmanager.amazonaws.com"
    
    if "stoptrail" in text or "deletetrail" in text or "cloudtrail" in text:
        if "stop" in text:
            intent.event_name = "StopLogging"
        elif "delete" in text:
            intent.event_name = "DeleteTrail"
        intent.event_source = "cloudtrail.amazonaws.com"

    # Parse error conditions
    if "failed" in text or "failure" in text:
        intent.error_code = "FailedAuthentication"
        intent.filters["has_error"] = True
    
    if "accessdenied" in text or "unauthorized" in text or "unauthorizedoperation" in text:
        if "accessdenied" in text:
            intent.error_code = "AccessDenied"
        elif "unauthorizedoperation" in text:
            intent.error_code = "UnauthorizedOperation"
        intent.filters["has_error"] = True

    # Parse user identity types
    if "root" in text and ("user" in text or "login" in text):
        intent.user_identity_type = "Root"
    
    if "iam user" in text or ("iam" in text and "user" in text and "role" not in text):
        intent.filters["is_iam_user"] = True
        intent.filters["not_role"] = True

    # Parse specific patterns
    if "brute force" in text or "bruteforce" in text:
        intent.filters["multiple_attempts"] = True
    
    if "suspicious user agent" in text or "user agent" in text:
        if "kali" in text or "parrot" in text or "powershell" in text:
            intent.filters["suspicious_ua_keywords"] = ["kali", "parrot", "powershell"]
        elif "command" in text:
            intent.filters["suspicious_ua_keywords"] = ["command/"]
    
    if "10xlarge" in text or "extra-large" in text or "large" in text:
        intent.filters["instance_size"] = "xlarge"
        intent.filters["min_instance_size"] = 10  # 10xlarge or bigger

    return intent


def build_query_function(intent: HypothesisIntent) -> Callable[[pd.DataFrame], pd.DataFrame]:
    """ Builds a pandas query function based on the HypothesisIntent object.
    """
    def query_func(df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        
        # Apply event name filter
        if intent.event_name:
            result = result[result['eventName'] == intent.event_name]
        
        # Apply event source filter
        if intent.event_source:
            result = result[result['eventSource'] == intent.event_source]
        
        # Apply error code filter
        if intent.error_code:
            if intent.error_code == "FailedAuthentication":
                result = result[result['errorCode'].notna()]
            elif intent.error_code in ["AccessDenied", "UnauthorizedOperation"]:
                result = result[result['errorCode'] == intent.error_code]
        
        # Apply user identity type filter
        if intent.user_identity_type:
            result = result[result['userIdentitytype'] == intent.user_identity_type]
        
        # Apply additional filters
        if intent.filters:
            if intent.filters.get("has_error"):
                result = result[result['errorCode'].notna() | result['errorMessage'].notna()]
            
            if intent.filters.get("is_iam_user"):
                result = result[result['userIdentitytype'] == 'IAMUser']
            
            if intent.filters.get("not_role"):
                result = result[result['userIdentitytype'] != 'AssumedRole']
            
            if intent.filters.get("suspicious_ua_keywords"):
                keywords = intent.filters["suspicious_ua_keywords"]
                mask = pd.Series([False] * len(result))
                for keyword in keywords:
                    mask |= result['userAgent'].str.contains(keyword, case=False, na=False)
                result = result[mask]
            
            if intent.filters.get("instance_size"):
                # Filter for large EC2 instances
                if 'requestParametersinstanceType' in result.columns:
                    result = result[
                        result['requestParametersinstanceType'].str.contains('xlarge', case=False, na=False)
                    ]
                    if intent.filters.get("min_instance_size"):
                        # Filter for 10xlarge or bigger (10xlarge, 12xlarge, etc.)
                        def is_large_enough(instance_type):
                            if pd.isna(instance_type):
                                return False
                            try:
                                # Extract number from instance type (e.g., "10xlarge" -> 10)
                                parts = str(instance_type).lower().split('x')
                                if len(parts) > 0 and parts[0].isdigit():
                                    return int(parts[0]) >= 10
                            except:
                                pass
                            return False
                        result = result[result['requestParametersinstanceType'].apply(is_large_enough)]
        
        return result
    
    return query_func


def generate_query(hypothesis_id: str, hypothesis_text: str, df_sample: Optional[pd.DataFrame] = None) -> QueryOutput:
    """
    Main function to generate a query from a hypothesis.
    
    Args: hypothesis_id, hypothesis_text: Natural language hypothesis, df
    
    Returns: QueryOutput with query function and metadata
    """
    # Parse hypothesis
    intent = parse_hypothesis(hypothesis_text)
    
    # Build query function
    query_func = build_query_function(intent)
    
    # Generate description and reasoning
    query_description = f"Filter CloudTrail logs for {intent.description}"
    if intent.event_name:
        query_description += f" where eventName='{intent.event_name}'"
    if intent.event_source:
        query_description += f" and eventSource='{intent.event_source}'"
    if intent.error_code:
        query_description += f" with errorCode='{intent.error_code}'"
    
    reasoning = f"This hypothesis is asking for: {hypothesis_text}. "
    reasoning += f"I structured the query to filter by "
    if intent.event_name:
        reasoning += f"eventName='{intent.event_name}'"
    if intent.event_source:
        reasoning += f" and eventSource='{intent.event_source}'"
    if intent.error_code:
        reasoning += f" with error conditions ({intent.error_code})"
    reasoning += "."
    
    assumptions = []
    if "recent" in hypothesis_text.lower():
        assumptions.append("I assumed 'recent' means all available data in the dataset")
    if "failed" in hypothesis_text.lower() and not intent.error_code:
        assumptions.append("I assumed 'failed' means presence of errorCode or errorMessage")
    if intent.filters and intent.filters.get("multiple_attempts"):
        assumptions.append("I assumed brute force detection requires multiple failed attempts from same source")
    
    # Calculate confidence based on how well we matched the hypothesis
    confidence = 0.7  # Base confidence
    if intent.event_name:
        confidence += 0.1
    if intent.event_source:
        confidence += 0.1
    if intent.error_code or (intent.filters and intent.filters.get("has_error")):
        confidence += 0.05
    confidence = min(confidence, 0.95)  # Cap at 95%
    
    return QueryOutput(
        hypothesis_id=hypothesis_id,
        hypothesis_text=hypothesis_text,
        query_description=query_description,
        query_function=query_func,
        reasoning=reasoning,
        assumptions=assumptions,
        confidence=confidence
    )
