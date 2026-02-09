"""
Brief Builder - Generate weekly attention briefs.
Ranks and prioritizes insights to answer: "What should I look at first?"
"""

import pandas as pd
from typing import Dict, List, Optional


def build_attention_brief(
    metrics_outputs: Dict,
    insights_list: List[Dict],
    window: str = "latest_month"
) -> Dict:
    """
    Build attention brief with top issues ranked by severity and impact.
    
    Args:
        metrics_outputs: Metrics engine outputs
        insights_list: List of all insights from insights_engine
        window: Time window ("latest_month", "all") - currently supports all
    
    Returns:
        {
            "top_critical": List[Dict],  # Top 3 critical issues
            "top_warnings": List[Dict],  # Top 3 warnings
            "key_changes": List[Dict],   # Key changes (if available)
            "summary_stats": Dict        # Quick stats
        }
    """
    # Rank critical issues
    critical_issues = [i for i in insights_list if i["severity"] == "critical"]
    ranked_critical = _rank_issues(critical_issues, metrics_outputs)
    
    # Rank warnings
    warnings = [i for i in insights_list if i["severity"] == "warning"]
    ranked_warnings = _rank_issues(warnings, metrics_outputs)
    
    # Key changes (if we have monthly data, detect trends)
    key_changes = _detect_key_changes(metrics_outputs)
    
    # Summary stats
    summary_stats = {
        "total_insights": len(insights_list),
        "critical_count": len(critical_issues),
        "warning_count": len(warnings),
        "info_count": len([i for i in insights_list if i["severity"] == "info"]),
        "affected_areas": _get_affected_areas(insights_list)
    }
    
    return {
        "top_critical": ranked_critical[:3],
        "top_warnings": ranked_warnings[:3],
        "key_changes": key_changes,
        "summary_stats": summary_stats
    }


def _rank_issues(issues: List[Dict], metrics_outputs: Dict) -> List[Dict]:
    """
    Rank issues by severity and impact.
    
    Ranking logic (deterministic):
    1. Projects: absolute gross_profit negative magnitude OR lowest margin %
    2. People: utilization distance from healthy range (0.6-0.85)
    3. Invoices: overdue amount/age (if available in drivers)
    4. Cash: lowest ending_cash or lowest runway
    """
    ranked = []
    
    projects_metrics = metrics_outputs.get("projects_metrics")
    employee_util = metrics_outputs.get("employee_utilization")
    cashflow_monthly = metrics_outputs.get("cashflow_monthly")
    
    for issue in issues:
        impact_score = 0
        entity_id = issue.get("entity")
        issue_type = issue.get("type")
        
        # Calculate impact score based on type
        if issue_type.startswith("project") and projects_metrics is not None:
            # Project impact: negative profit magnitude or low margin
            proj_row = projects_metrics[projects_metrics["project_id"] == entity_id]
            if len(proj_row) > 0:
                gross_profit = proj_row.iloc[0].get("gross_profit", 0)
                margin_pct = proj_row.iloc[0].get("gross_margin_pct", 0)
                
                if gross_profit < 0:
                    impact_score = abs(gross_profit)  # Higher negative = higher impact
                else:
                    impact_score = (1.0 - max(0, margin_pct)) * 10000  # Low margin score
        
        elif issue_type.startswith("employee") and employee_util is not None:
            # Employee impact: distance from healthy range
            emp_row = employee_util[employee_util["employee_id"] == entity_id]
            if len(emp_row) > 0:
                util_pct = emp_row.iloc[0].get("utilization_pct", 0.7)
                
                if util_pct < 0.6:
                    impact_score = (0.6 - util_pct) * 1000  # Underutilization distance
                elif util_pct > 0.85:
                    impact_score = (util_pct - 0.85) * 1000  # Overutilization distance
        
        elif issue_type.startswith("cashflow") and cashflow_monthly is not None:
            # Cash impact: low cash or negative runway
            df = cashflow_monthly.copy()
            if "month" in df.columns:
                df["month"] = df["month"].astype(str)
                df = df[df["month"] != "Total"]
            
            if len(df) > 0:
                ending_cash = df["ending_cash"].iloc[-1]
                # Lower cash = higher impact
                impact_score = max(0, 100000 - ending_cash)
        
        elif issue_type.startswith("invoices"):
            # Invoice impact: try to extract amount from drivers
            impact_score = 5000  # Default medium impact
            for driver in issue.get("drivers", []):
                # Try to extract € amounts
                if "€" in driver:
                    try:
                        # Extract number after €
                        parts = driver.split("€")
                        if len(parts) > 1:
                            amount_str = parts[1].split()[0].replace(",", "")
                            amount = float(amount_str)
                            impact_score = max(impact_score, amount)
                    except:
                        pass
        
        else:
            # Default impact score
            impact_score = 1000
        
        ranked.append({
            **issue,
            "impact_score": impact_score
        })
    
    # Sort by impact_score descending
    ranked.sort(key=lambda x: x["impact_score"], reverse=True)
    
    return ranked


