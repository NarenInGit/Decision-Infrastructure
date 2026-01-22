"""
Risk & Forecasts (Experimental) tab for Streamlit.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Optional

from ..features.build_features import FeatureBuilder
from ..models.registry import load_model_if_exists, get_model_path
from ..models.torch.train import train_model


def render_risk_tab(metrics_outputs: Dict):
    """
    Render the Risk & Forecasts (Experimental) tab.
    
    Args:
        metrics_outputs: Dictionary with keys:
            - income_statement_monthly: DataFrame
            - cashflow_monthly: DataFrame
            - projects_metrics: DataFrame (from compute_project_metrics)
            - people_utilization: DataFrame (from compute_employee_utilization)
            - time_entries: DataFrame
            - invoices: DataFrame
    """
    st.title("⚠️ Risk & Forecasts (Experimental)")
    
    # Warning banner
    st.warning("**Experimental — directional signals only. Not a substitute for deterministic metrics.**")
    
    # Check if we have required metrics
    required_keys = ["projects_metrics", "time_entries", "invoices"]
    missing_keys = [key for key in required_keys if key not in metrics_outputs]
    
    if missing_keys:
        st.error(f"Missing required metrics: {', '.join(missing_keys)}. Please visit other tabs first.")
        return
    
    # Build features
    builder = FeatureBuilder()
    
    # Try to load existing features, otherwise build them
    features_df = builder.load_features()
    
    if features_df is None:
        st.info("Building features from metrics outputs...")
        try:
            # Build features from metrics outputs
            features_df = builder.build_project_monthly_features(
                income_statement_monthly=metrics_outputs.get("income_statement_monthly", pd.DataFrame()),
                cashflow_monthly=metrics_outputs.get("cashflow_monthly", pd.DataFrame()),
                projects_metrics=metrics_outputs["projects_metrics"],
                people_utilization=metrics_outputs.get("people_utilization", pd.DataFrame()),
                time_entries=metrics_outputs["time_entries"],
                invoices=metrics_outputs["invoices"],
                expenses=metrics_outputs.get("expenses", pd.DataFrame())
            )
            
            # Save features
            builder.save_features(features_df)
            st.success("✅ Features built and saved.")
        except Exception as e:
            st.error(f"Error building features: {str(e)}")
            return
    
    # Try to load model
    model = load_model_if_exists()
    
    if model is None:
        st.info("**No predictive model trained yet. Using deterministic metrics only.**")
        
        # Show deterministic risk indicators
        st.subheader("Deterministic Risk Indicators")
        
        if "month" in metrics_outputs["projects_metrics"].columns:
            # Get latest month per project
            projects_monthly = metrics_outputs["projects_metrics"].copy()
            projects_monthly["month_dt"] = pd.to_datetime(projects_monthly["month"].astype(str))
            latest_idx = projects_monthly.groupby("project_id")["month_dt"].idxmax()
            # Filter out NaN values and ensure indices are valid
            latest_idx = latest_idx.dropna()
            # Convert to list and filter to only valid indices
            valid_indices = [idx for idx in latest_idx.values if idx in projects_monthly.index]
            if len(valid_indices) > 0:
                latest_projects = projects_monthly.loc[valid_indices]
            else:
                latest_projects = pd.DataFrame()
            
            # Show projects with negative or low margin
            if len(latest_projects) > 0:
                risky_projects = latest_projects[
                    (latest_projects["gross_margin_pct"] < 0) | 
                    (latest_projects["gross_margin_pct"] < 0.1)
                ][["project_id", "month", "gross_margin_pct", "revenue", "gross_profit"]]
            else:
                risky_projects = pd.DataFrame()
            
            if len(risky_projects) > 0:
                st.write("**Projects with negative or low margin (<10%):**")
                st.dataframe(
                    risky_projects.style.format({
                        "gross_margin_pct": "{:.1%}",
                        "revenue": "€{:,.0f}",
                        "gross_profit": "€{:,.0f}"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No projects with negative or low margin detected.")
        else:
            # Overall project metrics
            projects = metrics_outputs["projects_metrics"]
            risky_projects = projects[
                (projects["gross_margin_pct"] < 0) | 
                (projects["gross_margin_pct"] < 0.1)
            ][["project_id", "gross_margin_pct", "revenue", "gross_profit"]]
            
            if len(risky_projects) > 0:
                st.write("**Projects with negative or low margin (<10%):**")
                st.dataframe(
                    risky_projects.style.format({
                        "gross_margin_pct": "{:.1%}",
                        "revenue": "€{:,.0f}",
                        "gross_profit": "€{:,.0f}"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No projects with negative or low margin detected.")
        
        # Train model button
        st.divider()
        st.subheader("Train Model")
        
        if st.button("Train / Re-train Model", type="primary"):
            with st.spinner("Training model... This may take a moment."):
                try:
                    # Ensure features are built
                    if features_df is None:
                        features_df = builder.build_project_monthly_features(
                            income_statement_monthly=metrics_outputs.get("income_statement_monthly", pd.DataFrame()),
                            cashflow_monthly=metrics_outputs.get("cashflow_monthly", pd.DataFrame()),
                            projects_metrics=metrics_outputs["projects_metrics"],
                            people_utilization=metrics_outputs.get("people_utilization", pd.DataFrame()),
                            time_entries=metrics_outputs["time_entries"],
                            invoices=metrics_outputs["invoices"],
                            expenses=metrics_outputs.get("expenses", pd.DataFrame())
                        )
                        builder.save_features(features_df)
                    
                    # Train model
                    metrics = train_model(features_df, epochs=50)
                    
                    st.success("✅ Model trained successfully!")
                    st.json({
                        "Final Validation Loss": f"{metrics['final_val_loss']:.4f}",
                        "Final Validation Accuracy": f"{metrics['final_val_accuracy']:.2%}",
                        "Model Path": metrics["model_path"]
                    })
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error training model: {str(e)}")
                    st.exception(e)
    
    else:
        # Model exists - show predictions
        st.success("✅ Predictive model loaded.")
        
        try:
            # Get predictions for latest month of each project
            predictions_df = model.predict_latest(features_df)
            
            # Merge with project details if available
            if "month" in metrics_outputs["projects_metrics"].columns:
                projects_monthly = metrics_outputs["projects_metrics"].copy()
                projects_monthly["month_dt"] = pd.to_datetime(projects_monthly["month"].astype(str))
                latest_idx = projects_monthly.groupby("project_id")["month_dt"].idxmax()
                # Filter out NaN values and ensure indices are valid
                latest_idx = latest_idx.dropna()
                # Convert to list and filter to only valid indices
                valid_indices = [idx for idx in latest_idx.values if idx in projects_monthly.index]
                if len(valid_indices) > 0:
                    latest_projects = projects_monthly.loc[valid_indices]
                    # Merge predictions
                    display_df = latest_projects.merge(
                        predictions_df[["project_id", "risk_probability"]],
                        on="project_id",
                        how="left"
                    )
                else:
                    # Fallback: use predictions_df directly
                    display_df = predictions_df
            else:
                display_df = predictions_df
            
            # Select columns for display
            display_cols = ["project_id", "month", "risk_probability", "gross_margin_pct", "revenue"]
            available_cols = [col for col in display_cols if col in display_df.columns]
            
            # Highlight risky projects
            st.subheader("Project Risk Predictions")
            st.write("**Risk probability**: Probability that project will have negative margin next month")
            
            # Format and display
            display_df = display_df[available_cols].copy()
            
            # Highlight rows with risk > 0.6
            def highlight_risk(row):
                if "risk_probability" in row and row["risk_probability"] > 0.6:
                    return ['background-color: #ffcccc'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                display_df.style.format({
                    "risk_probability": "{:.1%}",
                    "gross_margin_pct": "{:.1%}",
                    "revenue": "€{:,.0f}"
                }).apply(highlight_risk, axis=1),
                use_container_width=True
            )
            
            # Summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                high_risk_count = len(display_df[display_df["risk_probability"] > 0.6])
                st.metric("High Risk Projects (>60%)", high_risk_count)
            with col2:
                medium_risk_count = len(display_df[
                    (display_df["risk_probability"] > 0.3) & 
                    (display_df["risk_probability"] <= 0.6)
                ])
                st.metric("Medium Risk Projects (30-60%)", medium_risk_count)
            with col3:
                low_risk_count = len(display_df[display_df["risk_probability"] <= 0.3])
                st.metric("Low Risk Projects (<30%)", low_risk_count)
            
            # Retrain button
            st.divider()
            if st.button("Re-train Model", type="secondary"):
                with st.spinner("Training model... This may take a moment."):
                    try:
                        metrics = train_model(features_df, epochs=50)
                        st.success("✅ Model retrained successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error training model: {str(e)}")
        
        except Exception as e:
            st.error(f"Error making predictions: {str(e)}")
            st.exception(e)
            st.info("Falling back to deterministic metrics...")
            
            # Show deterministic indicators
            st.subheader("Deterministic Risk Indicators")
            projects = metrics_outputs["projects_metrics"]
            risky_projects = projects[
                (projects["gross_margin_pct"] < 0) | 
                (projects["gross_margin_pct"] < 0.1)
            ][["project_id", "gross_margin_pct", "revenue", "gross_profit"]]
            
            if len(risky_projects) > 0:
                st.dataframe(
                    risky_projects.style.format({
                        "gross_margin_pct": "{:.1%}",
                        "revenue": "€{:,.0f}",
                        "gross_profit": "€{:,.0f}"
                    }),
                    use_container_width=True
                )
