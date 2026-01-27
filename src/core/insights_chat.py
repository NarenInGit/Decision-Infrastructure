"""
Insights Chat - Deterministic retrieval and answer building.
Parses user queries and builds answers from ONLY precomputed metrics and insights.
"""

import re
import pandas as pd
from typing import Dict, List, Optional, Tuple


def parse_intent(user_query: str) -> Dict:
    """
    Parse user query to extract intent and entities.
    
    Returns:
        {
            "intent": str (project, employee, company, invoices, cashflow, utilization, generic),
            "entity_id": str or None,
            "keywords": List[str]
        }
    """
    query_lower = user_query.lower()
    keywords = query_lower.split()
    
    # Try to extract project ID (e.g., P009, P001)
    project_match = re.search(r'\b(P\d+)\b', user_query, re.IGNORECASE)
    if project_match:
        return {
            "intent": "project",
            "entity_id": project_match.group(1).upper(),
            "keywords": keywords
        }
    
    # Try to extract employee ID (e.g., E017, E001)
    employee_match = re.search(r'\b(E\d+)\b', user_query, re.IGNORECASE)
    if employee_match:
        return {
            "intent": "employee",
            "entity_id": employee_match.group(1).upper(),
            "keywords": keywords
        }
    
    # Intent detection based on keywords
    if any(kw in query_lower for kw in ["invoice", "overdue", "unpaid", "payment"]):
        return {"intent": "invoices", "entity_id": None, "keywords": keywords}
    
    if any(kw in query_lower for kw in ["cash", "runway", "burn"]):
        return {"intent": "cashflow", "entity_id": None, "keywords": keywords}
    
    if any(kw in query_lower for kw in ["utilization", "utilized", "underutilized", "overutilized", "capacity"]):
        return {"intent": "utilization", "entity_id": None, "keywords": keywords}
    
    if any(kw in query_lower for kw in ["project", "margin", "profitability", "unprofitable"]):
        return {"intent": "project", "entity_id": None, "keywords": keywords}
    
    if any(kw in query_lower for kw in ["employee", "people", "person", "team"]):
        return {"intent": "employee", "entity_id": None, "keywords": keywords}
    
    if any(kw in query_lower for kw in ["revenue", "ebitda", "company", "overall", "total"]):
        return {"intent": "company", "entity_id": None, "keywords": keywords}
    
    return {"intent": "generic", "entity_id": None, "keywords": keywords}


