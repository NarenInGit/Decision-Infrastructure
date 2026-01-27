"""
Local LLM for interpreting deterministic insights.
AI is an interpreter, NOT a decision-maker.
"""

import streamlit as st
from typing import Dict, Optional
import json

# Optional imports - graceful fallback if transformers not available
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None


@st.cache_resource
def get_local_llm():
    """
    Get cached local LLM pipeline.
    Uses flan-t5-small for CPU compatibility.
    
    Returns:
        Pipeline object or None if not available
    """
    if not TRANSFORMERS_AVAILABLE:
        return None
    
    try:
        # Use small model for CPU
        model = pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
            max_new_tokens=300,
            device=-1  # CPU
        )
        return model
    except Exception as e:
        print(f"Error loading LLM: {e}")
        return None


def rewrite_answer(summary: Dict) -> str:
    """
    Rewrite deterministic answer using LLM (optional phrasing only).
    
    Args:
        summary: Chat summary dict from build_chat_summary
    
    Returns:
        Rewritten answer (or original if LLM fails/unavailable)
    """
    llm = get_local_llm()
    
    if llm is None:
        return summary["deterministic_answer"]
    
    try:
        prompt = _build_chat_rewrite_prompt(summary)
        result = llm(prompt, max_length=500, do_sample=False)
        
        if result and len(result) > 0 and "generated_text" in result[0]:
            rewritten = result[0]["generated_text"].strip()
            # Validate no forbidden language
            if _contains_forbidden_language(rewritten):
                return summary["deterministic_answer"]
            return rewritten
        else:
            return summary["deterministic_answer"]
    except Exception:
        return summary["deterministic_answer"]


def _build_chat_rewrite_prompt(summary: Dict) -> str:
    """Build prompt for chat answer rewriting."""
    prompt = f"""Rewrite this answer using the provided facts. Do not add or change any numbers.

User asked: {summary['user_query']}

Original answer:
{summary['deterministic_answer']}

Facts to use (do not modify these):
"""
    
    for fact in summary['facts_used']:
        prompt += f"- {fact}\n"
    
    prompt += """
Rules:
- Use ONLY the facts provided above
- Do not add, modify, or invent numbers
- Keep it concise and clear
- Do not predict or recommend actions
- Only explain what the data shows

Rewrite the answer:"""
    
    return prompt


def generate_insights_explanation(summary: Dict) -> str:
    """
    Generate insights explanation using local LLM or fallback template.
    
    Args:
        summary: Insights summary dict from build_insights_summary
    
    Returns:
        Plain text explanation
    """
    llm = get_local_llm()
    
    if llm is None:
        return generate_fallback_explanation(summary)
    
    try:
        prompt = build_interpretation_prompt(summary)
        result = llm(prompt, max_length=500, do_sample=False)
        
        if result and len(result) > 0 and "generated_text" in result[0]:
            explanation = result[0]["generated_text"].strip()
            # Validate explanation doesn't contain forbidden language
            if _contains_forbidden_language(explanation):
                st.warning("AI explanation contained prediction language. Using fallback.")
                return generate_fallback_explanation(summary)
            return explanation
        else:
            return generate_fallback_explanation(summary)
    except Exception as e:
        st.warning(f"Error generating AI explanation: {e}. Using fallback.")
        return generate_fallback_explanation(summary)


def build_interpretation_prompt(summary: Dict) -> str:
    """
    Build prompt for AI interpretation.
    
    Rules:
    - AI must ONLY explain what the data shows
    - AI must NEVER predict, forecast, or assign probabilities
    - AI must NEVER recommend specific actions
    - AI must use factual language only
    """
    key_metrics = summary.get("key_metrics", {})
    insights_by_severity = summary.get("insights_by_severity", {})
    summary_counts = summary.get("summary_counts", {})
    
    prompt = f"""Explain the following financial insights in plain English. Use only factual language. Do not predict or recommend actions.

Key Metrics:
- Total Revenue: €{key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: €{key_metrics.get('ebitda_total', 0):,.0f}
- Ending Cash: €{key_metrics.get('ending_cash', 0):,.0f}
- Runway: {key_metrics.get('runway_months', 0):.1f} months

Insights Summary:
- Critical issues: {summary_counts.get('critical', 0)}
- Warnings: {summary_counts.get('warning', 0)}
- Info: {summary_counts.get('info', 0)}

Critical Issues:
"""
    
    for insight in insights_by_severity.get("critical", [])[:5]:
        prompt += f"- {insight['message']}\n"
    
    prompt += "\nWarnings:\n"
    for insight in insights_by_severity.get("warning", [])[:5]:
        prompt += f"- {insight['message']}\n"
    
    prompt += """
Explain what these insights indicate about the current financial state. Use phrases like:
- "This indicates..."
- "This is driven by..."
- "Currently, the data shows..."

Do NOT use:
- "Will likely..."
- "Expected to..."
- "Probability of..."
- "You should..."
"""
    
    return prompt


def generate_fallback_explanation(summary: Dict) -> str:
    """
    Generate deterministic fallback explanation.
    """
    key_metrics = summary.get("key_metrics", {})
    insights_by_severity = summary.get("insights_by_severity", {})
    summary_counts = summary.get("summary_counts", {})
    
    explanation = "## Financial Insights Summary\n\n"
    
    # Key metrics
    explanation += "### Current Financial Position\n"
    explanation += f"- **Total Revenue**: €{key_metrics.get('revenue_total', 0):,.0f}\n"
    explanation += f"- **EBITDA**: €{key_metrics.get('ebitda_total', 0):,.0f}\n"
    explanation += f"- **Ending Cash**: €{key_metrics.get('ending_cash', 0):,.0f}\n"
    explanation += f"- **Runway**: {key_metrics.get('runway_months', 0):.1f} months\n\n"
    
    # Critical issues
    critical = insights_by_severity.get("critical", [])
    if critical:
        explanation += "### Critical Issues\n"
        for insight in critical[:5]:
            explanation += f"- {insight['message']}\n"
        explanation += "\n"
    
    # Warnings
    warnings = insights_by_severity.get("warning", [])
    if warnings:
        explanation += "### Warnings\n"
        for insight in warnings[:5]:
            explanation += f"- {insight['message']}\n"
        explanation += "\n"
    
    # Summary
    explanation += "### Summary\n"
    explanation += f"The analysis identified {summary_counts.get('total_insights', 0)} insights: "
    explanation += f"{summary_counts.get('critical', 0)} critical issues, "
    explanation += f"{summary_counts.get('warning', 0)} warnings, and "
    explanation += f"{summary_counts.get('info', 0)} informational items.\n"
    
    return explanation


def _contains_forbidden_language(text: str) -> bool:
    """
    Check if text contains forbidden prediction/recommendation language.
    """
    forbidden_phrases = [
        "will likely",
        "expected to",
        "probability",
        "you should",
        "you must",
        "recommend",
        "suggest",
        "forecast",
        "predict"
    ]
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in forbidden_phrases)
