import hashlib
import streamlit as st


# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()

# ──────────────────────────────────────────────
#  PERMISSION DECORATOR
# ──────────────────────────────────────────────

def check_permission(module, action="can_view"):
    """Check if current user has permission for a module/action."""
    if "user" not in st.session_state:
        return False
    if st.session_state.user["role"] == "admin":
        return True
    perms = st.session_state.get("permissions", {})
    mod_perms = perms.get(module, {})
    return mod_perms.get(action, False)

def require_permission(module, action="can_view"):
    """Show access denied if permission missing."""
    if not check_permission(module, action):
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                    min-height:50vh;text-align:center;">
            <div style="font-size:4rem;margin-bottom:0.5rem;">🔒</div>
            <h2 style="color:#ef4444;margin:0;">Access Denied</h2>
            <p style="color:#94a3b8;font-size:1.1rem;">You don't have permission to access this section.<br>
            Contact your administrator to request access.</p>
        </div>
        """, unsafe_allow_html=True)
        return False
    return True

# ──────────────────────────────────────────────
#  CUSTOM CSS STYLING
# ──────────────────────────────────────────────

def load_custom_css():
    st.markdown("""
    <style>
        /* ── Global ── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        .stApp {
            font-family: 'Inter', sans-serif;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
            border-right: 1px solid rgba(99,102,241,0.15);
        }
        [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }
        [data-testid="stSidebarNav"] { display: none; }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        /* ── Main container ── */
        .block-container {
            padding-top: 2rem;
            max-width: 1400px;
        }

        /* ── Metric cards ── */
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 16px;
            padding: 1.5rem;
            color: #f1f5f9;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }
        .metric-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 4px; height: 100%;
            border-radius: 4px 0 0 4px;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(99,102,241,0.15);
        }
        .metric-card .label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem; font-weight: 500; }
        .metric-card .value { font-size: 2rem; font-weight: 800; line-height: 1.2; }
        .metric-card .sub { font-size: 0.8rem; margin-top: 0.35rem; }

        .mc-indigo::before { background: #6366f1; }
        .mc-indigo .value { color: #a5b4fc; }

        .mc-emerald::before { background: #10b981; }
        .mc-emerald .value { color: #6ee7b7; }

        .mc-amber::before { background: #f59e0b; }
        .mc-amber .value { color: #fcd34d; }

        .mc-rose::before { background: #f43f5e; }
        .mc-rose .value { color: #fda4af; }

        .mc-cyan::before { background: #06b6d4; }
        .mc-cyan .value { color: #67e8f9; }

        .mc-violet::before { background: #8b5cf6; }
        .mc-violet .value { color: #c4b5fd; }

        /* ── Table styling ── */
        .dataframe {
            border-radius: 12px !important;
            overflow: hidden;
            border: 1px solid #334155 !important;
        }
        .dataframe thead tr th {
            background: #1e293b !important;
            color: #a5b4fc !important;
            font-weight: 600 !important;
            padding: 0.75rem 1rem !important;
            border-bottom: 2px solid #6366f1 !important;
        }
        .dataframe tbody tr td {
            padding: 0.65rem 1rem !important;
            border-bottom: 1px solid #1e293b !important;
            color: #e2e8f0 !important;
        }
        .dataframe tbody tr:hover td {
            background: rgba(99,102,241,0.08) !important;
        }
        .dataframe tbody tr:nth-child(even) td {
            background: rgba(15,23,42,0.4);
        }

        /* ── Buttons ── */
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.2s !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important;
        }

        /* ── Nav buttons in sidebar ── */
        .nav-btn {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 12px;
            border: none;
            background: transparent;
            color: #94a3b8;
            font-size: 0.95rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            margin-bottom: 4px;
        }
        .nav-btn:hover {
            background: rgba(99,102,241,0.12);
            color: #e2e8f0;
        }
        .nav-btn.active {
            background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.15));
            color: #a5b4fc;
            border: 1px solid rgba(99,102,241,0.3);
        }
        .nav-btn .icon { font-size: 1.2rem; width: 1.5rem; text-align: center; }

        /* ── Section header ── */
        .section-header {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
        }
        .section-header .icon-box {
            width: 48px; height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            color: white;
        }
        .section-header h1 {
            font-size: 1.8rem;
            font-weight: 800;
            margin: 0;
            color: #f1f5f9;
        }
        .section-header p {
            font-size: 0.9rem;
            color: #64748b;
            margin: 0;
        }

        /* ── Status badges ── */
        .badge {
            display: inline-flex;
            align-items: center;
            padding: 0.2rem 0.65rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-active { background: rgba(16,185,129,0.15); color: #10b981; }
        .badge-inactive { background: rgba(244,63,94,0.15); color: #f43f5e; }
        .badge-admin { background: rgba(99,102,241,0.15); color: #a5b4fc; }
        .badge-staff { background: rgba(6,182,212,0.15); color: #67e8f9; }
        .badge-low { background: rgba(245,158,11,0.15); color: #f59e0b; }
        .badge-ok { background: rgba(16,185,129,0.15); color: #10b981; }
        .badge-critical { background: rgba(244,63,94,0.15); color: #f43f5e; }

        /* ── Permission toggle grid ── */
        .perm-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
            margin-top: 0.5rem;
        }
        .perm-item {
            text-align: center;
            padding: 0.4rem;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .perm-on { background: rgba(16,185,129,0.15); color: #10b981; }
        .perm-off { background: rgba(100,116,139,0.15); color: #64748b; }

        /* ── Alert box ── */
        .alert-box {
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }
        .alert-warning { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
        .alert-info { background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3); }
        .alert-success { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); }
        .alert-danger { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.3); }

        /* ── Login page ── */
        .login-container {
            max-width: 420px;
            margin: 4rem auto;
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid rgba(99,102,241,0.2);
            border-radius: 24px;
            padding: 3rem;
            box-shadow: 0 25px 60px rgba(0,0,0,0.5);
        }
        .login-logo {
            width: 72px; height: 72px;
            border-radius: 20px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            margin: 0 auto 1.5rem;
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }

        /* ── Hide default top bar ── */
        [data-testid="stHeader"] { background: rgba(15,23,42,0.9); }

        /* ── Form styling ── */
        .stTextInput > div > div > input, .stNumberInput > div > div > input,
        .stSelectbox > div > div > select, .stTextArea > div > div > textarea {
            border-radius: 10px !important;
        }

        /* ── Expander styling ── */
        .streamlit-expanderHeader {
            border-radius: 10px !important;
            font-weight: 600 !important;
        }

        /* ── Toast / success messages ── */
        .stSuccess, .stWarning, .stError, .stInfo {
            border-radius: 10px !important;
        }
    </style>
    """, unsafe_allow_html=True)