"""
Insights & Explanations UI Tab - Professional master-detail layout.
Displays deterministic insights with filters, sorting, and progressive disclosure.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from ..core.insights_engine import generate_insights
from ..ai.summary_builder import build_insights_summary
from ..ai.local_llm import generate_insights_explanation


def render_insights_tab(
    metrics_outputs: Dict,
    data: Dict,
    starting_cash: float
) -> None:
    """
    Render the Insights & Explanations tab with professional UX.
    
    Args:
        metrics_outputs: Dictionary with metrics engine outputs
        data: Raw data dict with invoices, etc.
        starting_cash: Starting cash balance
    """
    # Initialize session state for filters
    _initialize_session_state()
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Insights")
        st.caption("Deterministic insights from your financial data (no predictions).")
    with col2:
        refresh_time = datetime.now().strftime("%H:%M")
        st.caption(f"Last refresh: {refresh_time}")
    
    # Generate insights
    with st.spinner("Analyzing financial data..."):
        insights = generate_insights(
            projects_metrics=metrics_outputs.get("projects_metrics"),
            projects_metrics_monthly=metrics_outputs.get("projects_metrics_monthly"),
            employee_utilization=metrics_outputs.get("employee_utilization"),
            income_statement_monthly=metrics_outputs.get("income_statement_monthly"),
            cashflow_monthly=metrics_outputs.get("cashflow_monthly"),
            invoices=data.get("invoices")
        )
    
    if not insights:
        st.info("No insights found. Your metrics look good!")
        return
    
    # Extract key metrics for AI summary
    key_metrics = _extract_key_metrics(metrics_outputs, starting_cash)
    summary = build_insights_summary(insights, key_metrics)
    
    # KPI strip
    _render_kpi_strip(summary)
    
    st.divider()
    
    # Controls bar
    filtered_insights = _render_controls_and_filter(insights)
    
    st.divider()
    
    # Master-detail layout
    if filtered_insights:
        _render_master_detail_layout(filtered_insights, metrics_outputs)
    else:
        st.info("No insights match your current filters.")
    
    st.divider()
    
    # Category tabs (collapsed by default)
    _render_category_tabs(insights)
    
    st.divider()
    
    # AI Explanation (optional, collapsed)
    _render_ai_explanation(summary, filtered_insights)


def _initialize_session_state():
    """Initialize session state for filters and selection."""
    if "insights_severity_filter" not in st.session_state:
        st.session_state.insights_severity_filter = ["critical", "warning", "info"]
    if "insights_category_filter" not in st.session_state:
        st.session_state.insights_category_filter = ["Company", "Projects", "People", "Cash", "Invoices"]
    if "insights_search" not in st.session_state:
        st.session_state.insights_search = ""
    if "insights_sort" not in st.session_state:
        st.session_state.insights_sort = "Severity (desc)"
    if "insights_top_5" not in st.session_state:
        st.session_state.insights_top_5 = True
    if "insights_focus_mode" not in st.session_state:
        st.session_state.insights_focus_mode = False
    if "insights_selected_idx" not in st.session_state:
        st.session_state.insights_selected_idx = 0
    if "insights_page_size" not in st.session_state:
        st.session_state.insights_page_size = 15


def _extract_key_metrics(metrics_outputs: Dict, starting_cash: float) -> Dict:
    """Extract key metrics for AI summary."""
    income_monthly = metrics_outputs.get("income_statement_monthly")
    cashflow_monthly = metrics_outputs.get("cashflow_monthly")
    
    # Filter out "Total" rows
    income_df = pd.DataFrame()
    cashflow_df = pd.DataFrame()
    
    if income_monthly is not None and len(income_monthly) > 0:
        income_df = income_monthly.copy()
        if "month" in income_df.columns:
            income_df["month"] = income_df["month"].astype(str)
            income_df = income_df[income_df["month"] != "Total"]
    
    if cashflow_monthly is not None and len(cashflow_monthly) > 0:
        cashflow_df = cashflow_monthly.copy()
        if "month" in cashflow_df.columns:
            cashflow_df["month"] = cashflow_df["month"].astype(str)
            cashflow_df = cashflow_df[cashflow_df["month"] != "Total"]
    
    return {
        "revenue_total": income_df["revenue"].sum() if len(income_df) > 0 else 0,
        "ebitda_total": income_df["ebitda"].sum() if len(income_df) > 0 else 0,
        "ending_cash": cashflow_df["ending_cash"].iloc[-1] if len(cashflow_df) > 0 else starting_cash,
        "runway_months": metrics_outputs.get("runway_months", 0),
        "gross_profit_total": income_df["gross_profit"].sum() if len(income_df) > 0 else 0,
        "operating_expenses_total": income_df["operating_expenses"].sum() if len(income_df) > 0 else 0
    }


def _render_kpi_strip(summary: Dict):
    """Render compact KPI strip with tooltips."""
    counts = summary["summary_counts"]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Insights", counts["total_insights"])
    with col2:
        st.metric("🔴 Critical", counts["critical"], help="Issues requiring immediate attention")
    with col3:
        st.metric("🟡 Warnings", counts["warning"], help="Issues to monitor or investigate")
    with col4:
        st.metric("🔵 Info", counts["info"], help="Informational insights")


def _render_controls_and_filter(insights: List[Dict]) -> List[Dict]:
    """Render controls bar and return filtered insights."""
    st.subheader("Filters & Controls")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Severity filter
        severity_options = ["critical", "warning", "info"]
        selected_severity = st.multiselect(
            "Severity",
            severity_options,
            default=st.session_state.insights_severity_filter,
            key="severity_filter_widget"
        )
        st.session_state.insights_severity_filter = selected_severity
    
    with col2:
        # Category filter
        category_options = ["Company", "Projects", "People", "Cash", "Invoices"]
        selected_categories = st.multiselect(
            "Category",
            category_options,
            default=st.session_state.insights_category_filter,
            key="category_filter_widget"
        )
        st.session_state.insights_category_filter = selected_categories
    
    with col3:
        # Sort
        sort_options = ["Severity (desc)", "Entity (A-Z)"]
        selected_sort = st.selectbox(
            "Sort by",
            sort_options,
            index=sort_options.index(st.session_state.insights_sort),
            key="sort_widget"
        )
        st.session_state.insights_sort = selected_sort
    
    col4, col5 = st.columns([3, 1])
    
    with col4:
        # Search
        search_query = st.text_input(
            "Search (project_id, employee_id, keyword)",
            value=st.session_state.insights_search,
            key="search_widget"
        )
        st.session_state.insights_search = search_query
    
    with col5:
        st.write("")  # Spacing
        st.write("")  # Spacing
        # Focus mode toggle
        focus_mode = st.checkbox(
            "Focus Mode",
            value=st.session_state.insights_focus_mode,
            help="Show only Critical + top 3 Warnings",
            key="focus_mode_widget"
        )
        st.session_state.insights_focus_mode = focus_mode
    
    # Apply filters
    filtered = _apply_filters(insights, selected_severity, selected_categories, search_query, focus_mode)
    
    # Apply sorting
    filtered = _apply_sorting(filtered, selected_sort)
    
    return filtered


def _apply_filters(
    insights: List[Dict],
    severity_filter: List[str],
    category_filter: List[str],
    search_query: str,
    focus_mode: bool
) -> List[Dict]:
    """Apply all filters to insights."""
    filtered = insights
    
    # Severity filter
    if severity_filter:
        filtered = [i for i in filtered if i["severity"] in severity_filter]
    
    # Category filter
    if category_filter:
        category_map = {
            "Company": lambda i: i["entity"] == "company",
            "Projects": lambda i: i["type"].startswith("project"),
            "People": lambda i: i["type"].startswith("employee"),
            "Cash": lambda i: i["type"].startswith("cashflow") or i["type"].startswith("company"),
            "Invoices": lambda i: i["type"].startswith("invoices")
        }
        filtered = [i for i in filtered if any(category_map.get(cat, lambda x: False)(i) for cat in category_filter)]
    
    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            i for i in filtered
            if query_lower in i["entity"].lower() or
               query_lower in i["message"].lower() or
               query_lower in i["type"].lower()
        ]
    
    # Focus mode
    if focus_mode:
        critical = [i for i in filtered if i["severity"] == "critical"]
        warnings = [i for i in filtered if i["severity"] == "warning"][:3]
        filtered = critical + warnings
    
    return filtered


def _apply_sorting(insights: List[Dict], sort_by: str) -> List[Dict]:
    """Apply sorting to insights."""
    if sort_by == "Severity (desc)":
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        return sorted(insights, key=lambda x: severity_order.get(x["severity"], 3))
    elif sort_by == "Entity (A-Z)":
        return sorted(insights, key=lambda x: x["entity"])
    return insights


def _render_master_detail_layout(insights: List[Dict], metrics_outputs: Dict):
    """Render master-detail layout with inbox and detail panel."""
    st.subheader("Insight Details")
    
    # Limit to page size
    page_size = st.session_state.insights_page_size
    visible_insights = insights[:page_size]
    
    # Ensure selected index is valid
    if st.session_state.insights_selected_idx >= len(visible_insights):
        st.session_state.insights_selected_idx = 0
    
    # Two columns: inbox (left) and detail (right)
    col_inbox, col_detail = st.columns([1, 2])
    
    with col_inbox:
        st.markdown("**Insight Inbox**")
        _render_insight_inbox(visible_insights)
        
        # Load more button
        if len(insights) > page_size:
            if st.button(f"Load more ({len(insights) - page_size} remaining)"):
                st.session_state.insights_page_size += 15
                st.rerun()
    
    with col_detail:
        st.markdown("**Selected Insight**")
        if visible_insights:
            selected_insight = visible_insights[st.session_state.insights_selected_idx]
            _render_insight_detail(selected_insight, metrics_outputs)


def _render_insight_inbox(insights: List[Dict]):
    """Render compact inbox list of insights."""
    for idx, insight in enumerate(insights):
        severity_badge = _get_severity_badge(insight["severity"])
        entity_tag = _get_entity_tag(insight["entity"])
        
        # Truncate message for inbox
        message = insight["message"]
        if len(message) > 60:
            message = message[:57] + "..."
        
        # Button to select insight
        button_label = f"{severity_badge} {message}"
        is_selected = (idx == st.session_state.insights_selected_idx)
        
        # Use different styling for selected
        if st.button(
            button_label,
            key=f"insight_btn_{idx}",
            type="primary" if is_selected else "secondary",
            use_container_width=True
        ):
            st.session_state.insights_selected_idx = idx
            st.rerun()
        
        # Show entity tag below button
        st.caption(entity_tag)


def _render_insight_detail(insight: Dict, metrics_outputs: Dict):
    """Render detailed view of selected insight."""
    # Title and severity
    severity_badge = _get_severity_badge(insight["severity"])
    st.markdown(f"### {severity_badge} {insight['severity'].upper()}")
    
    # Message
    st.markdown(f"**{insight['message']}**")
    
    st.divider()
    
    # What it means
    st.markdown("**What it means**")
    explanation = _generate_insight_explanation(insight)
    st.write(explanation)
    
    st.divider()
    
    # Drivers
    st.markdown("**Drivers**")
    drivers = insight.get("drivers", [])
    if drivers:
        for driver in drivers:
            st.markdown(f"- {driver}")
    else:
        st.caption("No specific drivers identified.")
    
    st.divider()
    
    # Actions to consider
    st.markdown("**Actions to consider**")
    actions = _generate_suggested_actions(insight)
    for action in actions:
        st.markdown(f"- {action}")
    
    st.divider()
    
    # Copy summary button
    summary_text = _format_insight_summary(insight)
    st.text_area("Copy summary", value=summary_text, height=150, key=f"summary_{insight['type']}_{insight['entity']}")


def _get_severity_badge(severity: str) -> str:
    """Get severity badge emoji."""
    return {
        "critical": "🔴",
        "warning": "🟡",
        "info": "🔵"
    }.get(severity, "⚪")


def _get_entity_tag(entity: str) -> str:
    """Get formatted entity tag."""
    return f"📌 {entity}"


def _generate_insight_explanation(insight: Dict) -> str:
    """Generate a 1-2 sentence explanation of the insight."""
    insight_type = insight["type"]
    
    explanations = {
        "project_margin_issue": "This project's costs exceed or nearly exceed its revenue, indicating potential scope creep, underpricing, or inefficient delivery.",
        "project_rate_issue": "The effective hourly rate is below typical thresholds, suggesting pricing may not cover costs or billable hours are low relative to revenue.",
        "project_margin_decline": "Margin has decreased over recent months, which may indicate rising costs, scope changes, or pricing pressure.",
        "employee_underutilized": "This employee's billable hours are below capacity, indicating potential for more client work or a need to review workload allocation.",
        "employee_overutilized": "This employee's billable hours exceed healthy capacity, which may lead to burnout or quality issues.",
        "company_negative_ebitda": "Operating expenses exceed gross profit in some months, indicating the company is spending more than it earns from operations.",
        "company_revenue_decline": "Revenue is trending downward, which may reflect fewer projects, lower contract values, or client churn.",
        "cashflow_stress": "Cash reserves are declining, which reduces runway and may require attention to collections, expenses, or new revenue.",
        "cashflow_negative": "Cash outflows exceeded inflows in some months, reducing the cash buffer.",
        "invoices_overdue": "Some invoices remain unpaid past their due dates, affecting cashflow and requiring follow-up."
    }
    
    return explanations.get(insight_type, "This insight highlights a notable pattern in your financial data that may require attention.")


def _generate_suggested_actions(insight: Dict) -> List[str]:
    """Generate neutral, deterministic action suggestions."""
    insight_type = insight["type"]
    
    actions_map = {
        "project_margin_issue": [
            "Review project scope and deliverables",
            "Check for untracked time or expenses",
            "Verify contract pricing and change orders"
        ],
        "project_rate_issue": [
            "Review pricing relative to market rates",
            "Check billable vs. non-billable hour allocation",
            "Verify time tracking accuracy"
        ],
        "project_margin_decline": [
            "Investigate cost increases over recent months",
            "Review scope changes or creep",
            "Check for pricing adjustments or discounts"
        ],
        "employee_underutilized": [
            "Review current project assignments",
            "Consider allocating to additional projects",
            "Check for non-billable time patterns"
        ],
        "employee_overutilized": [
            "Review workload distribution",
            "Consider hiring or reallocating work",
            "Monitor for potential quality or burnout risks"
        ],
        "company_negative_ebitda": [
            "Review operating expense categories",
            "Identify opportunities to reduce overhead",
            "Consider revenue growth initiatives"
        ],
        "company_revenue_decline": [
            "Review active projects and pipeline",
            "Check for client churn or contract renewals",
            "Investigate market or pricing factors"
        ],
        "cashflow_stress": [
            "Accelerate invoice collections",
            "Review payment terms with clients",
            "Consider expense timing or reductions"
        ],
        "cashflow_negative": [
            "Review timing of cash inflows and outflows",
            "Check invoice payment status",
            "Consider adjusting payment schedules"
        ],
        "invoices_overdue": [
            "Follow up on outstanding invoices",
            "Review payment terms with clients",
            "Check for invoicing errors or disputes"
        ]
    }
    
    return actions_map.get(insight_type, [
        "Review the underlying data",
        "Investigate potential root causes",
        "Monitor the trend over time"
    ])


def _format_insight_summary(insight: Dict) -> str:
    """Format insight as copyable text summary."""
    lines = []
    lines.append(f"INSIGHT: {insight['message']}")
    lines.append(f"SEVERITY: {insight['severity'].upper()}")
    lines.append(f"ENTITY: {insight['entity']}")
    lines.append(f"TYPE: {insight['type']}")
    lines.append("")
    lines.append("DRIVERS:")
    for driver in insight.get("drivers", []):
        lines.append(f"  - {driver}")
    lines.append("")
    lines.append("SUGGESTED ACTIONS:")
    for action in _generate_suggested_actions(insight):
        lines.append(f"  - {action}")
    return "\n".join(lines)


def _render_category_tabs(insights: List[Dict]):
    """Render category tabs (collapsed by default)."""
    with st.expander("Browse by Category", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Company", "Projects", "People", "Cash & Invoices"])
        
        with tab1:
            company_insights = [i for i in insights if i["entity"] == "company"]
            _render_category_insights(company_insights, "Company")
        
        with tab2:
            project_insights = [i for i in insights if i["type"].startswith("project")]
            _render_category_insights(project_insights, "Projects")
        
        with tab3:
            employee_insights = [i for i in insights if i["type"].startswith("employee")]
            _render_category_insights(employee_insights, "People")
        
        with tab4:
            cash_insights = [i for i in insights if i["type"].startswith("cashflow") or i["type"].startswith("invoices")]
            _render_category_insights(cash_insights, "Cash & Invoices")


def _render_category_insights(insights: List[Dict], category_name: str):
    """Render insights for a specific category."""
    if not insights:
        st.info(f"No {category_name} insights found.")
        return
    
    # Show top 5 by default
    display_count = 5
    top_insights = insights[:display_count]
    
    for insight in top_insights:
        severity_badge = _get_severity_badge(insight["severity"])
        st.markdown(f"{severity_badge} **{insight['message']}**")
        st.caption(f"{insight['entity']} | {insight['type']}")
    
    if len(insights) > display_count:
        if st.button(f"Show all {len(insights)} insights", key=f"show_all_{category_name}"):
            for insight in insights[display_count:]:
                severity_badge = _get_severity_badge(insight["severity"])
                st.markdown(f"{severity_badge} **{insight['message']}**")
                st.caption(f"{insight['entity']} | {insight['type']}")


def _render_ai_explanation(summary: Dict, filtered_insights: List[Dict]):
    """Render AI explanation section (optional, collapsed)."""
    with st.expander("AI Explanation (optional)", expanded=False):
        st.caption("Generated from pre-calculated metrics. No predictions. No new numbers.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Generate explanation for all insights"):
                with st.spinner("Generating explanation..."):
                    explanation = generate_insights_explanation(summary)
                    st.session_state["insights_explanation_all"] = explanation
        
        with col2:
            if st.button("Generate explanation for current filters") and filtered_insights:
                with st.spinner("Generating explanation..."):
                    # Build filtered summary
                    filtered_summary = {
                        "key_metrics": summary["key_metrics"],
                        "insights_by_severity": {
                            "critical": [i for i in filtered_insights if i["severity"] == "critical"],
                            "warning": [i for i in filtered_insights if i["severity"] == "warning"],
                            "info": [i for i in filtered_insights if i["severity"] == "info"]
                        },
                        "summary_counts": {
                            "total_insights": len(filtered_insights),
                            "critical": len([i for i in filtered_insights if i["severity"] == "critical"]),
                            "warning": len([i for i in filtered_insights if i["severity"] == "warning"]),
                            "info": len([i for i in filtered_insights if i["severity"] == "info"])
                        }
                    }
                    explanation = generate_insights_explanation(filtered_summary)
                    st.session_state["insights_explanation_filtered"] = explanation
        
        # Display explanations
        if "insights_explanation_all" in st.session_state:
            st.divider()
            st.markdown("**Explanation (all insights):**")
            st.markdown(st.session_state["insights_explanation_all"])
        
        if "insights_explanation_filtered" in st.session_state:
            st.divider()
            st.markdown("**Explanation (filtered insights):**")
            st.markdown(st.session_state["insights_explanation_filtered"])
