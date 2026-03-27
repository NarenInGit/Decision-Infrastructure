"""
Query Router - High-level interface for answering user queries.
Routes queries to deterministic answer builders with compact context.
"""

from typing import Dict, List
from ..ai.guardrails import sanitize_context
from .insights_chat import parse_intent, retrieve_context, build_deterministic_answer
from .context_builder import build_context


def answer_query(
    user_query: str,
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """
    Answer user query using deterministic logic only.
    
    This is the main entry point for query answering. It:
    1. Parses user intent
    2. Builds compact context (no raw tables)
    3. Constructs deterministic answer
    4. Returns structured payload
    
    Args:
        user_query: User's question
        metrics_outputs: Metrics engine outputs
        insights_list: List of all insights
    
    Returns:
        {
            "answer": str,              # Human-readable response
            "facts_used": List[str],    # Factual bullets with numbers
            "insights_used": List[str], # Insight messages used
            "followups": List[str],     # Suggested follow-up questions
            "entity": {                 # Entity info (if applicable)
                "type": "project|person|company|invoice",
                "id": "P009"
            },
            "intent": Dict              # Parsed intent for debugging
        }
    """
    # Parse intent
    intent = parse_intent(user_query)
    
    # Retrieve context (uses existing logic from insights_chat)
    context = retrieve_context(intent, metrics_outputs, insights_list)
    
    # Build deterministic answer
    deterministic_answer = build_deterministic_answer(user_query, context, intent)
    
    # Structure response
    response = {
        "answer": deterministic_answer["final_answer"],
        "facts_used": deterministic_answer["facts_used"],
        "insights_used": deterministic_answer["matched_insights"],
        "followups": deterministic_answer["followups"],
        "entity": {
            "type": intent["intent"],
            "id": intent.get("entity_id")
        },
        "intent": intent
    }
    
    return response


def get_context_summary(
    user_query: str,
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """
    Get a compact context summary for a query (useful for debugging or AI context).
    
    Returns only KPIs, insights, and small table snippets - never full dataframes.
    """
    intent = parse_intent(user_query)
    context = build_context(intent, metrics_outputs, insights_list, max_rows=5)
    
    return {
        "intent": intent,
        "context": sanitize_context(context)
    }
