"""
Build compact summaries for AI interpretation.
Only sends small, structured summaries - never raw tables or CSVs.
AI is an interpreter, NOT a decision-maker.
"""

import pandas as pd
from typing import Dict, List


def build_chat_summary(user_query: str, deterministic_answer: Dict) -> Dict:
    """
    Build compact summary for AI chat rewriting.
    
    Args:
        user_query: User's question
        deterministic_answer: Deterministic answer dict with:
            - final_answer: str
            - facts_used: List[str]
            - matched_insights: List[str]
            - followups: List[str]
    
    Returns:
        Dictionary with query, deterministic content, and rules
    """
    return {
        "user_query": user_query,
        "deterministic_answer": deterministic_answer["final_answer"],
        "facts_used": deterministic_answer["facts_used"],
        "matched_insights": deterministic_answer["matched_insights"],
        "followups": deterministic_answer["followups"],
        "rules": [
            "Use ONLY the provided facts_used values - do not add, modify, or invent numbers",
            "Keep the answer concise and structured",
            "Do not predict, forecast, or recommend specific actions",
            "Only interpret what the existing data shows"
        ]
    }


def build_insights_summary(
    insights: List[Dict],
    key_metrics: Dict
) -> Dict:
    """
    Build a compact JSON-serializable summary for AI interpretation.
    
    Args:
        insights: List of insight dicts from insights_engine
        key_metrics: Dictionary with key financial metrics:
            - revenue_total
            - ebitda_total
            - ending_cash
            - runway_months
            - gross_profit_total
            - operating_expenses_total
    
    Returns:
        Dictionary with:
            - key_metrics: headline financial numbers
            - insights_by_type: grouped insights by type
            - insights_by_severity: grouped insights by severity
            - summary_counts: counts of insights by type/severity
    """
    # Group insights by type
    insights_by_type = {}
    for insight in insights:
        insight_type = insight["type"]
        if insight_type not in insights_by_type:
            insights_by_type[insight_type] = []
        insights_by_type[insight_type].append({
            "entity": insight["entity"],
            "message": insight["message"],
            "drivers": insight["drivers"]
        })
    
    # Group insights by severity
    insights_by_severity = {"critical": [], "warning": [], "info": []}
    for insight in insights:
        severity = insight["severity"]
        insights_by_severity[severity].append({
            "type": insight["type"],
            "entity": insight["entity"],
            "message": insight["message"]
        })
    
    # Summary counts
    summary_counts = {
        "total_insights": len(insights),
        "critical": len([i for i in insights if i["severity"] == "critical"]),
        "warning": len([i for i in insights if i["severity"] == "warning"]),
        "info": len([i for i in insights if i["severity"] == "info"]),
        "by_type": {}
    }
    for insight_type, type_insights in insights_by_type.items():
        summary_counts["by_type"][insight_type] = len(type_insights)
    
    return {
        "key_metrics": key_metrics,
        "insights_by_type": insights_by_type,
        "insights_by_severity": insights_by_severity,
        "summary_counts": summary_counts
    }
