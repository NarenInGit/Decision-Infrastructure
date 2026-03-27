"""
Local LLM for interpreting deterministic insights.
AI is an interpreter, not a decision-maker.
"""

from typing import Dict

import streamlit as st

from .guardrails import generate_guarded_text

try:
    from transformers import pipeline

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None


@st.cache_resource
def get_local_llm():
    """Get cached local LLM pipeline."""
    if not TRANSFORMERS_AVAILABLE:
        return None

    try:
        return pipeline(
            "text2text-generation",
            model="google/flan-t5-small",
            max_new_tokens=300,
            device=-1,
        )
    except Exception as exc:
        print(f"Error loading LLM: {exc}")
        return None


def _run_model(prompt: str, max_length: int) -> str:
    llm = get_local_llm()
    if llm is None:
        return ""
    try:
        result = llm(prompt, max_length=max_length, do_sample=False)
        if result and "generated_text" in result[0]:
            return result[0]["generated_text"].strip()
    except Exception:
        return ""
    return ""


def rewrite_answer(summary: Dict) -> str:
    """Rewrite a deterministic answer while keeping facts fixed."""
    prompt = _build_chat_rewrite_prompt(summary)
    return _run_model(prompt, max_length=500) or summary["deterministic_answer"]


def _build_chat_rewrite_prompt(summary: Dict) -> str:
    prompt = f"""Rewrite this answer using the provided facts. Do not add or change any numbers.

User asked: {summary['user_query']}

Original answer:
{summary['deterministic_answer']}

Facts to use (do not modify these):
"""
    for fact in summary["facts_used"]:
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
    """Generate an explanation of deterministic insights."""
    prompt = build_interpretation_prompt(summary)
    return _run_model(prompt, max_length=500) or generate_fallback_explanation(summary)


def build_interpretation_prompt(summary: Dict) -> str:
    key_metrics = summary.get("key_metrics", {})
    insights_by_severity = summary.get("insights_by_severity", {})
    summary_counts = summary.get("summary_counts", {})

    prompt = f"""Explain the following financial insights in plain English. Use only factual language. Do not predict or recommend actions.

Key Metrics:
- Total Revenue: EUR {key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: EUR {key_metrics.get('ebitda_total', 0):,.0f}
- Ending Cash: EUR {key_metrics.get('ending_cash', 0):,.0f}
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
Explain what these insights indicate about the current financial state. Only describe what the current data shows.
"""
    return prompt


def generate_fallback_explanation(summary: Dict) -> str:
    key_metrics = summary.get("key_metrics", {})
    insights_by_severity = summary.get("insights_by_severity", {})
    summary_counts = summary.get("summary_counts", {})

    explanation = "## Financial Insights Summary\n\n"
    explanation += "### Current Financial Position\n"
    explanation += f"- **Total Revenue**: EUR {key_metrics.get('revenue_total', 0):,.0f}\n"
    explanation += f"- **EBITDA**: EUR {key_metrics.get('ebitda_total', 0):,.0f}\n"
    explanation += f"- **Ending Cash**: EUR {key_metrics.get('ending_cash', 0):,.0f}\n"
    explanation += f"- **Runway**: {key_metrics.get('runway_months', 0):.1f} months\n\n"

    critical = insights_by_severity.get("critical", [])
    if critical:
        explanation += "### Critical Issues\n"
        for insight in critical[:5]:
            explanation += f"- {insight['message']}\n"
        explanation += "\n"

    warnings = insights_by_severity.get("warning", [])
    if warnings:
        explanation += "### Warnings\n"
        for insight in warnings[:5]:
            explanation += f"- {insight['message']}\n"
        explanation += "\n"

    explanation += "### Summary\n"
    explanation += (
        f"The analysis identified {summary_counts.get('total_insights', 0)} insights: "
        f"{summary_counts.get('critical', 0)} critical issues, "
        f"{summary_counts.get('warning', 0)} warnings, and "
        f"{summary_counts.get('info', 0)} informational items.\n"
    )
    return explanation


