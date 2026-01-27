"""
Projects Page - Decision-oriented UI with clear verdicts.
Shows: "This project is bad because X — and the fix is Y."
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Optional
from ..core.project_profitability import (
    normalize_project_profitability,
    detect_drivers,
    generate_actions,
    generate_verdict_sentence,
    get_data_confidence,
    TARGET_MARGIN_PERCENT
)


def render_projects_page(data: Dict, projects_metrics: pd.DataFrame):
    """
    Render the refactored Projects page.
    
    Args:
        data: Dictionary with projects, employees, time_entries, etc.
        projects_metrics: Output from compute_project_metrics (overall, not monthly)
    """
    st.title("📁 Projects")
    
    # Initialize session state for selected project
    if "selected_project_id" not in st.session_state:
        st.session_state.selected_project_id = None
    
    # Merge with project details
    projects = data["projects"]
    projects_with_metrics = projects_metrics.merge(
        projects[["project_id", "client_name", "project_name", "status", "billing_model"]],
        on="project_id",
        how="left"
    )
    
    # Normalize all projects for selection
    project_vms = []
    for idx, row in projects_with_metrics.iterrows():
        vm = normalize_project_profitability(
            row,
            projects[projects["project_id"] == row["project_id"]].iloc[0] if len(projects[projects["project_id"] == row["project_id"]]) > 0 else None,
            None
        )
        project_vms.append(vm)
    
    # Project selector (dropdown)
    _render_project_selector(project_vms)
    
    st.divider()
    
    # Main panel
    if st.session_state.selected_project_id:
        selected_vm = [vm for vm in project_vms if vm["id"] == st.session_state.selected_project_id]
        if selected_vm:
            _render_project_decision_view(selected_vm[0], data)
    else:
        _render_empty_state()


def _render_project_selector(project_vms: List[Dict]):
    """Render project dropdown selector with search."""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create dropdown options with status emoji and margin
        dropdown_options = ["Select a project..."]
        project_map = {}
        
        for vm in project_vms:
            # Status emoji
            if vm["status"] == "Healthy":
                status_emoji = "🟢"
            elif vm["status"] == "At Risk":
                status_emoji = "🟡"
            elif vm["status"] == "Loss-making":
                status_emoji = "🔴"
            else:
                status_emoji = "⚪"
            
            # Margin display
            margin_display = f"{vm['marginPercent']:.1%}" if vm["marginPercent"] is not None else "—"
            
            # Create label
            label = f"{status_emoji} {vm['name']} ({vm['client']}) | {margin_display}"
            dropdown_options.append(label)
            project_map[label] = vm["id"]
        
        # Find current selection index
        current_index = 0
        if st.session_state.selected_project_id:
            for idx, label in enumerate(dropdown_options[1:], 1):
                if project_map[label] == st.session_state.selected_project_id:
                    current_index = idx
                    break
        
        # Dropdown selector
        selected_option = st.selectbox(
            "Select Project",
            dropdown_options,
            index=current_index,
            key="project_dropdown"
        )
        
        # Update selected project
        if selected_option != "Select a project...":
            selected_id = project_map[selected_option]
            if st.session_state.selected_project_id != selected_id:
                st.session_state.selected_project_id = selected_id
                st.rerun()
        else:
            st.session_state.selected_project_id = None
    
    with col2:
        # Quick stats
        total = len(project_vms)
        healthy = len([vm for vm in project_vms if vm["status"] == "Healthy"])
        at_risk = len([vm for vm in project_vms if vm["status"] == "At Risk"])
        loss_making = len([vm for vm in project_vms if vm["status"] == "Loss-making"])
        
        st.metric("Total Projects", total)
        st.caption(f"🟢 {healthy} | 🟡 {at_risk} | 🔴 {loss_making}")


def _render_empty_state():
    """Render empty state when no project is selected."""
    st.info("☝️ Select a project from the dropdown above to see its profitability verdict.")
    
    st.markdown("""
    ### What you'll see:
    
    - **Verdict Card**: Is the project healthy, at risk, or loss-making?
    - **Key Metrics**: Revenue, costs, margin %
    - **Cost Allocation**: Breakdown of labor and overhead costs
    - **Drivers**: Why is the project performing this way?
    - **Actions**: What to do to improve (or maintain) profitability
    
    Select a project to get started.
    """)


def _render_project_decision_view(vm: Dict, data: Dict):
    """Render main decision view for selected project."""
    
    # Detect drivers and generate actions
    drivers = detect_drivers(vm)
    actions = generate_actions(vm, drivers)
    verdict_sentence = generate_verdict_sentence(vm, drivers, actions)
    confidence_level, confidence_msg = get_data_confidence(vm)
    
    # Top row: Verdict Card
    st.markdown("### Verdict")
    
    with st.container():
        # Big headline with verdict sentence
        st.markdown(f"## {verdict_sentence}")
        
        st.divider()
        
        # Key metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Status",
                vm["status"],
                help="Healthy: margin ≥ 20% | At Risk: 0-20% | Loss-making: < 0%"
            )
        
        with col2:
            margin_display = f"{vm['marginPercent']:.1%}" if vm["marginPercent"] is not None else "N/A"
            st.metric("Margin %", margin_display)
        
        with col3:
            st.metric("Margin €", f"€{vm['marginValue']:,.0f}")
        
        with col4:
            st.metric("Revenue", f"€{vm['revenue']:,.0f}")
        
        with col5:
            st.metric("Total Cost", f"€{vm['totalCost']:,.0f}")
        
        # Data confidence
        st.caption(f"📊 Data Confidence: **{confidence_level}** — {confidence_msg}")
    
    st.divider()
    
    # Cost allocation (always shown for all projects)
    st.markdown("### Cost Allocation")
    _render_cost_breakdown(vm)
    
    st.divider()
    
    # Middle row: Drivers
    st.markdown("### Why it is this way (Drivers)")
    
    if drivers:
        for idx, driver in enumerate(drivers):
            with st.expander(f"**{idx + 1}. {driver['title']}**", expanded=(idx == 0)):
                st.markdown(f"**Evidence:** {driver['evidence']}")
                st.markdown(f"**Explanation:** {driver['explanation']}")
    else:
        st.info("No specific drivers identified. Profitability is within expected range.")
    
    st.divider()
    
    # Bottom row: Actions
    st.markdown("### Fix / Next Actions")
    
    if actions:
        for idx, action in enumerate(actions):
            with st.container():
                st.markdown(f"**{idx + 1}. {action['title']}** ({action['impact']} impact)")
                st.markdown(f"- **Why this helps:** {action['why']}")
                st.markdown(f"- **What to change:** {action['what']}")
                st.divider()
    else:
        st.info("No specific actions recommended at this time.")
    
    # Optional: AI Explanation (collapsed by default)
    with st.expander("🤖 AI Explanation (optional)", expanded=False):
        st.caption("Generated from computed metrics only. No predictions.")
        
        if st.button("Generate Explanation", key="generate_ai_explanation"):
            explanation = _generate_deterministic_explanation(vm, drivers, actions, verdict_sentence)
            st.session_state[f"ai_explanation_{vm['id']}"] = explanation
        
        if f"ai_explanation_{vm['id']}" in st.session_state:
            st.markdown(st.session_state[f"ai_explanation_{vm['id']}"])


def _render_cost_breakdown(vm: Dict):
    """Render cost breakdown visualization with detailed allocation."""
    labor = vm["costBreakdown"]["laborCost"]
    overhead = vm["costBreakdown"]["overheadCost"]
    other = vm["costBreakdown"]["otherCost"]
    total = labor + overhead + other
    revenue = vm["revenue"]
    
    if total == 0:
        st.caption("No cost data available.")
        return
    
    # Detailed allocation table
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Cost Components:**")
        
        # Create allocation table
        allocation_data = {
            "Category": ["Labor Cost", "Overhead (Allocated Expenses)", "Total Cost"],
            "Amount (€)": [f"€{labor:,.0f}", f"€{overhead:,.0f}", f"€{total:,.0f}"],
            "% of Revenue": [
                f"{(labor/revenue*100):.1f}%" if revenue > 0 else "—",
                f"{(overhead/revenue*100):.1f}%" if revenue > 0 else "—",
                f"{(total/revenue*100):.1f}%" if revenue > 0 else "—"
            ],
            "% of Total Cost": [
                f"{(labor/total*100):.1f}%",
                f"{(overhead/total*100):.1f}%",
                "100.0%"
            ]
        }
        
        st.dataframe(
            pd.DataFrame(allocation_data),
            use_container_width=True,
            hide_index=True
        )
    
    with col2:
        st.markdown("**Summary:**")
        st.metric("Total Cost", f"€{total:,.0f}")
        st.metric("Labor Share", f"{(labor/total*100):.1f}%")
        st.metric("Overhead Share", f"{(overhead/total*100):.1f}%")
    
    st.markdown("")
    
    # Visual stacked bar
    st.markdown("**Visual Breakdown:**")
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[labor],
        y=["Cost"],
        name="Labor",
        orientation='h',
        marker=dict(color='#FF6B6B'),
        text=f"€{labor:,.0f}",
        textposition='inside'
    ))
    
    fig.add_trace(go.Bar(
        x=[overhead],
        y=["Cost"],
        name="Overhead",
        orientation='h',
        marker=dict(color='#FFA726'),
        text=f"€{overhead:,.0f}",
        textposition='inside'
    ))
    
    if other > 0:
        fig.add_trace(go.Bar(
            x=[other],
            y=["Cost"],
            name="Other",
            orientation='h',
            marker=dict(color='#66BB6A'),
            text=f"€{other:,.0f}",
            textposition='inside'
        ))
    
    fig.update_layout(
        barmode='stack',
        height=120,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="EUR"),
        yaxis=dict(showticklabels=False)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _generate_deterministic_explanation(
    vm: Dict,
    drivers: List[Dict],
    actions: List[Dict],
    verdict_sentence: str
) -> str:
    """Generate deterministic AI-style explanation (no actual LLM call)."""
    
    lines = []
    lines.append(f"## Project Analysis: {vm['name']}")
    lines.append("")
    lines.append(f"**Verdict:** {verdict_sentence}")
    lines.append("")
    
    # Key numbers
    lines.append("### Key Numbers")
    lines.append(f"- **Revenue:** €{vm['revenue']:,.0f}")
    lines.append(f"- **Total Cost:** €{vm['totalCost']:,.0f}")
    labor = vm["costBreakdown"]["laborCost"]
    overhead = vm["costBreakdown"]["overheadCost"]
    lines.append(f"  - Labor: €{labor:,.0f} ({labor/(vm['totalCost'] or 1):.1%})")
    lines.append(f"  - Overhead: €{overhead:,.0f} ({overhead/(vm['totalCost'] or 1):.1%})")
    
    margin_display = f"{vm['marginPercent']:.1%}" if vm["marginPercent"] is not None else "N/A"
    lines.append(f"- **Margin:** €{vm['marginValue']:,.0f} ({margin_display})")
    
    if vm["hours"]["billable"] > 0:
        lines.append(f"- **Billable Hours:** {vm['hours']['billable']:.1f}")
    if vm["effectiveHourlyRate"] is not None:
        lines.append(f"- **Effective Rate:** €{vm['effectiveHourlyRate']:.2f}/hr")
    
    lines.append("")
    
    # Drivers
    if drivers:
        lines.append("### Why This Is Happening")
        for idx, driver in enumerate(drivers):
            lines.append(f"{idx + 1}. **{driver['title']}**: {driver['explanation']}")
            lines.append(f"   - {driver['evidence']}")
        lines.append("")
    
    # Actions
    if actions:
        lines.append("### Recommended Actions")
        for idx, action in enumerate(actions):
            lines.append(f"{idx + 1}. **{action['title']}** ({action['impact']} impact)")
            lines.append(f"   - Why: {action['why']}")
            lines.append(f"   - What: {action['what']}")
        lines.append("")
    
    lines.append("---")
    lines.append("*This explanation was generated from precomputed metrics. No predictions were made.*")
    
    return "\n".join(lines)
