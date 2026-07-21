import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Tuple
from bi_engine import BIEngine
from config import logger

@st.cache_resource(ttl=600)
def load_cached_summary() -> Tuple[Dict[str, Any], bool]:
    """
    Initializes the BI Engine, loads data, and calculates the executive summary.
    Returns the summary dictionary and a boolean indicating if it succeeded.
    """
    try:
        engine = BIEngine()
        engine.load_data()
        summary = engine.calculate_executive_summary()
        # Verify that we actually got data
        if not summary or not summary.get("Deals") or not summary.get("Work_Orders"):
            return {}, False
        return summary, True
    except Exception as e:
        logger.error(f"Failed to load BI data: {str(e)}", exc_info=True)
        return {}, False

def main() -> None:
    """
    Main function to render the Monday Business Intelligence Dashboard.
    """
    # Page setup
    st.set_page_config(
        page_title="Monday Business Intelligence Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom styling
    st.markdown("""
    <style>
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e2e8f0;
            padding: 1.25rem;
            border-radius: 0.5rem;
            text-align: center;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        }
        .metric-val {
            font-size: 1.85rem;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }
        .metric-lbl {
            font-size: 0.8rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .section-header {
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 0.5rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            font-weight: 700;
            color: #0f172a;
        }
    </style>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.title("Monday BI Agent")
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Metadata")
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.sidebar.info(f"Last updated:\n{current_time}")

    # Title & Subtitle
    st.title("📊 Monday Business Intelligence Dashboard")
    st.markdown("Automated strategic pipeline and operations analysis.")

    # Load data
    summary, success = load_cached_summary()

    if not success:
        st.warning("⚠️ Data is currently unavailable. Please check your Monday.com API credentials or database connection.")
        return

    # Extract metrics
    deals_kpis = summary.get("Deals", {})
    wo_kpis = summary.get("Work_Orders", {})
    financial = summary.get("Financial", {})
    operations = summary.get("Operations", {})

    # Top-level KPI Cards
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    
    with kpi_col1:
        total_deals = deals_kpis.get("total_deals", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{total_deals}</div>
            <div class="metric-lbl">Total Deals</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col2:
        pipe_val = deals_kpis.get("total_pipeline_value", 0.0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">₹{pipe_val:,.2f}</div>
            <div class="metric-lbl">Pipeline Value</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col3:
        contract_val = wo_kpis.get("total_contract_value", 0.0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">₹{contract_val:,.2f}</div>
            <div class="metric-lbl">Contract Value</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi_col4:
        coll_eff = wo_kpis.get("collection_efficiency", 0.0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-val">{coll_eff:.2f}%</div>
            <div class="metric-lbl">Collection Efficiency</div>
        </div>
        """, unsafe_allow_html=True)

    # Section 1: Deals Analytics
    st.markdown("<h2 class='section-header'>Section 1: Deals Analytics</h2>", unsafe_allow_html=True)
    d_col1, d_col2 = st.columns(2)
    
    with d_col1:
        st.subheader("Pipeline by Status")
        pipeline_by_status = deals_kpis.get("pipeline_by_status", {})
        if pipeline_by_status:
            df_status = pd.DataFrame(list(pipeline_by_status.items()), columns=["Status", "Count"])
            fig_bar = px.bar(
                df_status,
                x="Status",
                y="Count",
                labels={"Count": "Deals Count", "Status": "Deal Status"},
                color="Count",
                color_continuous_scale="Blues",
                template="plotly_white"
            )
            fig_bar.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No status data available for deals.")
            
    with d_col2:
        st.subheader("Deals by Owner")
        deals_by_owner = deals_kpis.get("deals_by_owner", {})
        if deals_by_owner:
            df_owner = pd.DataFrame(list(deals_by_owner.items()), columns=["Owner", "Count"])
            fig_hbar = px.bar(
                df_owner,
                x="Count",
                y="Owner",
                orientation="h",
                labels={"Count": "Deals Count", "Owner": "Deal Owner"},
                color="Count",
                color_continuous_scale="Purples",
                template="plotly_white"
            )
            fig_hbar.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_hbar, use_container_width=True)
        else:
            st.info("No owner data available for deals.")

    # Section 2: Work Orders
    st.markdown("<h2 class='section-header'>Section 2: Work Orders</h2>", unsafe_allow_html=True)
    w_col1, w_col2 = st.columns([1, 1])
    
    with w_col1:
        st.subheader("Status Distribution")
        wo_status_dist = wo_kpis.get("work_orders_by_status", {})
        if wo_status_dist:
            df_wo_status = pd.DataFrame(list(wo_status_dist.items()), columns=["Status", "Count"])
            fig_pie = px.pie(
                df_wo_status,
                values="Count",
                names="Status",
                color_discrete_sequence=px.colors.qualitative.Safe,
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No status distribution available for work orders.")
            
    with w_col2:
        st.markdown("### Operational Metrics")
        st.write(f"**Total Work Orders:** {wo_kpis.get('total_work_orders', 0)}")
        st.write(f"**Largest Work Order:** ₹{wo_kpis.get('largest_work_order', 0.0):,.2f}")
        st.write(f"**Average Contract Value:** ₹{wo_kpis.get('average_contract_value', 0.0):,.2f}")
        st.write(f"**Billing Completion:** {wo_kpis.get('billing_completion_percent', 0.0):.2f}%")

    # Section 3: Financial Summary
    st.markdown("<h2 class='section-header'>Section 3: Financial Summary</h2>", unsafe_allow_html=True)
    if financial:
        fin_col1, fin_col2 = st.columns(2)
        
        with fin_col1:
            st.markdown("### Revenue & Accounts Receivable Balance")
            st.write(f"**Revenue (Contract Value):** ₹{financial.get('revenue', 0.0):,.2f}")
            st.write(f"**Billed Value:** ₹{financial.get('billed', 0.0):,.2f}")
            st.write(f"**Collected Amount:** ₹{financial.get('collected', 0.0):,.2f}")
            st.write(f"**Outstanding Receivables:** ₹{financial.get('receivables', 0.0):,.2f}")
            
        with fin_col2:
            st.markdown("### Financial Leakage & Gaps")
            st.write(f"**Billing Gap (Revenue - Billed):** ₹{financial.get('billing_gap', 0.0):,.2f}")
            st.write(f"**Collection Gap (Billed - Collected):** ₹{financial.get('collection_gap', 0.0):,.2f}")
            
            # Gauge chart for collection efficiency
            coll_val = financial.get("collected", 0.0)
            bill_val = financial.get("billed", 0.0)
            eff_rate = (coll_val / bill_val * 100) if bill_val > 0 else 0.0
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=eff_rate,
                title={"text": "Collection Efficiency Rate (%)"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#1e293b"},
                    "steps": [
                        {"range": [0, 50], "color": "#f87171"},
                        {"range": [50, 80], "color": "#fbbf24"},
                        {"range": [80, 100], "color": "#34d399"}
                    ]
                }
            ))
            fig_gauge.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("Financial indicators are currently unavailable.")

    # Section 4: Operations
    st.markdown("<h2 class='section-header'>Section 4: Operations</h2>", unsafe_allow_html=True)
    if operations:
        op_col1, op_col2 = st.columns(2)
        
        with op_col1:
            st.markdown("### Project Breakdown")
            st.write(f"**Total Projects:** {operations.get('total_projects', 0)}")
            st.write(f"**Completed Projects:** {operations.get('completed_projects', 0)}")
            st.write(f"**Active Projects:** {operations.get('active_projects', 0)}")
            st.write(f"**Delayed Projects:** {operations.get('delayed_projects', 0)}")
            
        with op_col2:
            st.markdown("### Completion Rate")
            rate = operations.get("completion_rate", 0.0)
            st.write(f"**Project Completion Rate:** {rate:.2f}%")
            
            fig_comp = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rate,
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#3b82f6"},
                    "steps": [
                        {"range": [0, 50], "color": "#fee2e2"},
                        {"range": [50, 100], "color": "#dbeafe"}
                    ]
                }
            ))
            fig_comp.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Operational indicators are currently unavailable.")

if __name__ == "__main__":
    main()