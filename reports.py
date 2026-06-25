import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ✅ Changed from: from main import ...
from database import get_db, require_permission

def render_reports():
    if not require_permission("reports"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">📈</div>
        <div><h1>Reports</h1><p>Detailed analytics and reporting</p></div>
    </div>""", unsafe_allow_html=True)

    report_tabs = st.tabs(["💰 Revenue", "📦 Inventory", "🏆 Top Products", "📊 Sales Trend"])

    with report_tabs[0]:
        st.markdown("### 💰 Revenue Analysis")
        rev_period = st.selectbox("Period", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year", "All Time"], key="rev_period")
        period_map = {"Last 7 Days": "7 days", "Last 30 Days": "30 days", "Last 90 Days": "90 days", "This Year": "365 days", "All Time": "10000 days"}
        period_days = period_map[rev_period]
        with get_db() as conn:
            df_rev = pd.read_sql_query(f"SELECT date(sale_date) as date, COUNT(*) as transactions, SUM(quantity) as items, SUM(total) as revenue FROM sales WHERE sale_date >= date('now', '-{period_days}') GROUP BY date(sale_date) ORDER BY date", conn)
        if not df_rev.empty:
            total_rev = df_rev["revenue"].sum()
            avg_daily = df_rev["revenue"].mean()
            best_day = df_rev.loc[df_rev["revenue"].idxmax()]
            rm1, rm2, rm3 = st.columns(3)
            with rm1: st.metric("Total Revenue", f"₹{total_rev:,.2f}")
            with rm2: st.metric("Daily Average", f"₹{avg_daily:,.2f}")
            with rm3: st.metric("Best Day", f"₹{best_day['revenue']:,.2f}", f"{best_day['date']}")
            fig = px.area(df_rev, x="date", y="revenue", color_discrete_sequence=["#6366f1"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
            fig.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.1)")
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No revenue data for the selected period.")

    with report_tabs[1]:
        st.markdown("### 📦 Inventory Valuation")
        with get_db() as conn:
            df_inv = pd.read_sql_query("SELECT category, COUNT(*) as product_count, SUM(quantity) as total_units, SUM(quantity * cost) as stock_value, SUM(quantity * price) as retail_value, AVG((price - cost) / price * 100) as avg_margin FROM products GROUP BY category", conn)
        if not df_inv.empty:
            total_stock_val = df_inv["stock_value"].sum()
            total_retail_val = df_inv["retail_value"].sum()
            iv1, iv2 = st.columns(2)
            with iv1: st.metric("Total Stock Value (Cost)", f"₹{total_stock_val:,.2f}")
            with iv2: st.metric("Total Retail Value", f"₹{total_retail_val:,.2f}")
            fig_inv = px.bar(df_inv, x="category", y=["stock_value", "retail_value"], barmode="group", color_discrete_sequence=["#6366f1", "#10b981"])
            fig_inv.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
            st.plotly_chart(fig_inv, width='stretch')
            df_inv_display = df_inv.copy()
            df_inv_display["stock_value"] = df_inv_display["stock_value"].apply(lambda x: f"₹{x:,.2f}")
            df_inv_display["retail_value"] = df_inv_display["retail_value"].apply(lambda x: f"₹{x:,.2f}")
            df_inv_display["avg_margin"] = df_inv_display["avg_margin"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(df_inv_display, width='stretch', hide_index=True)
        else:
            st.info("No inventory data available.")

    with report_tabs[2]:
        st.markdown("### 🏆 Top Selling Products")
        with get_db() as conn:
            df_top = pd.read_sql_query("SELECT p.name, p.sku, p.category, SUM(s.quantity) as total_sold, SUM(s.total) as total_revenue, AVG(s.unit_price) as avg_price FROM sales s JOIN products p ON s.product_id = p.id GROUP BY s.product_id ORDER BY total_revenue DESC LIMIT 15", conn)
        if not df_top.empty:
            fig_top = px.bar(df_top, x="name", y="total_revenue", color="category", color_discrete_sequence=["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#06b6d4"])
            fig_top.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(gridcolor="#1e293b", tickangle=-30), yaxis=dict(gridcolor="#1e293b"))
            fig_top.update_traces(marker_line_width=0, marker_cornerradius=6)
            st.plotly_chart(fig_top, width='stretch')
            df_top_display = df_top.copy()
            df_top_display["total_revenue"] = df_top_display["total_revenue"].apply(lambda x: f"₹{x:,.2f}")
            df_top_display["avg_price"] = df_top_display["avg_price"].apply(lambda x: f"₹{x:,.2f}")
            st.dataframe(df_top_display, width='stretch', hide_index=True)
        else:
            st.info("No sales data available.")

    with report_tabs[3]:
        st.markdown("### 📊 Sales Trend & Forecast")
        with get_db() as conn:
            df_trend = pd.read_sql_query("SELECT date(sale_date) as date, SUM(total) as revenue, COUNT(*) as orders FROM sales WHERE sale_date >= date('now', '-90 days') GROUP BY date(sale_date) ORDER BY date", conn)
        if not df_trend.empty and len(df_trend) > 3:
            df_trend["date"] = pd.to_datetime(df_trend["date"])
            df_trend["rolling_avg"] = df_trend["revenue"].rolling(window=7, min_periods=1).mean()
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=df_trend["date"], y=df_trend["revenue"], mode="lines", name="Daily Revenue", line=dict(color="#6366f1", width=1.5), opacity=0.6))
            fig_trend.add_trace(go.Scatter(x=df_trend["date"], y=df_trend["rolling_avg"], mode="lines", name="7-Day Average", line=dict(color="#f59e0b", width=2.5)))
            fig_trend.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=400, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"), legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_trend, width='stretch')
        else:
            st.info("Need at least a few days of sales data to show trends.")