def _detect_key_changes(metrics_outputs: Dict) -> List[Dict]:
    """
    Detect key changes from month-to-month trends.
    Returns empty list if monthly data not available.
    """
    changes = []
    
    projects_monthly = metrics_outputs.get("projects_metrics_monthly")
    income_monthly = metrics_outputs.get("income_statement_monthly")
    
    # Revenue trend
    if income_monthly is not None and len(income_monthly) > 0:
        df = income_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        if len(df) >= 2:
            recent = df.tail(2)
            prev_revenue = recent.iloc[0]["revenue"]
            curr_revenue = recent.iloc[1]["revenue"]
            
            if curr_revenue < prev_revenue * 0.9:
                changes.append({
                    "type": "revenue_decline",
                    "message": f"Revenue declined from €{prev_revenue:,.0f} to €{curr_revenue:,.0f}",
                    "affects": ["profitability", "cash"]
                })
            elif curr_revenue > prev_revenue * 1.1:
                changes.append({
                    "type": "revenue_growth",
                    "message": f"Revenue grew from €{prev_revenue:,.0f} to €{curr_revenue:,.0f}",
                    "affects": ["profitability"]
                })
    
    # Project margin trends (if available)
    if projects_monthly is not None and len(projects_monthly) > 0:
        df = projects_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        # Find projects with declining margins
        for project_id in df["project_id"].unique():
            proj_df = df[df["project_id"] == project_id]
            if len(proj_df) >= 2:
                recent = proj_df.tail(2)
                prev_margin = recent.iloc[0].get("gross_margin_pct", 0)
                curr_margin = recent.iloc[1].get("gross_margin_pct", 0)
                
                if curr_margin < prev_margin - 0.1:  # More than 10pp decline
                    changes.append({
                        "type": "project_margin_decline",
                        "message": f"Project {project_id} margin declined from {prev_margin:.1%} to {curr_margin:.1%}",
                        "affects": ["profitability"]
                    })
    
    return changes[:5]  # Limit to 5 changes


def _get_affected_areas(insights_list: List[Dict]) -> Dict[str, int]:
    """
    Count how many insights affect each area (profitability, cash, utilization).
    """
    areas = {
        "profitability": 0,
        "cash": 0,
        "utilization": 0
    }
    
    for insight in insights_list:
        insight_type = insight["type"]
        
        if insight_type.startswith("project"):
            areas["profitability"] += 1
        elif insight_type.startswith("cashflow") or insight_type.startswith("invoices"):
            areas["cash"] += 1
        elif insight_type.startswith("employee"):
            areas["utilization"] += 1
    
    return areas


def generate_shareable_brief(
    brief: Dict,
    format: str = "email"
) -> str:
    """
    Generate copy-ready text for sharing the brief.
    
    Args:
        brief: Brief dict from build_attention_brief
        format: "slack", "email", or "investor"
    
    Returns:
        Formatted text string ready to copy/paste
    """
    if format == "slack":
        return _generate_slack_brief(brief)
    elif format == "email":
        return _generate_email_brief(brief)
    elif format == "investor":
        return _generate_investor_brief(brief)
    else:
        return _generate_email_brief(brief)


def _generate_slack_brief(brief: Dict) -> str:
    """Generate short Slack update."""
    stats = brief["summary_stats"]
    
    text = f"📊 *Weekly Brief*\n\n"
    text += f"🔴 {stats['critical_count']} critical issues | 🟡 {stats['warning_count']} warnings\n\n"
    
    if brief["top_critical"]:
        text += "*Top Issues:*\n"
        for issue in brief["top_critical"][:3]:
            text += f"• {issue['message']}\n"
    
    text += f"\n_Generated from computed data; no predictions_"
    
    return text


def _generate_email_brief(brief: Dict) -> str:
    """Generate structured email memo."""
    stats = brief["summary_stats"]
    
    text = f"## Weekly Financial Brief\n\n"
    text += f"**Summary:** {stats['critical_count']} critical issues, {stats['warning_count']} warnings detected.\n\n"
    
    if brief["top_critical"]:
        text += "### Critical Issues\n\n"
        for idx, issue in enumerate(brief["top_critical"], 1):
            text += f"{idx}. **{issue['message']}**\n"
            if issue.get("drivers"):
                text += f"   - {issue['drivers'][0]}\n"
            text += "\n"
    
    if brief["top_warnings"]:
        text += "### Warnings\n\n"
        for idx, issue in enumerate(brief["top_warnings"], 1):
            text += f"{idx}. {issue['message']}\n"
        text += "\n"
    
    if brief["key_changes"]:
        text += "### Key Changes\n\n"
        for change in brief["key_changes"][:3]:
            text += f"- {change['message']}\n"
        text += "\n"
    
    text += "---\n"
    text += "_This brief is generated from computed financial data. No predictions or forecasts included._\n"
    
    return text


def _generate_investor_brief(brief: Dict) -> str:
    """Generate neutral investor note."""
    stats = brief["summary_stats"]
    
    text = f"## Financial Update\n\n"
    text += f"**Current Status:** The financial analysis identified {stats['total_insights']} areas requiring attention.\n\n"
    
    # Focus on facts, avoid alarming language
    affected = stats["affected_areas"]
    
    text += "**Key Areas:**\n\n"
    
    if affected["profitability"] > 0:
        text += f"- **Profitability:** {affected['profitability']} project-level items\n"
        if brief["top_critical"]:
            for issue in brief["top_critical"]:
                if issue["type"].startswith("project"):
                    text += f"  - {issue['message']}\n"
                    break
    
    if affected["cash"] > 0:
        text += f"- **Cash Management:** {affected['cash']} items\n"
    
    if affected["utilization"] > 0:
        text += f"- **Resource Utilization:** {affected['utilization']} items\n"
    
    text += "\n---\n"
    text += "_Data based on actual financial computations. No forward-looking statements included._\n"
    
    return text
