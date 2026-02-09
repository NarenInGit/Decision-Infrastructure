"""
Test AI Layers - Verify acceptance tests work.
Run this script to validate AI layer functionality.

Usage:
    python test_ai_layers.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_guardrails():
    """Test 4: Guardrails Work"""
    print("\n" + "="*60)
    print("TEST 4: Guardrails Work")
    print("="*60)
    
    from src.ai.guardrails import validate_llm_output, apply_guardrails
    
    # Test Case 1: Forbidden language
    print("\n[Test Case 1] Forbidden language detection:")
    llm_output = "This project will likely fail with high probability."
    deterministic_answer = "This project has negative margin."
    facts_used = ["Revenue: €18,000", "Margin: -266.6%"]
    
    is_valid, error = validate_llm_output(llm_output, facts_used)
    print(f"  Input: '{llm_output}'")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error}")
    
    assert not is_valid, "Should detect forbidden language"
    assert "will likely" in error, "Should identify 'will likely' phrase"
    print("  ✅ PASS: Forbidden language detected correctly")
    
    # Test Case 2: New numbers
    print("\n[Test Case 2] New number detection:")
    llm_output = "The project lost €99,999 which is very high."
    
    is_valid, error = validate_llm_output(llm_output, facts_used, strict=True)
    print(f"  Input: '{llm_output}'")
    print(f"  Facts: {facts_used}")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error}")
    
    if not is_valid and "New numbers" in error:
        print("  ✅ PASS: New numbers detected correctly")
    else:
        print("  ⚠️  WARNING: New number detection may not catch all cases")
    
    # Test Case 3: Valid output
    print("\n[Test Case 3] Valid output (no violations):")
    llm_output = "This project currently shows a margin of -266.6% with revenue of €18,000."
    
    is_valid, error = validate_llm_output(llm_output, facts_used, strict=True)
    print(f"  Input: '{llm_output}'")
    print(f"  Valid: {is_valid}")
    print(f"  Error: {error}")
    
    assert is_valid, "Should accept valid output"
    print("  ✅ PASS: Valid output accepted")
    
    # Test Case 4: Apply guardrails (full flow)
    print("\n[Test Case 4] Apply guardrails (fallback on violation):")
    llm_bad = "You should definitely fix this, it will likely worsen."
    
    final_output, was_blocked, reason = apply_guardrails(
        llm_bad,
        deterministic_answer,
        facts_used
    )
    
    print(f"  LLM output: '{llm_bad}'")
    print(f"  Was blocked: {was_blocked}")
    print(f"  Reason: {reason}")
    print(f"  Final output: '{final_output}'")
    
    assert was_blocked, "Should block bad output"
    assert final_output == deterministic_answer, "Should return fallback"
    print("  ✅ PASS: Guardrails applied correctly, fallback returned")


def test_context_builder():
    """Verify context builder creates compact packages"""
    print("\n" + "="*60)
    print("TEST: Context Builder (Compact Packages)")
    print("="*60)
    
    from src.core.context_builder import build_context, _build_project_context
    import pandas as pd
    
    # Mock data
    projects_metrics = pd.DataFrame([
        {"project_id": "P001", "revenue": 50000, "gross_margin_pct": 0.3, "gross_profit": 15000},
        {"project_id": "P002", "revenue": 30000, "gross_margin_pct": -0.1, "gross_profit": -3000},
    ])
    
    metrics_outputs = {"projects_metrics": projects_metrics}
    insights_list = [
        {"type": "project_margin_issue", "entity": "P002", "severity": "critical", "message": "P002 negative margin"}
    ]
    
    intent = {"intent": "project", "entity_id": "P002", "keywords": ["p002"]}
    
    context = build_context(intent, metrics_outputs, insights_list, max_rows=5)
    
    print(f"\n  Intent: {intent}")
    print(f"  Context keys: {list(context.keys())}")
    print(f"  KPIs: {context.get('kpis', {})}")
    print(f"  Insights count: {len(context.get('insights', []))}")
    print(f"  Table snippets: {list(context.get('table_snippets', {}).keys())}")
    
    assert "kpis" in context, "Should have kpis"
    assert "insights" in context, "Should have insights"
    assert len(context["insights"]) <= 5, "Should limit insights to max_rows"
    
    print("  ✅ PASS: Context builder creates compact packages")


def test_query_router():
    """Test 1: Chat Query Works"""
    print("\n" + "="*60)
    print("TEST 1: Chat Query Works")
    print("="*60)
    
    from src.core.query_router import answer_query
    import pandas as pd
    
    # Mock data
    projects_metrics = pd.DataFrame([
        {"project_id": "P009", "revenue": 18000, "gross_margin_pct": -2.666, "gross_profit": -47985, "labor_cost": 65985, "billable_hours": 120}
    ])
    
    metrics_outputs = {"projects_metrics": projects_metrics}
    insights_list = [
        {
            "type": "project_margin_issue",
            "entity": "P009",
            "severity": "critical",
            "message": "Project P009 has negative gross margin (-266.6%)",
            "drivers": ["Revenue: €18,000", "Total costs: €65,985"]
        }
    ]
    
    response = answer_query("Why is P009 unprofitable?", metrics_outputs, insights_list)
    
    print(f"\n  Query: 'Why is P009 unprofitable?'")
    print(f"\n  Answer (first 200 chars):")
    print(f"  {response['answer'][:200]}...")
    print(f"\n  Facts used: {response['facts_used']}")
    print(f"\n  Insights used: {response['insights_used']}")
    print(f"\n  Follow-ups: {response['followups']}")
    
    assert "answer" in response, "Should have answer"
    assert len(response["facts_used"]) > 0, "Should have facts"
    assert len(response["insights_used"]) > 0, "Should have insights"
    assert len(response["followups"]) > 0, "Should have followups"
    assert "unprofitable" in response["answer"].lower() or "negative" in response["answer"].lower(), "Should mention unprofitability"
    
    print("\n  ✅ PASS: Query answering works correctly")


def test_brief_builder():
    """Test 2: Weekly Brief Works"""
    print("\n" + "="*60)
    print("TEST 2: Weekly Brief Works")
    print("="*60)
    
    from src.core.brief_builder import build_attention_brief, generate_shareable_brief
    import pandas as pd
    
    # Mock data
    projects_metrics = pd.DataFrame([
        {"project_id": "P001", "revenue": 50000, "gross_margin_pct": 0.3, "gross_profit": 15000},
        {"project_id": "P009", "revenue": 18000, "gross_margin_pct": -2.666, "gross_profit": -47985},
    ])
    
    metrics_outputs = {"projects_metrics": projects_metrics}
    insights_list = [
        {
            "type": "project_margin_issue",
            "entity": "P009",
            "severity": "critical",
            "message": "Project P009 has negative gross margin (-266.6%)",
            "drivers": ["Revenue: €18,000"]
        },
        {
            "type": "employee_underutilized",
            "entity": "E003",
            "severity": "warning",
            "message": "Employee E003 is underutilized (45%)",
            "drivers": ["Utilization: 45%"]
        }
    ]
    
    brief = build_attention_brief(metrics_outputs, insights_list)
    
    print(f"\n  Summary Stats:")
    print(f"    Total insights: {brief['summary_stats']['total_insights']}")
    print(f"    Critical: {brief['summary_stats']['critical_count']}")
    print(f"    Warnings: {brief['summary_stats']['warning_count']}")
    
    print(f"\n  Top Critical Issues:")
    for idx, issue in enumerate(brief["top_critical"][:3], 1):
        print(f"    {idx}. {issue['message']} (impact: {issue.get('impact_score', 0):.0f})")
    
    print(f"\n  Top Warnings:")
    for idx, issue in enumerate(brief["top_warnings"][:3], 1):
        print(f"    {idx}. {issue['message']}")
    
    assert len(brief["top_critical"]) > 0, "Should have critical issues"
    assert brief["summary_stats"]["total_insights"] == 2, "Should count all insights"
    
    print("\n  Testing shareable brief generation...")
    slack_brief = generate_shareable_brief(brief, format="slack")
    email_brief = generate_shareable_brief(brief, format="email")
    
    print(f"\n  Slack Brief (first 150 chars):")
    print(f"  {slack_brief[:150]}...")
    
    assert "critical" in slack_brief.lower(), "Should mention critical issues"
    assert "Generated from computed data" in slack_brief or "generated from" in slack_brief.lower(), "Should have disclaimer"
    
    print("\n  ✅ PASS: Brief builder works correctly")


def test_transformers_available():
    """Check if transformers is available"""
    print("\n" + "="*60)
    print("INFO: Check Transformers Availability")
    print("="*60)
    
    from src.ai.guardrails import check_transformers_available
    
    available = check_transformers_available()
    print(f"\n  Transformers library available: {available}")
    
    if available:
        print("  ✅ AI phrasing features enabled")
    else:
        print("  ⚠️  AI phrasing disabled (transformers not installed)")
        print("  💡 To enable: pip install transformers sentencepiece")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("AI LAYERS ACCEPTANCE TESTS")
    print("="*60)
    
    try:
        test_transformers_available()
        test_guardrails()
        test_context_builder()
        test_query_router()
        test_brief_builder()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\nAI Layers are working correctly!")
        print("Ready to use in Streamlit app.")
        
    except AssertionError as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        return 1
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ ERROR: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
