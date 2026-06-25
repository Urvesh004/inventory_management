import pandas as pd
import streamlit as st
# SELECT timestamp FROM logs;

# ✅ Changed from: from main import ...
from database import get_all_users, get_db, require_permission

def render_logs():
    if not require_permission("logs"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">📋</div>
        <div><h1>Activity Logs</h1><p>Track all system activities and changes</p></div>
    </div>""", unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        log_user = st.selectbox("User", ["All"] + [u["full_name"] for u in get_all_users()], key="log_user")
    with fc2:
        log_action = st.selectbox("Action", ["All", "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE", "VIEW"], key="log_action")
    with fc3:
        log_module = st.selectbox("Module", ["All", "auth", "products", "sales", "purchases", "staff", "reports"], key="log_module")
    with fc4:
        log_limit = st.selectbox("Show", [50, 100, 200, 500], index=1, key="log_limit")

    query = "SELECT l.id, u.full_name as user, l.action, l.module, l.details, l.timestamp FROM logs l LEFT JOIN users u ON l.user_id = u.id WHERE 1=1"
    params = []
    if log_user != "All":
        query += " AND u.full_name = ?"
        params.append(log_user)
    if log_action != "All":
        query += " AND l.action = ?"
        params.append(log_action)
    if log_module != "All":
        query += " AND l.module = ?"
        params.append(log_module)
    query += f" ORDER BY l.timestamp DESC LIMIT {log_limit}"

    with get_db() as conn:
        df_logs = pd.read_sql_query(query, conn, params=params)

    if not df_logs.empty:
        action_colors = {"LOGIN": "#6366f1", "LOGOUT": "#64748b", "CREATE": "#10b981", "UPDATE": "#f59e0b", "DELETE": "#f43f5e", "VIEW": "#06b6d4"}
        for _, row in df_logs.iterrows():
            color = action_colors.get(row["action"], "#64748b")
            st.markdown(f"""<div style="display:flex;align-items:center;gap:0.75rem;padding:0.6rem 0;border-bottom:1px solid #1e293b;"><div style="min-width:6px;height:6px;border-radius:50%;background:{color};"></div><div style="min-width:60px;font-size:0.75rem;color:#64748b;">#{row['id']}</div><div style="min-width:120px;font-weight:600;color:#e2e8f0;font-size:0.9rem;">{row['user'] or 'System'}</div><div style="min-width:80px;"><span style="background:{color}22;color:{color};padding:0.15rem 0.6rem;border-radius:12px;font-size:0.75rem;font-weight:600;">{row['action']}</span></div><div style="min-width:80px;font-size:0.8rem;color:#94a3b8;">{row['module']}</div><div style="flex:1;font-size:0.85rem;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{row['details'][:80]}</div><div style="font-size:0.75rem;color:#475569;white-space:nowrap;">{str(row['timestamp'])[:16]}</div></div>""", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;color:#64748b;padding:1rem;font-size:0.85rem;'>Showing {len(df_logs)} log entries</div>", unsafe_allow_html=True)
    else:
        st.info("No log entries match your filters.")