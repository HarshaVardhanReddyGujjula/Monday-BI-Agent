import streamlit as st
import pandas as pd
import datetime
import io
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Tuple, Optional

from bi_engine import BIEngine
from ai_assistant import BusinessAssistant
import database
from config import logger


def init_page_styles() -> None:
    """Applies modern corporate styling with high contrast and readable cards."""
    st.markdown("""
    <style>
        .metric-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #3b82f6;
            padding: 1.1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            margin-bottom: 0.8rem;
        }
        .metric-val {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.2rem;
        }
        .metric-lbl {
            font-size: 0.78rem;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        .metric-sub {
            font-size: 0.75rem;
            color: #10b981;
            font-weight: 500;
            margin-top: 0.2rem;
        }
        .section-header {
            font-size: 1.25rem;
            font-weight: 700;
            color: #1e293b;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 0.4rem;
            margin-top: 1.2rem;
            margin-bottom: 1.0rem;
        }
    </style>
    """, unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Monday BI Agent | Sales & Business Intelligence",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    init_page_styles()

    # ---------------------------------------------------------
    # SIDEBAR CONTROLS & SLICERS
    # ---------------------------------------------------------
    st.sidebar.title("📊 Monday BI Agent")
    st.sidebar.caption("Sales Pipeline & Business Intelligence Platform")
    st.sidebar.markdown("---")

    # Data Source Selection
    st.sidebar.markdown("### 🗄️ Data Ingestion Mode")
    data_source_mode = st.sidebar.radio(
        "Select Data Source:",
        ["Local SQLite Database (Demo/Offline)", "Live Monday.com API", "Upload Custom Excel/CSV"],
        index=0
    )

    engine_source = "auto"
    custom_uploaded_deals = None
    custom_uploaded_wo = None

    if data_source_mode == "Live Monday.com API":
        engine_source = "monday"
        st.sidebar.info("Using live credentials from `.env` file.")
    elif data_source_mode == "Upload Custom Excel/CSV":
        engine_source = "custom"
        uploaded_file = st.sidebar.file_uploader("Upload Sales / Deals File:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    custom_uploaded_deals = pd.read_csv(uploaded_file)
                else:
                    custom_uploaded_deals = pd.read_excel(uploaded_file)
                st.sidebar.success(f"Loaded {len(custom_uploaded_deals)} records!")
            except Exception as e:
                st.sidebar.error(f"Error reading file: {e}")

    # Initialize Engine
    engine = BIEngine(data_source=engine_source)
    try:
        engine.load_data()
        if custom_uploaded_deals is not None and not custom_uploaded_deals.empty:
            engine.deals_df = engine.processor.clean_dataframe(custom_uploaded_deals)
            engine.deals_df = engine.processor.normalize_column_names(engine.deals_df)
            engine.deals_df = engine.processor.convert_numeric_columns(engine.deals_df)
            engine.deals_df = engine.processor.convert_date_columns(engine.deals_df)
            engine.deals_df, _ = engine.processor.apply_dax_business_measures(engine.deals_df, engine.work_orders_df)
            engine.filtered_deals_df = engine.deals_df.copy()
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        return

    # Extract distinct dimensions for dynamic slicers
    deals_raw = engine.deals_df
    wo_raw = engine.work_orders_df

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Dynamic Slicers & Filters")

    # 1. Date Range Filter
    selected_date_range = None
    if "created_date" in deals_raw.columns and pd.api.types.is_datetime64_any_dtype(deals_raw["created_date"]):
        min_date = deals_raw["created_date"].min().date() if pd.notna(deals_raw["created_date"].min()) else datetime.date(2025, 1, 1)
        max_date = deals_raw["created_date"].max().date() if pd.notna(deals_raw["created_date"].max()) else datetime.date(2026, 12, 31)
        selected_date_range = st.sidebar.date_input(
            "Date Range Filter:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

    # 2. Deal Status Slicer
    available_statuses = sorted(deals_raw["deal_status"].dropna().unique().tolist()) if "deal_status" in deals_raw.columns else []
    selected_statuses = st.sidebar.multiselect("Deal Stage / Status:", available_statuses, default=available_statuses)

    # 3. Sales Rep / Owner Slicer
    available_owners = sorted(deals_raw["owner"].dropna().unique().tolist()) if "owner" in deals_raw.columns else []
    selected_owners = st.sidebar.multiselect("Deal Owner / Rep:", available_owners, default=available_owners)

    # 4. Client Tier Slicer
    available_tiers = sorted(deals_raw["client_tier"].dropna().unique().tolist()) if "client_tier" in deals_raw.columns else []
    selected_tiers = st.sidebar.multiselect("Client Tier:", available_tiers, default=available_tiers)

    # Apply slicers to Engine
    engine.apply_filters(
        date_range=selected_date_range if isinstance(selected_date_range, (list, tuple)) and len(selected_date_range) == 2 else None,
        deal_statuses=selected_statuses if selected_statuses else None,
        owners=selected_owners if selected_owners else None,
        client_tiers=selected_tiers if selected_tiers else None
    )

    # Compute Summaries
    summary = engine.calculate_executive_summary()
    deals_kpis = summary["Deals"]
    wo_kpis = summary["Work_Orders"]
    financial = summary["Financial"]
    operations = summary["Operations"]

    # Refresh Button
    if st.sidebar.button("🔄 Reset Slicers & Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # ---------------------------------------------------------
    # MAIN DASHBOARD HEADER & TABS
    # ---------------------------------------------------------
    st.title("📊 Business Intelligence & Sales Analytics Platform")
    st.markdown(
        "Executive KPI tracking, multi-dimensional sales analysis, cash-flow leakage audits, and AI decision support."
    )

    tabs = st.tabs([
        "📈 Executive KPI Dashboard",
        "💼 Sales Performance & Trends",
        "👥 Customer & Category Insights",
        "💰 Financial & Operations Health",
        "🤖 AI Business Assistant",
        "🗄️ SQL Data Explorer & Export"
    ])

    # =========================================================
    # TAB 1: EXECUTIVE KPI DASHBOARD
    # =========================================================
    with tabs[0]:
        st.markdown("<div class='section-header'>Executive KPI Scorecards</div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Total Pipeline Value</div>
                <div class="metric-val">₹{deals_kpis.get('total_pipeline_value', 0.0):,.0f}</div>
                <div class="metric-sub">{deals_kpis.get('total_deals', 0)} Active Opportunities</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Weighted Pipeline</div>
                <div class="metric-val">₹{deals_kpis.get('weighted_pipeline_value', 0.0):,.0f}</div>
                <div class="metric-sub">Probability-Adjusted Value</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Contracted Revenue</div>
                <div class="metric-val">₹{financial.get('revenue', 0.0):,.0f}</div>
                <div class="metric-sub">{wo_kpis.get('total_work_orders', 0)} Executing Work Orders</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Collected Cash</div>
                <div class="metric-val">₹{financial.get('collected', 0.0):,.0f}</div>
                <div class="metric-sub">{wo_kpis.get('collection_efficiency', 0.0):.1f}% Efficiency Rate</div>
            </div>
            """, unsafe_allow_html=True)

        with c5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-lbl">Pipeline Win Rate</div>
                <div class="metric-val">{deals_kpis.get('win_rate_pct', 0.0):.1f}%</div>
                <div class="metric-sub">{deals_kpis.get('high_probability_deals', 0)} High-Confidence Deals</div>
            </div>
            """, unsafe_allow_html=True)

        # Overview Visuals
        row1_col1, row1_col2 = st.columns([3, 2])

        with row1_col1:
            st.markdown("### Pipeline Distribution by Stage")
            pipe_status = deals_kpis.get("pipeline_by_status", {})
            if pipe_status:
                df_st = pd.DataFrame(list(pipe_status.items()), columns=["Stage", "Count"])
                fig_stage = px.bar(
                    df_st, x="Stage", y="Count", color="Count",
                    color_continuous_scale="Blues", template="plotly_white",
                    text="Count"
                )
                fig_stage.update_layout(coloraxis_showscale=False, height=320, margin=dict(t=20, b=20, l=20, r=20))
                st.plotly_chart(fig_stage, use_container_width=True)
            else:
                st.info("No deal status data matches current slicers.")

        with row1_col2:
            st.markdown("### Cash Flow & Efficiency Rates")
            eff = wo_kpis.get("collection_efficiency", 0.0)
            comp = operations.get("completion_rate", 0.0)

            fig_gauges = go.Figure()
            fig_gauges.add_trace(go.Indicator(
                mode="gauge+number",
                value=eff,
                title={"text": "Collection Efficiency (%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#10b981"},
                    "steps": [
                        {"range": [0, 50], "color": "#fee2e2"},
                        {"range": [50, 80], "color": "#fef3c7"},
                        {"range": [80, 100], "color": "#d1fae5"}
                    ]
                },
                domain={"row": 0, "column": 0}
            ))
            fig_gauges.update_layout(grid={"rows": 1, "columns": 1}, height=300, margin=dict(t=40, b=10, l=20, r=20))
            st.plotly_chart(fig_gauges, use_container_width=True)

    # =========================================================
    # TAB 2: SALES PERFORMANCE & REVENUE TRENDS
    # =========================================================
    with tabs[1]:
        st.markdown("<div class='section-header'>Historical Revenue Trends & Pipeline Progression</div>", unsafe_allow_html=True)

        trends = deals_kpis.get("monthly_trends", {})
        if trends:
            months = list(trends.keys())
            revs = [trends[m]["revenue"] for m in months]
            counts = [trends[m]["count"] for m in months]

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=months, y=revs, name="Pipeline Revenue (₹)",
                marker_color="#3b82f6", yaxis="y"
            ))
            fig_trend.add_trace(go.Scatter(
                x=months, y=counts, name="Deal Count",
                mode="lines+markers", line=dict(color="#f59e0b", width=3), yaxis="y2"
            ))
            fig_trend.update_layout(
                template="plotly_white",
                title="Revenue Pipeline Trends by Creation Month",
                yaxis=dict(title="Pipeline Value (₹)"),
                yaxis2=dict(title="Number of Deals", overlaying="y", side="right"),
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No date-based monthly trend data available.")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("### Sales Rep Performance")
            owners = deals_kpis.get("deals_by_owner", {})
            if owners:
                df_owners = pd.DataFrame(list(owners.items()), columns=["Owner", "Deals Count"])
                fig_rep = px.bar(
                    df_owners, x="Deals Count", y="Owner", orientation="h",
                    color="Deals Count", color_continuous_scale="Purples", template="plotly_white"
                )
                fig_rep.update_layout(coloraxis_showscale=False, height=300)
                st.plotly_chart(fig_rep, use_container_width=True)

        with col_s2:
            st.markdown("### High-Value Opportunities (Decision Support)")
            if not engine.filtered_deals_df.empty:
                display_cols = [c for c in ["deal_name", "client_name", "deal_value", "deal_status", "probability", "owner"] if c in engine.filtered_deals_df.columns]
                top_deals = engine.filtered_deals_df[display_cols].sort_values("deal_value", ascending=False).head(5)
                st.dataframe(top_deals, use_container_width=True, hide_index=True)

    # =========================================================
    # TAB 3: CUSTOMER & CATEGORY INSIGHTS
    # =========================================================
    with tabs[2]:
        st.markdown("<div class='section-header'>Customer Account Tiers & Product Line Distribution</div>", unsafe_allow_html=True)
        c_tier1, c_tier2 = st.columns(2)

        with c_tier1:
            st.markdown("### Revenue by Client Tier")
            tiers = deals_kpis.get("deals_by_tier", {})
            if tiers:
                df_tier = pd.DataFrame(list(tiers.items()), columns=["Tier", "Deals Count"])
                fig_tier = px.pie(
                    df_tier, names="Tier", values="Deals Count",
                    color_discrete_sequence=["#1e3a8a", "#3b82f6", "#93c5fd"], hole=0.45
                )
                fig_tier.update_layout(height=320)
                st.plotly_chart(fig_tier, use_container_width=True)

        with c_tier2:
            st.markdown("### Product Category Distribution")
            cats = deals_kpis.get("deals_by_category", {})
            if cats:
                df_cat = pd.DataFrame(list(cats.items()), columns=["Category", "Deals Count"])
                fig_cat = px.bar(
                    df_cat, x="Category", y="Deals Count",
                    color="Category", color_discrete_sequence=px.colors.qualitative.Safe, template="plotly_white"
                )
                fig_cat.update_layout(showlegend=False, height=320)
                st.plotly_chart(fig_cat, use_container_width=True)

    # =========================================================
    # TAB 4: FINANCIAL & OPERATIONS HEALTH
    # =========================================================
    with tabs[3]:
        st.markdown("<div class='section-header'>Accounts Receivable & Operational Progress</div>", unsafe_allow_html=True)
        f_col1, f_col2 = st.columns(2)

        with f_col1:
            st.markdown("### Financial Leakage & Balance (₹)")
            fin_df = pd.DataFrame({
                "Metric": ["Contract Revenue", "Invoiced / Billed", "Cash Collected", "Billing Gap (Unbilled)", "Collection Gap (Overdue)"],
                "Amount (₹)": [
                    financial.get("revenue", 0.0),
                    financial.get("billed", 0.0),
                    financial.get("collected", 0.0),
                    financial.get("billing_gap", 0.0),
                    financial.get("collection_gap", 0.0)
                ]
            })
            fig_fin = px.bar(
                fin_df, x="Metric", y="Amount (₹)", color="Metric",
                color_discrete_sequence=["#3b82f6", "#6366f1", "#10b981", "#f59e0b", "#ef4444"],
                template="plotly_white"
            )
            fig_fin.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig_fin, use_container_width=True)

        with f_col2:
            st.markdown("### Work Order Execution Status")
            wo_status = wo_kpis.get("work_orders_by_status", {})
            if wo_status:
                df_wo_st = pd.DataFrame(list(wo_status.items()), columns=["Status", "Orders"])
                fig_wo = px.pie(
                    df_wo_st, names="Status", values="Orders",
                    color_discrete_sequence=px.colors.qualitative.Pastel, hole=0.4
                )
                fig_wo.update_layout(height=350)
                st.plotly_chart(fig_wo, use_container_width=True)

        # Operational project list
        if not engine.filtered_wo_df.empty:
            st.markdown("### Work Orders Progress Table")
            wo_cols = [c for c in ["order_name", "client_name", "contract_value", "billed_amount", "collected_amount", "completion_percent", "status"] if c in engine.filtered_wo_df.columns]
            st.dataframe(engine.filtered_wo_df[wo_cols], use_container_width=True, hide_index=True)

    # =========================================================
    # TAB 5: AI BUSINESS ASSISTANT
    # =========================================================
    with tabs[4]:
        st.markdown("<div class='section-header'>🤖 AI Strategic Business Assistant</div>", unsafe_allow_html=True)
        st.write("Ask natural-language business questions to identify bottlenecks, compute leakage, and generate executive recommendations.")

        assistant = BusinessAssistant(summary=summary)

        # Quick prompt buttons
        q_cols = st.columns(4)
        quick_query = None
        if q_cols[0].button("🚨 Which projects are delayed?", use_container_width=True):
            quick_query = "Which projects are delayed or at risk?"
        if q_cols[1].button("💰 How is collection efficiency?", use_container_width=True):
            quick_query = "How is our collection efficiency and receivables?"
        if q_cols[2].button("📊 What is our billing gap?", use_container_width=True):
            quick_query = "What is our billing gap and unbilled revenue?"
        if q_cols[3].button("📈 Give executive briefing", use_container_width=True):
            quick_query = "Provide a comprehensive executive business briefing."

        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Render conversation history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask a business intelligence question...") or quick_query
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing business KPIs and operational workflows..."):
                    answer = assistant.ask(user_input)
                    st.markdown(answer)
                    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # =========================================================
    # TAB 6: SQL DATA EXPLORER & EXCEL EXPORT
    # =========================================================
    with tabs[5]:
        st.markdown("<div class='section-header'>🗄️ SQL Data Explorer & Excel Reporting</div>", unsafe_allow_html=True)
        st.write("Demonstrates technical database querying (SQLite/DBMS) and export capabilities for executive reporting.")

        st.markdown("### Execute Custom SQL Query")
        sample_query = "SELECT client_tier, count(*) as deal_count, round(sum(deal_value), 2) as total_value FROM deals GROUP BY client_tier;"
        user_query = st.text_area("SQL Statement:", value=sample_query, height=85)

        if st.button("▶️ Run SQL Query"):
            try:
                sql_results = database.execute_sql(user_query)
                st.success(f"Query returned {len(sql_results)} rows.")
                st.dataframe(sql_results, use_container_width=True)
            except Exception as e:
                st.error(f"SQL Execution Error: {e}")

        st.markdown("---")
        st.markdown("### Export Filtered Datasets to Excel & CSV")
        exp_col1, exp_col2 = st.columns(2)

        # Excel Export
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            engine.filtered_deals_df.to_excel(writer, sheet_name="Deals_Pipeline", index=False)
            engine.filtered_wo_df.to_excel(writer, sheet_name="Work_Orders", index=False)
        excel_data = excel_buffer.getvalue()

        exp_col1.download_button(
            label="📥 Download Executive Report (Excel .xlsx)",
            data=excel_data,
            file_name=f"Monday_BI_Executive_Report_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # CSV Export
        deals_csv = engine.filtered_deals_df.to_csv(index=False).encode("utf-8")
        exp_col2.download_button(
            label="📥 Download Filtered Deals (CSV)",
            data=deals_csv,
            file_name=f"Filtered_Deals_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )


if __name__ == "__main__":
    main()