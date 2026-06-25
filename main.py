import streamlit as st

# Import from database FIRST (no circular dependency)
from database import (
    init_database, authenticate_user, get_user_permissions, 
    add_log, check_permission
)

# Import page renderers AFTER database
from dashboard import render_dashboard
from logs import render_logs
from products import render_products
from purcheses import render_purchases
from reports import render_reports
from sales import render_sales
from staff import render_staff_access

# ──────────────────────────────────────────────
#  CUSTOM CSS STYLING
# ──────────────────────────────────────────────

def load_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        .stApp { font-family: 'Inter', sans-serif; }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
            border-right: 1px solid rgba(99,102,241,0.15);
        }
        [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }
        [data-testid="stSidebarNav"] { display: none; }
        section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }
        .block-container { padding-top: 2rem; max-width: 1400px; }
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 16px; padding: 1.5rem; color: #f1f5f9;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative; overflow: hidden;
        }
        .metric-card::before {
            content: ''; position: absolute; top: 0; left: 0;
            width: 4px; height: 100%; border-radius: 4px 0 0 4px;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(99,102,241,0.15); }
        .metric-card .label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem; font-weight: 500; }
        .metric-card .value { font-size: 2rem; font-weight: 800; line-height: 1.2; }
        .metric-card .sub { font-size: 0.8rem; margin-top: 0.35rem; }
        .mc-indigo::before { background: #6366f1; } .mc-indigo .value { color: #a5b4fc; }
        .mc-emerald::before { background: #10b981; } .mc-emerald .value { color: #6ee7b7; }
        .mc-amber::before { background: #f59e0b; } .mc-amber .value { color: #fcd34d; }
        .mc-rose::before { background: #f43f5e; } .mc-rose .value { color: #fda4af; }
        .mc-cyan::before { background: #06b6d4; } .mc-cyan .value { color: #67e8f9; }
        .mc-violet::before { background: #8b5cf6; } .mc-violet .value { color: #c4b5fd; }
        .dataframe { border-radius: 12px !important; overflow: hidden; border: 1px solid #334155 !important; }
        .dataframe thead tr th { background: #1e293b !important; color: #a5b4fc !important; font-weight: 600 !important; padding: 0.75rem 1rem !important; border-bottom: 2px solid #6366f1 !important; }
        .dataframe tbody tr td { padding: 0.65rem 1rem !important; border-bottom: 1px solid #1e293b !important; color: #e2e8f0 !important; }
        .dataframe tbody tr:hover td { background: rgba(99,102,241,0.08) !important; }
        .dataframe tbody tr:nth-child(even) td { background: rgba(15,23,42,0.4); }
        .stButton > button { border-radius: 10px !important; font-weight: 600 !important; transition: all 0.2s !important; }
        .stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important; }
        .section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; }
        .section-header .icon-box { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; }
        .section-header h1 { font-size: 1.8rem; font-weight: 800; margin: 0; color: #f1f5f9; }
        .section-header p { font-size: 0.9rem; color: #64748b; margin: 0; }
        .badge { display: inline-flex; align-items: center; padding: 0.2rem 0.65rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
        .badge-active { background: rgba(16,185,129,0.15); color: #10b981; }
        .badge-inactive { background: rgba(244,63,94,0.15); color: #f43f5e; }
        .badge-admin { background: rgba(99,102,241,0.15); color: #a5b4fc; }
        .badge-staff { background: rgba(6,182,212,0.15); color: #67e8f9; }
        .perm-item { text-align: center; padding: 0.4rem; border-radius: 8px; font-size: 0.75rem; font-weight: 600; }
        .perm-on { background: rgba(16,185,129,0.15); color: #10b981; }
        .perm-off { background: rgba(100,116,139,0.15); color: #64748b; }
        .alert-box { border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem; display: flex; align-items: flex-start; gap: 0.75rem; }
        .alert-warning { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
        .login-container { max-width: 420px; margin: 4rem auto; background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid rgba(99,102,241,0.2); border-radius: 24px; padding: 3rem; box-shadow: 0 25px 60px rgba(0,0,0,0.5); }
        .login-logo { width: 72px; height: 72px; border-radius: 20px; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto 1.5rem; }
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; } ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        [data-testid="stHeader"] { background: rgba(15,23,42,0.9); }
        .stTextInput > div > div > input, .stNumberInput > div > div > input, .stSelectbox > div > div > select { border-radius: 10px !important; }
        .stSuccess, .stWarning, .stError, .stInfo { border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  SIDEBAR NAVIGATION
# ──────────────────────────────────────────────

NAV_ITEMS = [
    ("dashboard", "📊", "Dashboard"),
    ("sales", "💰", "Sales"),
    ("products", "📦", "Products"),
    ("purchases", "🛒", "Purchases"),
    ("logs", "📋", "Logs"),
    ("reports", "📈", "Reports"),
    ("staff_access", "👥", "Staff Access"),
]

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:1rem 0 1.5rem;">
            <div style="width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                        display:inline-flex;align-items:center;justify-content:center;font-size:1.5rem;margin-bottom:0.5rem;">🗄️</div>
            <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9;">InvenTrack</div>
            <div style="font-size:0.75rem;color:#64748b;">Inventory Management</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div style='height:1px;background:rgba(99,102,241,0.2);margin:0 0.5rem 1rem;'></div>", unsafe_allow_html=True)

        for key, icon, label in NAV_ITEMS:
            if key == "staff_access" and st.session_state.user["role"] != "admin":
                continue
            if not check_permission(key, "can_view"):
                continue
            if st.button(f"{icon}  {label}", key=f"nav_{key}", width='stretch'):
                st.session_state.current_page = key
                st.rerun()

        st.markdown("<div style='height:1px;background:rgba(99,102,241,0.2);margin:1.5rem 0.5rem 1rem;'></div>", unsafe_allow_html=True)

        user = st.session_state.user
        role_badge = "badge-admin" if user["role"] == "admin" else "badge-staff"
        role_label = "Administrator" if user["role"] == "admin" else "Staff"
        st.markdown(f"""
        <div style="padding:0.75rem;border-radius:12px;background:rgba(30,41,59,0.6);border:1px solid rgba(99,102,241,0.1);">
            <div style="display:flex;align-items:center;gap:0.75rem;">
                <div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
                            display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:1rem;">
                    {user['full_name'][0].upper()}</div>
                <div><div style="font-weight:600;color:#f1f5f9;font-size:0.9rem;">{user['full_name']}</div>
                <span class="badge {role_badge}">{role_label}</span></div>
            </div>
        </div>""", unsafe_allow_html=True)

        if st.button("🚪  Sign Out", key="logout_btn", width='stretch'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ──────────────────────────────────────────────
#  LOGIN PAGE
# ──────────────────────────────────────────────

def render_login():
    st.markdown("""
    <div class="login-container">
        <div class="login-logo">🗄️</div>
        <h1 style="text-align:center;color:#f1f5f9;font-size:1.8rem;font-weight:800;margin-bottom:0.25rem;">Welcome Back</h1>
        <p style="text-align:center;color:#64748b;margin-bottom:2rem;">Sign in to InvenTrack</p>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        username = st.text_input("Username", placeholder="Enter your username", key="login_user")
        password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
        if st.button("🔐  Sign In", width='stretch', type="primary"):
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.permissions = get_user_permissions(user["id"])
                    st.session_state.current_page = "dashboard"
                    add_log(user["id"], "LOGIN", "auth", f"User {username} logged in")
                    st.rerun()
                else:
                    st.error("Invalid credentials or account is disabled.")
        st.markdown("""
        <div style="text-align:center;margin-top:1.5rem;color:#475569;font-size:0.8rem;">
            Default admin: <strong style="color:#a5b4fc;">admin</strong> / <strong style="color:#a5b4fc;">admin123</strong>
        </div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────

def main():
    st.set_page_config(page_title="InvenTrack", page_icon="🗄️", layout="wide", initial_sidebar_state="expanded")
    load_custom_css()
    init_database()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"

    if "user" not in st.session_state:
        render_login()
        return

    render_sidebar()

    page_renderers = {
        "dashboard": render_dashboard,
        "sales": render_sales,
        "products": render_products,
        "purchases": render_purchases,
        "logs": render_logs,
        "reports": render_reports,
        "staff_access": render_staff_access,
    }
    renderer = page_renderers.get(st.session_state.current_page, render_dashboard)
    renderer()

    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem;color:#334155;font-size:0.75rem;border-top:1px solid #1e293b;margin-top:3rem;">
        InvenTrack Inventory Management System v1.0</div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()