def generate_narrative(summary: Dict, format: str = "email") -> str:
    """Generate copy-ready narrative for sharing."""
    prompt = _build_narrative_prompt(summary, format)
    return _run_model(prompt, max_length=600) or _generate_fallback_narrative(summary, format)


def _build_narrative_prompt(summary: Dict, format: str) -> str:
    key_metrics = summary.get("key_metrics", {})
    insights_by_severity = summary.get("insights_by_severity", {})

    if format == "slack":
        prompt = f"""Write a brief Slack update about the financial status. Use only the facts below.

Facts:
- Revenue: EUR {key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: EUR {key_metrics.get('ebitda_total', 0):,.0f}
- Cash: EUR {key_metrics.get('ending_cash', 0):,.0f}
- Runway: {key_metrics.get('runway_months', 0):.1f} months
- Critical issues: {len(insights_by_severity.get('critical', []))}
- Warnings: {len(insights_by_severity.get('warning', []))}

Do not predict or recommend actions.
"""
    elif format == "investor":
        prompt = f"""Write a concise investor-style update using only current facts.

Facts:
- Revenue: EUR {key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: EUR {key_metrics.get('ebitda_total', 0):,.0f}
- Cash: EUR {key_metrics.get('ending_cash', 0):,.0f}
- Critical issues: {len(insights_by_severity.get('critical', []))}
- Warnings: {len(insights_by_severity.get('warning', []))}

Be factual, not predictive.
"""
    else:
        prompt = f"""Write a short email memo using only current facts.

Facts:
- Revenue: EUR {key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: EUR {key_metrics.get('ebitda_total', 0):,.0f}
- Cash: EUR {key_metrics.get('ending_cash', 0):,.0f}
- Runway: {key_metrics.get('runway_months', 0):.1f} months
- Critical issues: {len(insights_by_severity.get('critical', []))}
- Warnings: {len(insights_by_severity.get('warning', []))}

Be factual, not predictive.
"""
    return prompt


def _generate_fallback_narrative(summary: Dict, format: str) -> str:
    key_metrics = summary.get("key_metrics", {})
    if format == "slack":
        return (
            f"Financial Update: Revenue EUR {key_metrics.get('revenue_total', 0):,.0f}, "
            f"EBITDA EUR {key_metrics.get('ebitda_total', 0):,.0f}, "
            f"Cash EUR {key_metrics.get('ending_cash', 0):,.0f}. "
            f"Review needed on {len(summary.get('insights_by_severity', {}).get('critical', []))} critical items. "
            "(Generated from computed data)"
        )
    if format == "investor":
        return (
            f"Financial Update: Revenue EUR {key_metrics.get('revenue_total', 0):,.0f}, "
            f"EBITDA EUR {key_metrics.get('ebitda_total', 0):,.0f}, "
            f"Cash EUR {key_metrics.get('ending_cash', 0):,.0f}. "
            "Data reflects current computed metrics without forward projections."
        )
    return f"""## Financial Memo

**Current Metrics:**
- Revenue: EUR {key_metrics.get('revenue_total', 0):,.0f}
- EBITDA: EUR {key_metrics.get('ebitda_total', 0):,.0f}
- Cash: EUR {key_metrics.get('ending_cash', 0):,.0f}
- Runway: {key_metrics.get('runway_months', 0):.1f} months

**Items Requiring Attention:**
- Critical: {len(summary.get('insights_by_severity', {}).get('critical', []))}
- Warnings: {len(summary.get('insights_by_severity', {}).get('warning', []))}

Generated from computed financial data.
"""


def generate_guarded_rewrite(
    llm_output: str,
    deterministic_answer: str,
    facts_used,
    strict: bool = True,
) -> Dict[str, str]:
    """Thin wrapper used by the UI so all LLM paths share one guardrail flow."""
    return generate_guarded_text(llm_output, deterministic_answer, facts_used, strict=strict)