def retrieve_context(
    intent: Dict,
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """
    Retrieve deterministic context based on intent.
    
    Returns:
        {
            "metrics": Dict,
            "insights": List[Dict],
            "trends": Dict (optional)
        }
    """
    intent_type = intent["intent"]
    entity_id = intent["entity_id"]
    
    if intent_type == "project":
        return _retrieve_project_context(entity_id, metrics_outputs, insights_list)
    elif intent_type == "employee":
        return _retrieve_employee_context(entity_id, metrics_outputs, insights_list)
    elif intent_type == "invoices":
        return _retrieve_invoices_context(metrics_outputs, insights_list)
    elif intent_type == "cashflow":
        return _retrieve_cashflow_context(metrics_outputs, insights_list)
    elif intent_type == "utilization":
        return _retrieve_utilization_context(metrics_outputs, insights_list)
    elif intent_type == "company":
        return _retrieve_company_context(metrics_outputs, insights_list)
    else:
        return _retrieve_generic_context(metrics_outputs, insights_list)


def _retrieve_project_context(
    project_id: Optional[str],
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve project-specific context."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    projects_metrics = metrics_outputs.get("projects_metrics")
    projects_monthly = metrics_outputs.get("projects_metrics_monthly")
    
    # Get project-level insights
    if project_id:
        context["insights"] = [i for i in insights_list if i["entity"] == project_id]
    else:
        # Get all project insights, sorted by severity
        context["insights"] = [i for i in insights_list if i["type"].startswith("project")]
        context["insights"] = sorted(
            context["insights"],
            key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
        )[:10]  # Limit to top 10
    
    # Get metrics
    if projects_metrics is not None and len(projects_metrics) > 0:
        if project_id:
            project_row = projects_metrics[projects_metrics["project_id"] == project_id]
            if len(project_row) > 0:
                context["metrics"] = project_row.iloc[0].to_dict()
        else:
            # Get worst projects by margin
            sorted_projects = projects_metrics.sort_values("gross_margin_pct")
            context["metrics"]["worst_projects"] = sorted_projects.head(5).to_dict("records")
    
    # Get trends (last 3 months)
    if projects_monthly is not None and len(projects_monthly) > 0 and project_id:
        project_monthly = projects_monthly[projects_monthly["project_id"] == project_id]
        if len(project_monthly) > 0:
            # Filter out "Total" rows
            if "month" in project_monthly.columns:
                project_monthly = project_monthly[project_monthly["month"].astype(str) != "Total"]
            
            recent = project_monthly.tail(3)
            if len(recent) > 0:
                context["trends"]["recent_months"] = recent.to_dict("records")
    
    return context


def _retrieve_employee_context(
    employee_id: Optional[str],
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve employee-specific context."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    employee_util = metrics_outputs.get("employee_utilization")
    
    # Get employee insights
    if employee_id:
        context["insights"] = [i for i in insights_list if i["entity"] == employee_id]
    else:
        context["insights"] = [i for i in insights_list if i["type"].startswith("employee")]
        context["insights"] = sorted(
            context["insights"],
            key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
        )[:10]
    
    # Get metrics
    if employee_util is not None and len(employee_util) > 0:
        if employee_id:
            emp_row = employee_util[employee_util["employee_id"] == employee_id]
            if len(emp_row) > 0:
                context["metrics"] = emp_row.iloc[0].to_dict()
        else:
            # Get underutilized and overutilized
            underutil = employee_util[employee_util["utilization_pct"] < 0.6]
            overutil = employee_util[employee_util["utilization_pct"] > 0.85]
            context["metrics"]["underutilized"] = underutil.to_dict("records") if len(underutil) > 0 else []
            context["metrics"]["overutilized"] = overutil.to_dict("records") if len(overutil) > 0 else []
    
    return context


def _retrieve_invoices_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve invoices context."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    # Get invoice insights
    context["insights"] = [i for i in insights_list if i["type"].startswith("invoices")]
    
    # Could add more invoice metrics here if available
    context["metrics"]["insight_count"] = len(context["insights"])
    
    return context


def _retrieve_cashflow_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve cashflow context."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    cashflow_monthly = metrics_outputs.get("cashflow_monthly")
    
    # Get cashflow insights
    context["insights"] = [i for i in insights_list if i["type"].startswith("cashflow")]
    
    # Get metrics
    if cashflow_monthly is not None and len(cashflow_monthly) > 0:
        # Filter out "Total" row
        df = cashflow_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        if len(df) > 0:
            context["metrics"]["ending_cash"] = df["ending_cash"].iloc[-1]
            context["metrics"]["runway_months"] = metrics_outputs.get("runway_months", 0)
            
            # Negative cashflow months
            negative_months = df[df["net_cashflow"] < 0]
            context["metrics"]["negative_cashflow_months"] = len(negative_months)
            
            # Recent trend
            recent = df.tail(3)
            context["trends"]["recent_months"] = recent[["month", "cash_in", "cash_out_total", "net_cashflow", "ending_cash"]].to_dict("records")
    
    return context


def _retrieve_utilization_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve utilization context."""
    return _retrieve_employee_context(None, metrics_outputs, insights_list)


def _retrieve_company_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve company-level context."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    income_monthly = metrics_outputs.get("income_statement_monthly")
    
    # Get company insights
    context["insights"] = [i for i in insights_list if i["entity"] == "company"]
    
    # Get metrics
    if income_monthly is not None and len(income_monthly) > 0:
        df = income_monthly.copy()
        if "month" in df.columns:
            df["month"] = df["month"].astype(str)
            df = df[df["month"] != "Total"]
        
        if len(df) > 0:
            context["metrics"]["total_revenue"] = df["revenue"].sum()
            context["metrics"]["total_ebitda"] = df["ebitda"].sum()
            
            # Negative EBITDA months
            negative_months = df[df["ebitda"] < 0]
            context["metrics"]["negative_ebitda_months"] = len(negative_months)
            
            # Recent trend
            recent = df.tail(3)
            context["trends"]["recent_months"] = recent[["month", "revenue", "ebitda"]].to_dict("records")
    
    return context


def _retrieve_generic_context(
    metrics_outputs: Dict,
    insights_list: List[Dict]
) -> Dict:
    """Retrieve generic context (top insights across all categories)."""
    context = {"metrics": {}, "insights": [], "trends": {}}
    
    # Get top insights by severity
    sorted_insights = sorted(
        insights_list,
        key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
    )
    context["insights"] = sorted_insights[:10]
    
    return context


def build_deterministic_answer(user_query: str, context: Dict, intent: Dict) -> Dict:
    """
    Build deterministic answer from context.
    
    Returns:
        {
            "final_answer": str,
            "facts_used": List[str],
            "matched_insights": List[str],
            "followups": List[str]
        }
    """
    intent_type = intent["intent"]
    entity_id = intent["entity_id"]
    
    if intent_type == "project":
        return _build_project_answer(user_query, context, entity_id)
    elif intent_type == "employee":
        return _build_employee_answer(user_query, context, entity_id)
    elif intent_type == "invoices":
        return _build_invoices_answer(user_query, context)
    elif intent_type == "cashflow":
        return _build_cashflow_answer(user_query, context)
    elif intent_type == "utilization":
        return _build_utilization_answer(user_query, context)
    elif intent_type == "company":
        return _build_company_answer(user_query, context)
    else:
        return _build_generic_answer(user_query, context)


def _build_project_answer(user_query: str, context: Dict, project_id: Optional[str]) -> Dict:
    """Build answer for project queries."""
    metrics = context.get("metrics", {})
    insights = context.get("insights", [])
    trends = context.get("trends", {})
    
    facts_used = []
    answer_lines = []
    matched_insights = []
    followups = []
    
    if project_id and metrics:
        # Specific project
        answer_lines.append(f"**Project {project_id} Analysis:**")
        answer_lines.append("")
        
        # Key metrics
        revenue = metrics.get("revenue", 0)
        gross_profit = metrics.get("gross_profit", 0)
        gross_margin_pct = metrics.get("gross_margin_pct", 0)
        labor_cost = metrics.get("labor_cost", 0)
        billable_hours = metrics.get("billable_hours", 0)
        
        facts_used.append(f"Revenue: €{revenue:,.0f}")
        facts_used.append(f"Gross profit: €{gross_profit:,.0f}")
        facts_used.append(f"Gross margin: {gross_margin_pct:.1%}")
        facts_used.append(f"Labor cost: €{labor_cost:,.0f}")
        facts_used.append(f"Billable hours: {billable_hours:.1f}")
        
        if gross_margin_pct < 0:
            answer_lines.append(f"- This project is **unprofitable** with a {gross_margin_pct:.1%} margin")
            answer_lines.append(f"- Costs (€{labor_cost:,.0f}) exceed revenue (€{revenue:,.0f})")
        elif gross_margin_pct < 0.1:
            answer_lines.append(f"- This project has a **low margin** of {gross_margin_pct:.1%}")
        else:
            answer_lines.append(f"- This project has a {gross_margin_pct:.1%} margin")
        
        # Trends
        if trends.get("recent_months"):
            recent = trends["recent_months"]
            if len(recent) >= 2:
                first_margin = recent[0].get("gross_margin_pct", 0)
                last_margin = recent[-1].get("gross_margin_pct", 0)
                if last_margin < first_margin:
                    answer_lines.append(f"- Margin has **declined** from {first_margin:.1%} to {last_margin:.1%} over recent months")
                    facts_used.append(f"Margin trend: {first_margin:.1%} → {last_margin:.1%}")
        
        followups = [
            f"Show monthly trend for {project_id}",
            f"Who is working on {project_id}?",
            "Which other projects are unprofitable?"
        ]
    
    elif "worst_projects" in metrics:
        # Multiple projects
        answer_lines.append("**Projects with Low/Negative Margins:**")
        answer_lines.append("")
        
        worst = metrics["worst_projects"]
        for proj in worst[:5]:
            pid = proj.get("project_id", "?")
            margin = proj.get("gross_margin_pct", 0)
            revenue = proj.get("revenue", 0)
            answer_lines.append(f"- **{pid}**: {margin:.1%} margin (€{revenue:,.0f} revenue)")
            facts_used.append(f"{pid}: {margin:.1%} margin, €{revenue:,.0f} revenue")
        
        followups = [
            "Why is P009 unprofitable?",
            "Show all project margins",
            "Which projects are most profitable?"
        ]
    
    # Add insights
    if insights:
        answer_lines.append("")
        answer_lines.append("**Key Issues:**")
        for insight in insights[:5]:
            answer_lines.append(f"- {insight['message']}")
            matched_insights.append(insight['message'])
            # Add drivers
            for driver in insight.get("drivers", [])[:2]:
                answer_lines.append(f"  - {driver}")
    
    final_answer = "\n".join(answer_lines)
    
    return {
        "final_answer": final_answer,
        "facts_used": facts_used,
        "matched_insights": matched_insights,
        "followups": followups
    }


def _build_employee_answer(user_query: str, context: Dict, employee_id: Optional[str]) -> Dict:
    """Build answer for employee queries."""
    metrics = context.get("metrics", {})
    insights = context.get("insights", [])
    
    facts_used = []
    answer_lines = []
    matched_insights = []
    followups = []
    
    if employee_id and metrics:
        # Specific employee
        answer_lines.append(f"**Employee {employee_id} Analysis:**")
        answer_lines.append("")
        
        utilization_pct = metrics.get("utilization_pct", 0)
        billable_hours = metrics.get("billable_hours", 0)
        capacity = metrics.get("monthly_capacity_hours", 0)
        
        facts_used.append(f"Utilization: {utilization_pct:.1%}")
        facts_used.append(f"Billable hours: {billable_hours:.1f}")
        facts_used.append(f"Capacity: {capacity:.1f}")
        
        if utilization_pct < 0.6:
            answer_lines.append(f"- **Underutilized** at {utilization_pct:.1%}")
            answer_lines.append(f"- Billable hours ({billable_hours:.1f}) below capacity ({capacity:.1f})")
        elif utilization_pct > 0.85:
            answer_lines.append(f"- **Overutilized** at {utilization_pct:.1%}")
            answer_lines.append(f"- Working above healthy capacity")
        else:
            answer_lines.append(f"- Utilization is {utilization_pct:.1%}")
        
        followups = [
            f"What projects is {employee_id} on?",
            "Who else is underutilized?",
            "Show team utilization"
        ]
    
    else:
        # Multiple employees
        answer_lines.append("**Employee Utilization:**")
        answer_lines.append("")
        
        underutil = metrics.get("underutilized", [])
        overutil = metrics.get("overutilized", [])
        
        if underutil:
            answer_lines.append("**Underutilized:**")
            for emp in underutil[:5]:
                eid = emp.get("employee_id", "?")
                util = emp.get("utilization_pct", 0)
                answer_lines.append(f"- {eid}: {util:.1%}")
                facts_used.append(f"{eid}: {util:.1%} utilization")
        
        if overutil:
            answer_lines.append("")
            answer_lines.append("**Overutilized:**")
            for emp in overutil[:5]:
                eid = emp.get("employee_id", "?")
                util = emp.get("utilization_pct", 0)
                answer_lines.append(f"- {eid}: {util:.1%}")
                facts_used.append(f"{eid}: {util:.1%} utilization")
        
        followups = [
            "Show E017 details",
            "Why is E003 underutilized?",
            "Show all employees"
        ]
    
    # Add insights
    if insights:
        answer_lines.append("")
        answer_lines.append("**Key Issues:**")
        for insight in insights[:5]:
            answer_lines.append(f"- {insight['message']}")
            matched_insights.append(insight['message'])
    
    final_answer = "\n".join(answer_lines)
    
    return {
        "final_answer": final_answer,
        "facts_used": facts_used,
        "matched_insights": matched_insights,
        "followups": followups
    }


def _build_invoices_answer(user_query: str, context: Dict) -> Dict:
    """Build answer for invoice queries."""
    insights = context.get("insights", [])
    
    answer_lines = ["**Invoice Status:**", ""]
    facts_used = []
    matched_insights = []
    
    if insights:
        for insight in insights:
            answer_lines.append(f"- {insight['message']}")
            matched_insights.append(insight['message'])
            for driver in insight.get("drivers", []):
                answer_lines.append(f"  - {driver}")
                facts_used.append(driver)
    else:
        answer_lines.append("- No overdue invoice issues detected")
    
    followups = [
        "Show cashflow status",
        "Which clients have overdue invoices?",
        "Show revenue trend"
    ]
    
    return {
        "final_answer": "\n".join(answer_lines),
        "facts_used": facts_used,
        "matched_insights": matched_insights,
        "followups": followups
    }


def _build_cashflow_answer(user_query: str, context: Dict) -> Dict:
    """Build answer for cashflow queries."""
    metrics = context.get("metrics", {})
    insights = context.get("insights", [])
    trends = context.get("trends", {})
    
    answer_lines = ["**Cashflow Status:**", ""]
    facts_used = []
    matched_insights = []
    
    ending_cash = metrics.get("ending_cash", 0)
    runway = metrics.get("runway_months", 0)
    negative_months = metrics.get("negative_cashflow_months", 0)
    
    facts_used.append(f"Ending cash: €{ending_cash:,.0f}")
    facts_used.append(f"Runway: {runway:.1f} months")
    
    answer_lines.append(f"- Current cash: €{ending_cash:,.0f}")
    answer_lines.append(f"- Runway: {runway:.1f} months")
    
    if negative_months > 0:
        answer_lines.append(f"- {negative_months} month(s) with negative cashflow")
        facts_used.append(f"Negative cashflow months: {negative_months}")
    
    # Trends
    if trends.get("recent_months"):
        answer_lines.append("")
        answer_lines.append("**Recent Trend:**")
        for month_data in trends["recent_months"]:
            month = month_data.get("month", "?")
            net_cf = month_data.get("net_cashflow", 0)
            answer_lines.append(f"- {month}: €{net_cf:,.0f} net cashflow")
    
    # Insights
    if insights:
        answer_lines.append("")
        answer_lines.append("**Key Issues:**")
        for insight in insights:
            answer_lines.append(f"- {insight['message']}")
            matched_insights.append(insight['message'])
    
    followups = [
        "Which invoices are overdue?",
        "Show monthly expenses",
        "Show revenue trend"
    ]
    
    return {
        "final_answer": "\n".join(answer_lines),
        "facts_used": facts_used,
        "matched_insights": matched_insights,
        "followups": followups
    }


def _build_utilization_answer(user_query: str, context: Dict) -> Dict:
    """Build answer for utilization queries."""
    return _build_employee_answer(user_query, context, None)


def _build_company_answer(user_query: str, context: Dict) -> Dict:
    """Build answer for company queries."""
    metrics = context.get("metrics", {})
    insights = context.get("insights", [])
    trends = context.get("trends", {})
    
    answer_lines = ["**Company Performance:**", ""]
    facts_used = []
    matched_insights = []
    
    revenue = metrics.get("total_revenue", 0)
    ebitda = metrics.get("total_ebitda", 0)
    negative_months = metrics.get("negative_ebitda_months", 0)
    
    facts_used.append(f"Total revenue: €{revenue:,.0f}")
    facts_used.append(f"Total EBITDA: €{ebitda:,.0f}")
    
    answer_lines.append(f"- Total revenue: €{revenue:,.0f}")
    answer_lines.append(f"- Total EBITDA: €{ebitda:,.0f}")
    
    if negative_months > 0:
        answer_lines.append(f"- {negative_months} month(s) with negative EBITDA")
        facts_used.append(f"Negative EBITDA months: {negative_months}")
    
    # Trends
    if trends.get("recent_months"):
        recent = trends["recent_months"]
        if len(recent) >= 2:
            first_rev = recent[0].get("revenue", 0)
            last_rev = recent[-1].get("revenue", 0)
            if last_rev < first_rev * 0.9:
                answer_lines.append(f"- Revenue declined from €{first_rev:,.0f} to €{last_rev:,.0f}")
                facts_used.append(f"Revenue trend: €{first_rev:,.0f} → €{last_rev:,.0f}")
    
    # Insights
    if insights:
        answer_lines.append("")
        answer_lines.append("**Key Issues:**")
        for insight in insights:
            answer_lines.append(f"- {insight['message']}")
            matched_insights.append(insight['message'])
    
    followups = [
        "Which projects are unprofitable?",
        "Show cashflow status",
        "Who is underutilized?"
    ]
    
    return {
        "final_answer": "\n".join(answer_lines),
        "facts_used": facts_used,
        "matched_insights": matched_insights,
        "followups": followups
    }


def _build_generic_answer(user_query: str, context: Dict) -> Dict:
    """Build answer for generic queries."""
    insights = context.get("insights", [])
    
    answer_lines = ["**Top Insights:**", ""]
    matched_insights = []
    
    if insights:
        for insight in insights[:10]:
            severity_badge = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(insight["severity"], "⚪")
            answer_lines.append(f"{severity_badge} {insight['message']}")
            matched_insights.append(insight['message'])
    else:
        answer_lines.append("No critical issues detected.")
    
    followups = [
        "Why is P009 unprofitable?",
        "Who is underutilized?",
        "Show cashflow status"
    ]
    
    return {
        "final_answer": "\n".join(answer_lines),
        "facts_used": [],
        "matched_insights": matched_insights,
        "followups": followups
    }
