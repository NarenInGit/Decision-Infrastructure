"""
Weekly Brief UI - Top issues and attention focus.
Helps founders answer: "What should I look at first?"
"""

import streamlit as st
from typing import Dict, List
from ..core.brief_builder import build_attention_brief, generate_shareable_brief
from ..core.insights_engine import generate_insights


def render_briefs_tab(
    metrics_outputs: Dict,
    data: Dict,
    starting_cash: float
) -> None:
    """
    Render the Weekly Brief tab.
    
    Shows:
    - Top 3 critical issues
    - Top 3 warnings
    - Key changes (if available)
    - Shareable brief generator
    """
    st.caption("Focus on what matters most - ranked by severity and impact")
    
    cache_key = metrics_outputs.get("cache_key", "default")
    if st.session_state.get("insights_cache_key") != cache_key:
        with st.spinner("Analyzing financial data..."):
            st.session_state.insights_list = generate_insights(
                projects_metrics=metrics_outputs.get("projects_metrics"),
                projects_metrics_monthly=metrics_outputs.get("projects_metrics_monthly"),
                employee_utilization=metrics_outputs.get("employee_utilization"),
                income_statement_monthly=metrics_outputs.get("income_statement_monthly"),
                cashflow_monthly=metrics_outputs.get("cashflow_monthly"),
                invoices=data.get("invoices"),
                as_of_date=metrics_outputs.get("filters", {}).get("as_of_date"),
            )
            st.session_state.insights_cache_key = cache_key
    
    insights_list = st.session_state.insights_list
    
    # Build brief
    brief = build_attention_brief(metrics_outputs, insights_list)
    
    # Summary stats
    st.divider()
    _render_summary_stats(brief)
    
    st.divider()
    
    # Top issues
    col1, col2 = st.columns(2)
    
    with col1:
        _render_critical_issues(brief)
    
    with col2:
        _render_warnings(brief)
    
    st.divider()
    
    # Key changes
    if brief["key_changes"]:
        _render_key_changes(brief)
        st.divider()
    
    # Shareable brief
    _render_shareable_brief(brief)


def _render_summary_stats(brief: Dict):
    """Render summary statistics."""
    stats = brief["summary_stats"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Insights", stats["total_insights"])
    
    with col2:
        st.metric("🔴 Critical", stats["critical_count"])
    
    with col3:
        st.metric("🟡 Warnings", stats["warning_count"])
    
    with col4:
        st.metric("🔵 Info", stats["info_count"])
    
    # Affected areas
    st.markdown("**Affected Areas:**")
    affected = stats["affected_areas"]
    
    areas_col1, areas_col2, areas_col3 = st.columns(3)
    with areas_col1:
        st.caption(f"💰 Profitability: {affected['profitability']}")
    with areas_col2:
        st.caption(f"💵 Cash: {affected['cash']}")
    with areas_col3:
        st.caption(f"👥 Utilization: {affected['utilization']}")


def _render_critical_issues(brief: Dict):
    """Render top 3 critical issues."""
    st.markdown("### 🔴 Top Critical Issues")
    
    if not brief["top_critical"]:
        st.success("No critical issues detected!")
        return
    
    for idx, issue in enumerate(brief["top_critical"], 1):
        with st.container():
            st.markdown(f"**{idx}. {issue['message']}**")
            st.caption(f"Entity: {issue['entity']} | Type: {issue['type']}")
            
            # Show first driver
            if issue.get("drivers"):
                st.caption(f"💡 {issue['drivers'][0]}")
            
            # "Ask about this" button
            query = _generate_query_for_issue(issue)
            if st.button(f"Ask about this", key=f"critical_{idx}"):
                # Switch to Insights tab with pre-filled query
                st.session_state["prefill_query"] = query
                st.session_state["switch_to_insights"] = True
                st.info(f"💡 Switch to 'Ask Your Data' tab and ask: '{query}'")
            
            st.divider()


def _render_warnings(brief: Dict):
    """Render top 3 warnings."""
    st.markdown("### 🟡 Top Warnings")
    
    if not brief["top_warnings"]:
        st.success("No warnings!")
        return
    
    for idx, issue in enumerate(brief["top_warnings"], 1):
        with st.container():
            st.markdown(f"**{idx}. {issue['message']}**")
            st.caption(f"Entity: {issue['entity']} | Type: {issue['type']}")
            
            # Show first driver
            if issue.get("drivers"):
                st.caption(f"💡 {issue['drivers'][0]}")
            
            # "Ask about this" button
            query = _generate_query_for_issue(issue)
            if st.button(f"Ask about this", key=f"warning_{idx}"):
                st.session_state["prefill_query"] = query
                st.session_state["switch_to_insights"] = True
                st.info(f"💡 Switch to 'Ask Your Data' tab and ask: '{query}'")
            
            st.divider()


def _render_key_changes(brief: Dict):
    """Render key changes detected."""
    st.markdown("### 📈 Key Changes")
    
    for change in brief["key_changes"]:
        affects_str = ", ".join(change.get("affects", []))
        st.markdown(f"- **{change['message']}**")
        st.caption(f"Affects: {affects_str}")


def _render_shareable_brief(brief: Dict):
    """Render shareable brief generator."""
    st.markdown("### 📤 Generate Shareable Brief")
    st.caption("Create copy-ready summaries for co-founders, clients, or investors")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📱 Slack Update", use_container_width=True):
            text = generate_shareable_brief(brief, format="slack")
            st.session_state["shareable_brief"] = text
            st.session_state["brief_format"] = "Slack"
    
    with col2:
        if st.button("📧 Email Memo", use_container_width=True):
            text = generate_shareable_brief(brief, format="email")
            st.session_state["shareable_brief"] = text
            st.session_state["brief_format"] = "Email"
    
    with col3:
        if st.button("📊 Investor Note", use_container_width=True):
            text = generate_shareable_brief(brief, format="investor")
            st.session_state["shareable_brief"] = text
            st.session_state["brief_format"] = "Investor"
    
    # Display generated brief
    if "shareable_brief" in st.session_state:
        st.divider()
        st.markdown(f"**{st.session_state['brief_format']} Brief:**")
        
        with st.container():
            st.code(st.session_state["shareable_brief"], language="markdown")
        
        st.caption("_Generated from computed data; no predictions. Copy and paste as needed._")
        
        # Copy button (visual only - user still needs to manually copy)
        if st.button("📋 Copy to Clipboard (manual)"):
            st.info("Select the text above and copy it manually (Cmd+C / Ctrl+C)")


def _generate_query_for_issue(issue: Dict) -> str:
    """
    Generate a natural language query for an issue.
    Used for "Ask about this" buttons.
    """
    entity = issue.get("entity", "")
    issue_type = issue.get("type", "")
    
    if issue_type.startswith("project"):
        return f"Why is {entity} unprofitable?"
    elif issue_type.startswith("employee"):
        return f"Show {entity} utilization details"
    elif issue_type.startswith("cashflow"):
        return "Why is cash tight?"
    elif issue_type.startswith("invoices"):
        return "Which invoices are overdue?"
    else:
        return f"Tell me about {entity}"
