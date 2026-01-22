"""
Local PyTorch LLM for scenario narrative generation.
Uses HuggingFace Transformers with a small CPU-compatible model.
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


def generate_scenario_memo(summary: Dict) -> str:
    """
    Generate scenario memo using local LLM or fallback template.
    
    Args:
        summary: Scenario summary dict from build_scenario_summary
    
    Returns:
        Formatted memo string
    """
    model = get_local_llm()
    
    if model is None:
        return generate_fallback_memo(summary)
    
    # Build prompt
    prompt = build_prompt(summary)
    
    try:
        # Generate with LLM
        result = model(prompt, max_length=500, do_sample=False, temperature=0.3)
        generated_text = result[0]["generated_text"]
        
        # Format output
        return format_memo(generated_text, summary)
    except Exception as e:
        print(f"Error generating memo: {e}")
        return generate_fallback_memo(summary)


def build_prompt(summary: Dict) -> str:
    """Build prompt for LLM."""
    kpis = summary["headline_kpis"]
    
    prompt = f"""Write a structured memo analyzing a financial scenario.

Scenario: {summary['scenario_name']}
Start Month: {summary['start_month']}

Changes:
{chr(10).join(f"- {c['type']}: {json.dumps(c)}" for c in summary['changes'])}

Key Metrics:
- Revenue: €{kpis['revenue_total']['before']:,.0f} → €{kpis['revenue_total']['after']:,.0f} (Δ€{kpis['revenue_total']['delta']:,.0f})
- EBITDA: €{kpis['ebitda_total']['before']:,.0f} → €{kpis['ebitda_total']['after']:,.0f} (Δ€{kpis['ebitda_total']['delta']:,.0f})
- Ending Cash: €{kpis['ending_cash']['before']:,.0f} → €{kpis['ending_cash']['after']:,.0f} (Δ€{kpis['ending_cash']['delta']:,.0f})
- Runway: {kpis['runway_months']['before']:.1f} → {kpis['runway_months']['after']:.1f} months

Top Winners (by gross profit improvement):
{chr(10).join(f"- {p['project_id']}: Δ€{p['gross_profit_delta']:,.0f}" for p in summary['top_winners'][:3])}

High Risk Projects (negative margin):
{chr(10).join(f"- {p['project_id']}: {p['gross_margin_pct']:.1%}" for p in summary['high_risk_projects'][:3])}

Key Drivers:
{chr(10).join(f"- {d}" for d in summary['key_drivers'])}

Write a memo with:
Title
1) What changed (bullets)
2) Impact (bullets with numbers)
3) Risks / assumptions (bullets)
4) Recommended next actions (bullets, concrete)

IMPORTANT: Only use the numbers provided above. Do not invent numbers."""
    
    return prompt


def format_memo(generated_text: str, summary: Dict) -> str:
    """Format generated text into memo structure."""
    # If LLM output is good, use it; otherwise enhance with template
    memo = f"# {summary['scenario_name']}\n\n"
    memo += generated_text
    
    return memo


def generate_fallback_memo(summary: Dict) -> str:
    """
    Generate deterministic fallback memo without LLM.
    
    Args:
        summary: Scenario summary dict
    
    Returns:
        Formatted memo string
    """
    kpis = summary["headline_kpis"]
    
    memo = f"# {summary['scenario_name']}\n\n"
    memo += f"**Start Month:** {summary['start_month']}\n\n"
    
    memo += "## 1) What Changed\n\n"
    for driver in summary["key_drivers"]:
        memo += f"- {driver}\n"
    
    memo += "\n## 2) Impact\n\n"
    memo += f"- **Revenue:** €{kpis['revenue_total']['before']:,.0f} → €{kpis['revenue_total']['after']:,.0f} "
    memo += f"(Δ€{kpis['revenue_total']['delta']:+,.0f})\n"
    memo += f"- **EBITDA:** €{kpis['ebitda_total']['before']:,.0f} → €{kpis['ebitda_total']['after']:,.0f} "
    memo += f"(Δ€{kpis['ebitda_total']['delta']:+,.0f})\n"
    memo += f"- **Ending Cash:** €{kpis['ending_cash']['before']:,.0f} → €{kpis['ending_cash']['after']:,.0f} "
    memo += f"(Δ€{kpis['ending_cash']['delta']:+,.0f})\n"
    
    if kpis['runway_months']['before'] is not None and kpis['runway_months']['after'] is not None:
        memo += f"- **Runway:** {kpis['runway_months']['before']:.1f} → {kpis['runway_months']['after']:.1f} months "
        if kpis['runway_months']['delta'] is not None:
            memo += f"(Δ{kpis['runway_months']['delta']:+.1f} months)\n"
    
    memo += "\n## 3) Risks / Assumptions\n\n"
    if summary["high_risk_projects"]:
        memo += "- Projects with negative margins in scenario:\n"
        for p in summary["high_risk_projects"][:5]:
            memo += f"  - {p['project_id']}: {p['gross_margin_pct']:.1%} margin\n"
    else:
        memo += "- No projects with negative margins identified.\n"
    
    memo += "\n## 4) Recommended Next Actions\n\n"
    memo += "- Review top winners and losers to understand project-level impacts\n"
    memo += "- Monitor high-risk projects closely\n"
    memo += "- Validate assumptions underlying scenario changes\n"
    memo += "- Consider additional scenario variations\n"
    
    return memo
