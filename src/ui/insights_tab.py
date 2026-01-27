"""
Insights Chat UI - Chat-first experience with deterministic answers.
Ask questions about projects, people, company, invoices, cashflow.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List
from datetime import datetime
from ..core.insights_engine import generate_insights
from ..core.insights_chat import parse_intent, retrieve_context, build_deterministic_answer
from ..ai.summary_builder import build_chat_summary, build_insights_summary
from ..ai.local_llm import rewrite_answer, generate_insights_explanation


def render_insights_tab(
    metrics_outputs: Dict,
    data: Dict,
    starting_cash: float
) -> None:
    """
    Render the Insights tab with chat-first UX.
    
    Args:
        metrics_outputs: Dictionary with metrics engine outputs
        data: Raw data dict
        starting_cash: Starting cash balance
    """
    # Initialize session state
    _initialize_session_state()
    
    # Generate insights once
    if "insights_list" not in st.session_state:
        with st.spinner("Analyzing financial data..."):
            st.session_state.insights_list = generate_insights(
                projects_metrics=metrics_outputs.get("projects_metrics"),
                projects_metrics_monthly=metrics_outputs.get("projects_metrics_monthly"),
                employee_utilization=metrics_outputs.get("employee_utilization"),
                income_statement_monthly=metrics_outputs.get("income_statement_monthly"),
                cashflow_monthly=metrics_outputs.get("cashflow_monthly"),
                invoices=data.get("invoices")
            )
    
    insights_list = st.session_state.insights_list
    
    # Header
    st.title("💬 Ask Your Data")
    st.caption("Chat with your financial metrics - all answers grounded in deterministic data (no predictions).")
    
    # AI phrasing toggle
    use_ai_phrasing = st.checkbox(
        "Use AI phrasing (optional)",
        value=st.session_state.get("use_ai_phrasing", False),
        help="Let AI rephrase answers (numbers stay the same)",
        key="ai_phrasing_toggle"
    )
    st.session_state.use_ai_phrasing = use_ai_phrasing
    
    st.divider()
    
    # Chat interface
    _render_chat_interface(metrics_outputs, insights_list)
    
    st.divider()
    
    # Browse mode (optional, collapsed)
    _render_browse_mode(insights_list, metrics_outputs, starting_cash)


def _initialize_session_state():
    """Initialize session state for chat."""
    if "insights_chat" not in st.session_state:
        # Add welcome message
        st.session_state.insights_chat = [
            {
                "role": "assistant",
                "content": "👋 Ask about a project (e.g., 'Why is P009 unprofitable?'), a person (e.g., 'Show E017 utilization'), or company metrics (e.g., 'Why did revenue drop?').",
                "meta": {}
            }
        ]
    if "use_ai_phrasing" not in st.session_state:
        st.session_state.use_ai_phrasing = False


def _render_chat_interface(metrics_outputs: Dict, insights_list: List[Dict]):
    """Render chat interface with input and history."""
    
    # Example questions (chips)
    st.markdown("**Quick questions:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    example_questions = [
        "Why is P009 unprofitable?",
        "Which projects are dragging margins?",
        "Who is underutilized?",
        "Which invoices are overdue?",
        "Why did revenue drop?"
    ]
    
    for idx, (col, question) in enumerate(zip([col1, col2, col3, col4, col5], example_questions)):
        with col:
            if st.button(question, key=f"example_{idx}", use_container_width=True):
                _handle_user_query(question, metrics_outputs, insights_list)
                st.rerun()
    
    st.divider()
    
    # Chat history
    for msg_idx, msg in enumerate(st.session_state.insights_chat):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Show sources for assistant messages
            if msg["role"] == "assistant" and msg.get("meta", {}).get("facts_used"):
                with st.expander("📊 Sources (deterministic)", expanded=False):
                    st.markdown("**Facts used:**")
                    for fact in msg["meta"]["facts_used"]:
                        st.markdown(f"- {fact}")
                    
                    if msg["meta"].get("matched_insights"):
                        st.markdown("")
                        st.markdown("**Matched insights:**")
                        for insight in msg["meta"]["matched_insights"]:
                            st.markdown(f"- {insight}")
            
            # Show follow-ups
            if msg["role"] == "assistant" and msg.get("meta", {}).get("followups"):
                st.markdown("")
                st.markdown("**Suggested follow-ups:**")
                followups = msg["meta"]["followups"]
                for followup_idx, followup in enumerate(followups[:4]):
                    if st.button(followup, key=f"followup_msg{msg_idx}_opt{followup_idx}"):
                        _handle_user_query(followup, metrics_outputs, insights_list)
                        st.rerun()
    
    # Chat input
    user_input = st.chat_input("Ask a question about your data...")
    if user_input:
        _handle_user_query(user_input, metrics_outputs, insights_list)
        st.rerun()


def _handle_user_query(query: str, metrics_outputs: Dict, insights_list: List[Dict]):
    """Handle user query and generate response."""
    # Add user message
    st.session_state.insights_chat.append({
        "role": "user",
        "content": query,
        "meta": {}
    })
    
    # Parse intent
    intent = parse_intent(query)
    
    # Retrieve context
    context = retrieve_context(intent, metrics_outputs, insights_list)
    
    # Build deterministic answer
    deterministic_answer = build_deterministic_answer(query, context, intent)
    
    # Optional AI rewriting
    if st.session_state.use_ai_phrasing:
        chat_summary = build_chat_summary(query, deterministic_answer)
        final_text = rewrite_answer(chat_summary)
    else:
        final_text = deterministic_answer["final_answer"]
    
    # Add assistant message
    st.session_state.insights_chat.append({
        "role": "assistant",
        "content": final_text,
        "meta": {
            "facts_used": deterministic_answer["facts_used"],
            "matched_insights": deterministic_answer["matched_insights"],
            "followups": deterministic_answer["followups"],
            "intent": intent
        }
    })


def _render_browse_mode(insights_list: List[Dict], metrics_outputs: Dict, starting_cash: float):
    """Render optional browse mode (collapsed by default)."""
    with st.expander("📋 Browse Insights (optional)", expanded=False):
        if not insights_list:
            st.info("No insights found. Your metrics look good!")
            return
        
        # Summary counts
        counts = {
            "total": len(insights_list),
            "critical": len([i for i in insights_list if i["severity"] == "critical"]),
            "warning": len([i for i in insights_list if i["severity"] == "warning"]),
            "info": len([i for i in insights_list if i["severity"] == "info"])
        }
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", counts["total"])
        with col2:
            st.metric("🔴 Critical", counts["critical"])
        with col3:
            st.metric("🟡 Warnings", counts["warning"])
        with col4:
            st.metric("🔵 Info", counts["info"])
        
        st.divider()
        
        # Top 10 insights by severity
        st.markdown("**Top 10 Insights by Severity:**")
        
        sorted_insights = sorted(
            insights_list,
            key=lambda x: {"critical": 0, "warning": 1, "info": 2}.get(x["severity"], 3)
        )[:10]
        
        for insight in sorted_insights:
            severity_badge = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(insight["severity"], "⚪")
            
            with st.container():
                st.markdown(f"**{severity_badge} {insight['message']}**")
                st.caption(f"{insight['entity']} | {insight['type']}")
                
                with st.expander("Details", expanded=False):
                    st.markdown("**Drivers:**")
                    for driver in insight.get("drivers", []):
                        st.markdown(f"- {driver}")
                
                st.divider()
        
        # Category tabs
        st.markdown("**Browse by Category:**")
        tab1, tab2, tab3, tab4 = st.tabs(["Company", "Projects", "People", "Cash & Invoices"])
        
        with tab1:
            _render_category_list(
                [i for i in insights_list if i["entity"] == "company"],
                "Company"
            )
        
        with tab2:
            _render_category_list(
                [i for i in insights_list if i["type"].startswith("project")],
                "Projects"
            )
        
        with tab3:
            _render_category_list(
                [i for i in insights_list if i["type"].startswith("employee")],
                "People"
            )
        
        with tab4:
            cash_insights = [i for i in insights_list if i["type"].startswith("cashflow") or i["type"].startswith("invoices")]
            _render_category_list(cash_insights, "Cash & Invoices")
        
        st.divider()
        
        # AI explanation (optional)
        with st.expander("🤖 AI Explanation (optional)", expanded=False):
            st.caption("Generated from pre-calculated metrics. No predictions. No new numbers.")
            
            if st.button("Generate AI Explanation for All Insights"):
                key_metrics = _extract_key_metrics(metrics_outputs, starting_cash)
                summary = build_insights_summary(insights_list, key_metrics)
                
                with st.spinner("Generating explanation..."):
                    explanation = generate_insights_explanation(summary)
                    st.session_state["insights_explanation_all"] = explanation
            
            if "insights_explanation_all" in st.session_state:
                st.divider()
                st.markdown(st.session_state["insights_explanation_all"])


def _render_category_list(insights: List[Dict], category_name: str):
    """Render insights for a specific category."""
    if not insights:
        st.info(f"No {category_name} insights found.")
        return
    
    for insight in insights[:5]:
        severity_badge = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(insight["severity"], "⚪")
        st.markdown(f"{severity_badge} **{insight['message']}**")
        st.caption(f"{insight['entity']}")
    
    if len(insights) > 5:
        st.caption(f"... and {len(insights) - 5} more")


def _extract_key_metrics(metrics_outputs: Dict, starting_cash: float) -> Dict:
    """Extract key metrics for AI summary."""
    income_monthly = metrics_outputs.get("income_statement_monthly")
    cashflow_monthly = metrics_outputs.get("cashflow_monthly")
    
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
