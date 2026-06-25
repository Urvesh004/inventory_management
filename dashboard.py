import streamlit as st
import plotly.express as px
import pandas as pd
import datetime

# ✅ CORRECT: Import from database.py (no circular import)
from database import get_db, get_low_stock_products, require_permission

def render_dashboard():
    if not require_permission("dashboard"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">📊</div>
        <div><h1>Dashboard</h1><p>Real-time overview of your inventory</p></div>
    </div>""", unsafe_allow_html=True)

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM products")
        total_products = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(quantity),0) FROM products")
        total_stock = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock")
        low_stock_count = c.fetchone()[0]
        today = datetime.date.today()
        c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)=?", (today.isoformat(),))
        today_revenue = c.fetchone()[0]
        month_start = today.replace(day=1).isoformat()
        c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)>=?", (month_start,))
        month_revenue = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(total),0) FROM sales")
        total_revenue = c.fetchone()[0]

    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
    metrics = [
        (mc1, "mc-indigo", "📦", "Total Products", f"{total_products}", ""),
        (mc2, "mc-emerald", "🗃️", "Total Stock", f"{total_stock:,}", "units"),
        (mc3, "mc-amber", "⚠️", "Low Stock", f"{low_stock_count}", "items below minimum"),
        (mc4, "mc-cyan", "💵", "Today's Sales", f"₹{today_revenue:,.1f}", ""),
        (mc5, "mc-violet", "📅", "Monthly Revenue", f"₹{month_revenue:,.1f}", ""),
        (mc6, "mc-rose", "🏆", "Total Revenue", f"₹{total_revenue:,.1f}", ""),
    ]
    for col, cls, icon, label, value, sub in metrics:
        with col:
            st.markdown(f"""<div class="metric-card {cls}"><div class="label">{icon} {label}</div><div class="value">{value}</div><div class="sub">{sub}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 📊 Sales Last 30 Days")
        with get_db() as conn:
            df_sales = pd.read_sql_query("SELECT date(sale_date) as date, SUM(total) as total FROM sales WHERE sale_date >= date('now', '-30 days') GROUP BY date(sale_date) ORDER BY date", conn)
        if not df_sales.empty:
            fig = px.bar(df_sales, x="date", y="total", color_discrete_sequence=["#6366f1"])
            fig.update_layout(xaxis_title="Date", yaxis_title="Revenue (₹)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=320, margin=dict(l=10, r=10, t=10, b=10), xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"))
            fig.update_traces(marker_line_width=0, marker_cornerradius=6)
            st.plotly_chart(fig, width='stretch')
        else:
            st.info("No sales data in the last 30 days.")

    with col_right:
        st.markdown("### 📦 Stock by Category")
        with get_db() as conn:
            df_cat = pd.read_sql_query("SELECT category, SUM(quantity) as total_qty FROM products GROUP BY category ORDER BY total_qty DESC", conn)
        if not df_cat.empty:
            colors = ["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#06b6d4", "#8b5cf6"]
            fig2 = px.pie(df_cat, names="category", values="total_qty", color_discrete_sequence=colors, hole=0.55)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#94a3b8", height=320, margin=dict(l=10, r=10, t=10, b=10), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.15))
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig2, width='stretch')

    low_stock = get_low_stock_products()
    if low_stock:
        st.markdown("---")
        st.markdown("""<div class="alert-box alert-warning"><span style="font-size:1.3rem;">⚠️</span><div><strong>Low Stock Alert</strong> — Items at or below minimum stock levels:</div></div>""", unsafe_allow_html=True)
        low_df = pd.DataFrame(low_stock)[["name", "sku", "category", "quantity", "min_stock"]]
        low_df["status"] = low_df.apply(lambda r: "🔴 Critical" if r["quantity"] == 0 else "🟡 Low", axis=1)
        st.dataframe(low_df, width='stretch', hide_index=True)

    st.markdown("---")
    st.markdown("### 🕐 Recent Activity")
    with get_db() as conn:
        df_logs = pd.read_sql_query(
    """
    SELECT 
        l.action,
        l.module,
        l.details,
        datetime(l.timestamp) as timestamp,
        u.full_name
    FROM logs l
    LEFT JOIN users u ON l.user_id = u.id
    ORDER BY l.timestamp DESC
    LIMIT 10
    """,
    conn
)
    if not df_logs.empty:
        for _, row in df_logs.iterrows():
            action_colors = {"LOGIN": "#6366f1", "LOGOUT": "#64748b", "CREATE": "#10b981", "UPDATE": "#f59e0b", "DELETE": "#f43f5e", "VIEW": "#06b6d4"}
            color = action_colors.get(row["action"], "#64748b")
            st.markdown(f"""<div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid #1e293b;"><div style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></div><div style="flex:1;"><span style="color:#e2e8f0;font-weight:600;font-size:0.9rem;">{row['full_name']}</span><span style="color:#94a3b8;font-size:0.85rem;"> {row['action']} on {row['module']}</span><span style="color:#64748b;font-size:0.8rem;"> — {row['details'][:60]}</span></div><div style="color:#475569;font-size:0.75rem;white-space:nowrap;">{str(row['timestamp'])[:16]}</div></div>""", unsafe_allow_html=True)
    else:
        st.info("No recent activity.")