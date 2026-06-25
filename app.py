# import streamlit as st
# import sqlite3
# import hashlib
# import datetime
# import json
# import pandas as pd
# import plotly.express as px
# import plotly.graph_objects as go
# from functools import wraps
# from contextlib import contextmanager


# # ──────────────────────────────────────────────
# #  DATABASE SETUP
# # ──────────────────────────────────────────────

# DB_PATH = "inventory.db"

# @contextmanager
# def get_db():
#     conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
#     conn.row_factory = sqlite3.Row
#     try:
#         yield conn
#     finally:
#         conn.close()

# def init_database():
#     with get_db() as conn:
#         c = conn.cursor()

#         c.execute("""CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT UNIQUE NOT NULL,
#             password_hash TEXT NOT NULL,
#             full_name TEXT NOT NULL,
#             role TEXT DEFAULT 'staff',
#             is_active INTEGER DEFAULT 1,
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )""")

#         c.execute("""CREATE TABLE IF NOT EXISTS permissions (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER NOT NULL,
#             module TEXT NOT NULL,
#             can_view INTEGER DEFAULT 0,
#             can_add INTEGER DEFAULT 0,
#             can_edit INTEGER DEFAULT 0,
#             can_delete INTEGER DEFAULT 0,
#             FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
#             UNIQUE(user_id, module)
#         )""")

#         c.execute("""CREATE TABLE IF NOT EXISTS products (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             sku TEXT UNIQUE NOT NULL,
#             category TEXT DEFAULT 'General',
#             price REAL NOT NULL,
#             cost REAL NOT NULL,
#             quantity INTEGER DEFAULT 0,
#             min_stock INTEGER DEFAULT 10,
#             supplier TEXT DEFAULT '',
#             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )""")

#         c.execute("""CREATE TABLE IF NOT EXISTS sales (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             product_id INTEGER NOT NULL,
#             quantity INTEGER NOT NULL,
#             unit_price REAL NOT NULL,
#             total REAL NOT NULL,
#             sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             sold_by INTEGER NOT NULL,
#             customer_name TEXT DEFAULT 'Walk-in',
#             FOREIGN KEY(product_id) REFERENCES products(id),
#             FOREIGN KEY(sold_by) REFERENCES users(id)
#         )""")

#         c.execute("""CREATE TABLE IF NOT EXISTS purchases (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             product_id INTEGER NOT NULL,
#             quantity INTEGER NOT NULL,
#             unit_cost REAL NOT NULL,
#             total REAL NOT NULL,
#             purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             purchased_by INTEGER NOT NULL,
#             supplier TEXT DEFAULT '',
#             FOREIGN KEY(product_id) REFERENCES products(id),
#             FOREIGN KEY(purchased_by) REFERENCES users(id)
#         )""")

#         c.execute("""CREATE TABLE IF NOT EXISTS logs (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id INTEGER,
#             action TEXT NOT NULL,
#             module TEXT NOT NULL,
#             details TEXT DEFAULT '',
#             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY(user_id) REFERENCES users(id)
#         )""")

#         # Create default admin if not exists
#         c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
#         if c.fetchone()[0] == 0:
#             admin_hash = hash_password("admin123")
#             c.execute(
#                 "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
#                 ("admin", admin_hash, "System Administrator", "admin"),
#             )
#             # Give admin all permissions
#             admin_id = c.lastrowid
#             modules = ["dashboard", "sales", "products", "purchases", "logs", "reports", "staff_access"]
#             for mod in modules:
#                 c.execute(
#                     "INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)",
#                     (admin_id, mod, 1, 1, 1, 1),
#                 )

#         conn.commit()

# # ──────────────────────────────────────────────
# #  AUTHENTICATION & HELPERS
# # ──────────────────────────────────────────────

# def hash_password(password):
#     return hashlib.sha256(password.encode()).hexdigest()

# def verify_password(password, hashed):
#     return hash_password(password) == hashed

# def authenticate_user(username, password):
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
#         user = c.fetchone()
#         if user and verify_password(password, user["password_hash"]):
#             return dict(user)
#     return None

# def get_user_permissions(user_id):
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("SELECT * FROM permissions WHERE user_id=?", (user_id,))
#         rows = c.fetchall()
#         perms = {}
#         for row in rows:
#             perms[row["module"]] = {
#                 "can_view": bool(row["can_view"]),
#                 "can_add": bool(row["can_add"]),
#                 "can_edit": bool(row["can_edit"]),
#                 "can_delete": bool(row["can_delete"]),
#             }
#         return perms

# def add_log(user_id, action, module, details=""):
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute(
#             "INSERT INTO logs (user_id, action, module, details) VALUES (?,?,?,?)",
#             (user_id, action, module, details),
#         )
#         conn.commit()

# def get_all_users():
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("SELECT * FROM users ORDER BY created_at DESC")
#         return [dict(row) for row in c.fetchall()]

# def get_all_products():
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("SELECT * FROM products ORDER BY updated_at DESC")
#         return [dict(row) for row in c.fetchall()]

# def get_low_stock_products():
#     with get_db() as conn:
#         c = conn.cursor()
#         c.execute("SELECT * FROM products WHERE quantity <= min_stock ORDER BY quantity ASC")
#         return [dict(row) for row in c.fetchall()]

# # ──────────────────────────────────────────────
# #  PERMISSION DECORATOR
# # ──────────────────────────────────────────────

# def check_permission(module, action="can_view"):
#     """Check if current user has permission for a module/action."""
#     if "user" not in st.session_state:
#         return False
#     if st.session_state.user["role"] == "admin":
#         return True
#     perms = st.session_state.get("permissions", {})
#     mod_perms = perms.get(module, {})
#     return mod_perms.get(action, False)

# def require_permission(module, action="can_view"):
#     """Show access denied if permission missing."""
#     if not check_permission(module, action):
#         st.markdown("""
#         <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
#                     min-height:50vh;text-align:center;">
#             <div style="font-size:4rem;margin-bottom:0.5rem;">🔒</div>
#             <h2 style="color:#ef4444;margin:0;">Access Denied</h2>
#             <p style="color:#94a3b8;font-size:1.1rem;">You don't have permission to access this section.<br>
#             Contact your administrator to request access.</p>
#         </div>
#         """, unsafe_allow_html=True)
#         return False
#     return True

# # ──────────────────────────────────────────────
# #  CUSTOM CSS STYLING
# # ──────────────────────────────────────────────

# def load_custom_css():
#     st.markdown("""
#     <style>
#         /* ── Global ── */
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

#         .stApp {
#             font-family: 'Inter', sans-serif;
#         }

#         /* ── Sidebar ── */
#         [data-testid="stSidebar"] {
#             background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
#             border-right: 1px solid rgba(99,102,241,0.15);
#         }
#         [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }
#         [data-testid="stSidebarNav"] { display: none; }
#         section[data-testid="stSidebar"] > div:first-child {
#             padding-top: 1rem;
#         }

#         /* ── Main container ── */
#         .block-container {
#             padding-top: 2rem;
#             max-width: 1400px;
#         }

#         /* ── Metric cards ── */
#         .metric-card {
#             background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
#             border: 1px solid rgba(99,102,241,0.2);
#             border-radius: 16px;
#             padding: 1.5rem;
#             color: #f1f5f9;
#             transition: transform 0.2s, box-shadow 0.2s;
#             position: relative;
#             overflow: hidden;
#         }
#         .metric-card::before {
#             content: '';
#             position: absolute;
#             top: 0; left: 0;
#             width: 4px; height: 100%;
#             border-radius: 4px 0 0 4px;
#         }
#         .metric-card:hover {
#             transform: translateY(-2px);
#             box-shadow: 0 8px 30px rgba(99,102,241,0.15);
#         }
#         .metric-card .label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem; font-weight: 500; }
#         .metric-card .value { font-size: 2rem; font-weight: 800; line-height: 1.2; }
#         .metric-card .sub { font-size: 0.8rem; margin-top: 0.35rem; }

#         .mc-indigo::before { background: #6366f1; }
#         .mc-indigo .value { color: #a5b4fc; }

#         .mc-emerald::before { background: #10b981; }
#         .mc-emerald .value { color: #6ee7b7; }

#         .mc-amber::before { background: #f59e0b; }
#         .mc-amber .value { color: #fcd34d; }

#         .mc-rose::before { background: #f43f5e; }
#         .mc-rose .value { color: #fda4af; }

#         .mc-cyan::before { background: #06b6d4; }
#         .mc-cyan .value { color: #67e8f9; }

#         .mc-violet::before { background: #8b5cf6; }
#         .mc-violet .value { color: #c4b5fd; }

#         /* ── Table styling ── */
#         .dataframe {
#             border-radius: 12px !important;
#             overflow: hidden;
#             border: 1px solid #334155 !important;
#         }
#         .dataframe thead tr th {
#             background: #1e293b !important;
#             color: #a5b4fc !important;
#             font-weight: 600 !important;
#             padding: 0.75rem 1rem !important;
#             border-bottom: 2px solid #6366f1 !important;
#         }
#         .dataframe tbody tr td {
#             padding: 0.65rem 1rem !important;
#             border-bottom: 1px solid #1e293b !important;
#             color: #e2e8f0 !important;
#         }
#         .dataframe tbody tr:hover td {
#             background: rgba(99,102,241,0.08) !important;
#         }
#         .dataframe tbody tr:nth-child(even) td {
#             background: rgba(15,23,42,0.4);
#         }

#         /* ── Buttons ── */
#         .stButton > button {
#             border-radius: 10px !important;
#             font-weight: 600 !important;
#             transition: all 0.2s !important;
#         }
#         .stButton > button:hover {
#             transform: translateY(-1px) !important;
#             box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important;
#         }

#         /* ── Nav buttons in sidebar ── */
#         .nav-btn {
#             display: flex;
#             align-items: center;
#             gap: 0.75rem;
#             width: 100%;
#             padding: 0.75rem 1rem;
#             border-radius: 12px;
#             border: none;
#             background: transparent;
#             color: #94a3b8;
#             font-size: 0.95rem;
#             font-weight: 500;
#             cursor: pointer;
#             transition: all 0.2s;
#             text-align: left;
#             margin-bottom: 4px;
#         }
#         .nav-btn:hover {
#             background: rgba(99,102,241,0.12);
#             color: #e2e8f0;
#         }
#         .nav-btn.active {
#             background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.15));
#             color: #a5b4fc;
#             border: 1px solid rgba(99,102,241,0.3);
#         }
#         .nav-btn .icon { font-size: 1.2rem; width: 1.5rem; text-align: center; }

#         /* ── Section header ── */
#         .section-header {
#             display: flex;
#             align-items: center;
#             gap: 0.75rem;
#             margin-bottom: 1.5rem;
#         }
#         .section-header .icon-box {
#             width: 48px; height: 48px;
#             border-radius: 14px;
#             display: flex;
#             align-items: center;
#             justify-content: center;
#             font-size: 1.4rem;
#             background: linear-gradient(135deg, #6366f1, #8b5cf6);
#             color: white;
#         }
#         .section-header h1 {
#             font-size: 1.8rem;
#             font-weight: 800;
#             margin: 0;
#             color: #f1f5f9;
#         }
#         .section-header p {
#             font-size: 0.9rem;
#             color: #64748b;
#             margin: 0;
#         }

#         /* ── Status badges ── */
#         .badge {
#             display: inline-flex;
#             align-items: center;
#             padding: 0.2rem 0.65rem;
#             border-radius: 20px;
#             font-size: 0.75rem;
#             font-weight: 600;
#         }
#         .badge-active { background: rgba(16,185,129,0.15); color: #10b981; }
#         .badge-inactive { background: rgba(244,63,94,0.15); color: #f43f5e; }
#         .badge-admin { background: rgba(99,102,241,0.15); color: #a5b4fc; }
#         .badge-staff { background: rgba(6,182,212,0.15); color: #67e8f9; }
#         .badge-low { background: rgba(245,158,11,0.15); color: #f59e0b; }
#         .badge-ok { background: rgba(16,185,129,0.15); color: #10b981; }
#         .badge-critical { background: rgba(244,63,94,0.15); color: #f43f5e; }

#         /* ── Permission toggle grid ── */
#         .perm-grid {
#             display: grid;
#             grid-template-columns: repeat(4, 1fr);
#             gap: 0.5rem;
#             margin-top: 0.5rem;
#         }
#         .perm-item {
#             text-align: center;
#             padding: 0.4rem;
#             border-radius: 8px;
#             font-size: 0.75rem;
#             font-weight: 600;
#         }
#         .perm-on { background: rgba(16,185,129,0.15); color: #10b981; }
#         .perm-off { background: rgba(100,116,139,0.15); color: #64748b; }

#         /* ── Alert box ── */
#         .alert-box {
#             border-radius: 12px;
#             padding: 1rem 1.25rem;
#             margin-bottom: 1rem;
#             display: flex;
#             align-items: flex-start;
#             gap: 0.75rem;
#         }
#         .alert-warning { background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); }
#         .alert-info { background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3); }
#         .alert-success { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); }
#         .alert-danger { background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.3); }

#         /* ── Login page ── */
#         .login-container {
#             max-width: 420px;
#             margin: 4rem auto;
#             background: linear-gradient(135deg, #1e293b, #0f172a);
#             border: 1px solid rgba(99,102,241,0.2);
#             border-radius: 24px;
#             padding: 3rem;
#             box-shadow: 0 25px 60px rgba(0,0,0,0.5);
#         }
#         .login-logo {
#             width: 72px; height: 72px;
#             border-radius: 20px;
#             background: linear-gradient(135deg, #6366f1, #8b5cf6);
#             display: flex;
#             align-items: center;
#             justify-content: center;
#             font-size: 2rem;
#             margin: 0 auto 1.5rem;
#         }

#         /* ── Scrollbar ── */
#         ::-webkit-scrollbar { width: 6px; }
#         ::-webkit-scrollbar-track { background: transparent; }
#         ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
#         ::-webkit-scrollbar-thumb:hover { background: #475569; }

#         /* ── Hide default top bar ── */
#         [data-testid="stHeader"] { background: rgba(15,23,42,0.9); }

#         /* ── Form styling ── */
#         .stTextInput > div > div > input, .stNumberInput > div > div > input,
#         .stSelectbox > div > div > select, .stTextArea > div > div > textarea {
#             border-radius: 10px !important;
#         }

#         /* ── Expander styling ── */
#         .streamlit-expanderHeader {
#             border-radius: 10px !important;
#             font-weight: 600 !important;
#         }

#         /* ── Toast / success messages ── */
#         .stSuccess, .stWarning, .stError, .stInfo {
#             border-radius: 10px !important;
#         }
#     </style>
#     """, unsafe_allow_html=True)

# # ──────────────────────────────────────────────
# #  SIDEBAR NAVIGATION
# # ──────────────────────────────────────────────

# NAV_ITEMS = [
#     ("dashboard", "📊", "Dashboard"),
#     ("sales", "💰", "Sales"),
#     ("products", "📦", "Products"),
#     ("purchases", "🛒", "Purchases"),
#     ("logs", "📋", "Logs"),
#     ("reports", "📈", "Reports"),
#     ("staff_access", "👥", "Staff Access"),
# ]

# def render_sidebar():
#     with st.sidebar:
#         # Brand
#         st.markdown("""
#         <div style="text-align:center;padding:1rem 0 1.5rem;">
#             <div style="width:52px;height:52px;border-radius:16px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
#                         display:inline-flex;align-items:center;justify-content:center;font-size:1.5rem;margin-bottom:0.5rem;">🗄️</div>
#             <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9;">InvenTrack</div>
#             <div style="font-size:0.75rem;color:#64748b;">Inventory Management</div>
#         </div>
#         """, unsafe_allow_html=True)

#         st.markdown("<div style='height:1px;background:rgba(99,102,241,0.2);margin:0 0.5rem 1rem;'></div>", unsafe_allow_html=True)

#         # Navigation
#         for key, icon, label in NAV_ITEMS:
#             if key == "staff_access" and st.session_state.user["role"] != "admin":
#                 continue
#             if not check_permission(key, "can_view"):
#                 continue
#             is_active = st.session_state.get("current_page") == key
#             btn_class = "nav-btn active" if is_active else "nav-btn"
#             if st.button(
#                 f"{icon}  {label}",
#                 key=f"nav_{key}",
#                 use_container_width=True,
#             ):
#                 st.session_state.current_page = key
#                 st.rerun()

#         st.markdown("<div style='height:1px;background:rgba(99,102,241,0.2);margin:1.5rem 0.5rem 1rem;'></div>", unsafe_allow_html=True)

#         # User info
#         user = st.session_state.user
#         role_badge = "badge-admin" if user["role"] == "admin" else "badge-staff"
#         role_label = "Administrator" if user["role"] == "admin" else "Staff"
#         st.markdown(f"""
#         <div style="padding:0.75rem;border-radius:12px;background:rgba(30,41,59,0.6);border:1px solid rgba(99,102,241,0.1);">
#             <div style="display:flex;align-items:center;gap:0.75rem;">
#                 <div style="width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#6366f1,#8b5cf6);
#                             display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:1rem;">
#                     {user['full_name'][0].upper()}
#                 </div>
#                 <div>
#                     <div style="font-weight:600;color:#f1f5f9;font-size:0.9rem;">{user['full_name']}</div>
#                     <span class="badge {role_badge}">{role_label}</span>
#                 </div>
#             </div>
#         </div>
#         """, unsafe_allow_html=True)

#         if st.button("🚪  Sign Out", key="logout_btn", use_container_width=True):
#             for key in list(st.session_state.keys()):
#                 del st.session_state[key]
#             st.rerun()

# # ──────────────────────────────────────────────
# #  LOGIN PAGE
# # ──────────────────────────────────────────────

# def render_login():
#     st.markdown("""
#     <div class="login-container">
#         <div class="login-logo">🗄️</div>
#         <h1 style="text-align:center;color:#f1f5f9;font-size:1.8rem;font-weight:800;margin-bottom:0.25rem;">Welcome Back</h1>
#         <p style="text-align:center;color:#64748b;margin-bottom:2rem;">Sign in to InvenTrack</p>
#     </div>
#     """, unsafe_allow_html=True)

#     col1, col2, col3 = st.columns([1, 1.2, 1])
#     with col2:
#         username = st.text_input("Username", placeholder="Enter your username", key="login_user")
#         password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")

#         if st.button("🔐  Sign In", use_container_width=True, type="primary"):
#             if not username or not password:
#                 st.warning("Please enter both username and password.")
#             else:
#                 user = authenticate_user(username, password)
#                 if user:
#                     st.session_state.user = user
#                     st.session_state.permissions = get_user_permissions(user["id"])
#                     st.session_state.current_page = "dashboard"
#                     add_log(user["id"], "LOGIN", "auth", f"User {username} logged in")
#                     st.rerun()
#                 else:
#                     st.error("Invalid credentials or account is disabled.")

#         st.markdown("""
#         <div style="text-align:center;margin-top:1.5rem;color:#475569;font-size:0.8rem;">
#             Default admin: <strong style="color:#a5b4fc;">admin</strong> / <strong style="color:#a5b4fc;">admin123</strong>
#         </div>
#         """, unsafe_allow_html=True)

# # ──────────────────────────────────────────────
# #  DASHBOARD PAGE
# # ──────────────────────────────────────────────

# def render_dashboard():
#     if not require_permission("dashboard"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">📊</div>
#         <div>
#             <h1>Dashboard</h1>
#             <p>Real-time overview of your inventory</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # Metrics
#     with get_db() as conn:
#         c = conn.cursor()

#         c.execute("SELECT COUNT(*) FROM products")
#         total_products = c.fetchone()[0]

#         c.execute("SELECT COALESCE(SUM(quantity),0) FROM products")
#         total_stock = c.fetchone()[0]

#         c.execute("SELECT COUNT(*) FROM products WHERE quantity <= min_stock")
#         low_stock_count = c.fetchone()[0]

#         today = datetime.date.today()
#         c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)=?", (today.isoformat(),))
#         today_revenue = c.fetchone()[0]

#         month_start = today.replace(day=1).isoformat()
#         c.execute("SELECT COALESCE(SUM(total),0) FROM sales WHERE date(sale_date)>=?", (month_start,))
#         month_revenue = c.fetchone()[0]

#         c.execute("SELECT COALESCE(SUM(total),0) FROM sales")
#         total_revenue = c.fetchone()[0]

#     mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
#     metrics = [
#         (mc1, "mc-indigo", "📦", "Total Products", f"{total_products}", ""),
#         (mc2, "mc-emerald", "🗃️", "Total Stock", f"{total_stock:,}", "units"),
#         (mc3, "mc-amber", "⚠️", "Low Stock", f"{low_stock_count}", "items below minimum"),
#         (mc4, "mc-cyan", "💵", "Today's Sales", f"₹{today_revenue:,.2f}", ""),
#         (mc5, "mc-violet", "📅", "Monthly Revenue", f"₹{month_revenue:,.2f}", ""),
#         (mc6, "mc-rose", "🏆", "Total Revenue", f"₹{total_revenue:,.2f}", ""),
#     ]
#     for col, cls, icon, label, value, sub in metrics:
#         with col:
#             st.markdown(f"""
#             <div class="metric-card {cls}">
#                 <div class="label">{icon} {label}</div>
#                 <div class="value">{value}</div>
#                 <div class="sub">{sub}</div>
#             </div>
#             """, unsafe_allow_html=True)

#     st.markdown("---")

#     # Charts row
#     col_left, col_right = st.columns(2)

#     with col_left:
#         st.markdown("### 📊 Sales Last 30 Days")
#         with get_db() as conn:
#             df_sales = pd.read_sql_query("""
#                 SELECT date(sale_date) as date, SUM(total) as total
#                 FROM sales WHERE sale_date >= date('now', '-30 days')
#                 GROUP BY date(sale_date) ORDER BY date
#             """, conn)

#         if not df_sales.empty:
#             fig = px.bar(df_sales, x="date", y="total", color_discrete_sequence=["#6366f1"])
#             fig.update_layout(
#                 xaxis_title="Date", yaxis_title="Revenue (₹)",
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=320,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
#             )
#             fig.update_traces(marker_line_width=0, marker_cornerradius=6)
#             st.plotly_chart(fig, use_container_width=True)
#         else:
#             st.info("No sales data in the last 30 days.")

#     with col_right:
#         st.markdown("### 📦 Stock by Category")
#         with get_db() as conn:
#             df_cat = pd.read_sql_query("""
#                 SELECT category, SUM(quantity) as total_qty
#                 FROM products GROUP BY category ORDER BY total_qty DESC
#             """, conn)

#         if not df_cat.empty:
#             colors = ["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#06b6d4", "#8b5cf6"]
#             fig2 = px.pie(df_cat, names="category", values="total_qty",
#                          color_discrete_sequence=colors, hole=0.55)
#             fig2.update_layout(
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=320,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.15),
#             )
#             fig2.update_traces(textposition="inside", textinfo="percent+label")
#             st.plotly_chart(fig2, use_container_width=True)

#     # Low stock alert
#     low_stock = get_low_stock_products()
#     if low_stock:
#         st.markdown("---")
#         st.markdown("""
#         <div class="alert-box alert-warning">
#             <span style="font-size:1.3rem;">⚠️</span>
#             <div><strong>Low Stock Alert</strong> — The following items are at or below minimum stock levels:</div>
#         </div>
#         """, unsafe_allow_html=True)

#         low_df = pd.DataFrame(low_stock)[["name", "sku", "category", "quantity", "min_stock"]]
#         low_df["status"] = low_df.apply(
#             lambda r: "🔴 Critical" if r["quantity"] == 0 else "🟡 Low", axis=1
#         )
#         st.dataframe(low_df, use_container_width=True, hide_index=True)

#     # Recent activity
#     st.markdown("---")
#     st.markdown("### 🕐 Recent Activity")
#     with get_db() as conn:
#         df_logs = pd.read_sql_query("""
#             SELECT l.action, l.module, l.details, l.timestamp, u.full_name
#             FROM logs l LEFT JOIN users u ON l.user_id = u.id
#             ORDER BY l.timestamp DESC LIMIT 10
#         """, conn)
#     if not df_logs.empty:
#         for _, row in df_logs.iterrows():
#             action_colors = {
#                 "LOGIN": "#6366f1", "LOGOUT": "#64748b", "CREATE": "#10b981",
#                 "UPDATE": "#f59e0b", "DELETE": "#f43f5e", "VIEW": "#06b6d4"
#             }
#             color = action_colors.get(row["action"], "#64748b")
#             st.markdown(f"""
#             <div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;border-bottom:1px solid #1e293b;">
#                 <div style="width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0;"></div>
#                 <div style="flex:1;">
#                     <span style="color:#e2e8f0;font-weight:600;font-size:0.9rem;">{row['full_name']}</span>
#                     <span style="color:#94a3b8;font-size:0.85rem;"> {row['action']} on {row['module']}</span>
#                     <span style="color:#64748b;font-size:0.8rem;"> — {row['details'][:60]}</span>
#                 </div>
#                 <div style="color:#475569;font-size:0.75rem;white-space:nowrap;">{str(row['timestamp'])[:16]}</div>
#             </div>
#             """, unsafe_allow_html=True)
#     else:
#         st.info("No recent activity.")

# # ──────────────────────────────────────────────
# #  PRODUCTS PAGE
# # ──────────────────────────────────────────────

# def render_products():
#     if not require_permission("products"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">📦</div>
#         <div>
#             <h1>Products</h1>
#             <p>Manage your product inventory</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # Action bar
#     col_search, col_cat, col_btn = st.columns([3, 2, 1])
#     with col_search:
#         search = st.text_input("🔍 Search", placeholder="Search by name or SKU...", key="prod_search")
#     with col_cat:
#         categories = ["All"] + list(set(p["category"] for p in get_all_products()))
#         cat_filter = st.selectbox("Category", categories, key="prod_cat_filter")
#     with col_btn:
#         st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
#         if check_permission("products", "can_add"):
#             if st.button("➕ Add Product", type="primary", use_container_width=True):
#                 st.session_state.show_add_product = True

#     # Add Product Form
#     if st.session_state.get("show_add_product", False):
#         with st.expander("➕ New Product", expanded=True):
#             with st.form("add_product_form"):
#                 c1, c2, c3 = st.columns(3)
#                 with c1:
#                     pname = st.text_input("Product Name *")
#                     psku = st.text_input("SKU *")
#                 with c2:
#                     pcategory = st.text_input("Category", value="General")
#                     psupplier = st.text_input("Supplier")
#                 with c3:
#                     pprice = st.number_input("Selling Price (₹) *", min_value=0.01, step=0.01, format="%.2f")
#                     pcost = st.number_input("Cost Price (₹) *", min_value=0.01, step=0.01, format="%.2f")
#                 c4, c5 = st.columns(2)
#                 with c4:
#                     pquantity = st.number_input("Quantity", min_value=0, step=1)
#                 with c5:
#                     pmin_stock = st.number_input("Min Stock Level", min_value=0, value=10, step=1)

#                 submitted = st.form_submit_button("✅ Create Product", use_container_width=True)
#                 if submitted:
#                     if not pname or not psku:
#                         st.error("Name and SKU are required.")
#                     else:
#                         try:
#                             with get_db() as conn:
#                                 c = conn.cursor()
#                                 c.execute(
#                                     """INSERT INTO products (name, sku, category, price, cost, quantity, min_stock, supplier)
#                                        VALUES (?,?,?,?,?,?,?,?)""",
#                                     (pname, psku, pcategory, pprice, pcost, pquantity, pmin_stock, psupplier),
#                                 )
#                                 conn.commit()
#                             add_log(st.session_state.user["id"], "CREATE", "products", f"Added product: {pname} ({psku})")
#                             st.success(f"Product '{pname}' created successfully!")
#                             st.session_state.show_add_product = False
#                             st.rerun()
#                         except sqlite3.IntegrityError:
#                             st.error(f"SKU '{psku}' already exists!")

#                 # Cancel button OUTSIDE the form
#                 if st.button("Cancel"):
#                     st.session_state.show_add_product = False
#                     st.rerun()

#     # Products table
#     products = get_all_products()
#     if search:
#         search_lower = search.lower()
#         products = [p for p in products if search_lower in p["name"].lower() or search_lower in p["sku"].lower()]
#     if cat_filter != "All":
#         products = [p for p in products if p["category"] == cat_filter]

#     if products:
#         df = pd.DataFrame(products)
#         display_cols = ["id", "name", "sku", "category", "price", "cost", "quantity", "min_stock", "supplier"]
#         df_display = df[display_cols].copy()
#         df_display["price"] = df_display["price"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["cost"] = df_display["cost"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["status"] = df.apply(
#             lambda r: "🔴 Out" if r["quantity"] == 0 else ("🟡 Low" if r["quantity"] <= r["min_stock"] else "🟢 OK"), axis=1
#         )
#         df_display["margin"] = df.apply(
#             lambda r: f"{((r['price'] - r['cost']) / r['price'] * 100):.1f}%" if r['price'] > 0 else "0%", axis=1
#         )

#         st.dataframe(df_display, use_container_width=True, hide_index=True)

#         # Edit/Delete
#         if check_permission("products", "can_edit") or check_permission("products", "can_delete"):
#             st.markdown("---")
#             st.markdown("### ✏️ Manage Product")
#             col_sel, col_act = st.columns([1, 2])
#             with col_sel:
#                 prod_names = {f"{p['name']} ({p['sku']})": p["id"] for p in get_all_products()}
#                 selected_prod = st.selectbox("Select Product", list(prod_names.keys()), key="prod_select")
#                 selected_id = prod_names[selected_prod]

#             with get_db() as conn:
#                 c = conn.cursor()
#                 c.execute("SELECT * FROM products WHERE id=?", (selected_id,))
#                 prod = dict(c.fetchone())

#             tab_edit, tab_del = st.tabs(["✏️ Edit", "🗑️ Delete"])

#             with tab_edit:
#                 if check_permission("products", "can_edit"):
#                     with st.form("edit_product_form"):
#                         ec1, ec2, ec3 = st.columns(3)
#                         with ec1:
#                             ename = st.text_input("Name", value=prod["name"])
#                             esku = st.text_input("SKU", value=prod["sku"])
#                         with ec2:
#                             ecategory = st.text_input("Category", value=prod["category"])
#                             esupplier = st.text_input("Supplier", value=prod["supplier"])
#                         with ec3:
#                             eprice = st.number_input("Price (₹)", value=prod["price"], min_value=0.01, step=0.01, format="%.2f")
#                             ecost = st.number_input("Cost (₹)", value=prod["cost"], min_value=0.01, step=0.01, format="%.2f")
#                         ec4, ec5 = st.columns(2)
#                         with ec4:
#                             equantity = st.number_input("Quantity", value=prod["quantity"], min_value=0, step=1)
#                         with ec5:
#                             emin_stock = st.number_input("Min Stock", value=prod["min_stock"], min_value=0, step=1)

#                         if st.form_submit_button("💾 Save Changes", use_container_width=True):
#                             with get_db() as conn:
#                                 c = conn.cursor()
#                                 c.execute(
#                                     """UPDATE products SET name=?, sku=?, category=?, price=?, cost=?,
#                                        quantity=?, min_stock=?, supplier=?, updated_at=CURRENT_TIMESTAMP
#                                        WHERE id=?""",
#                                     (ename, esku, ecategory, eprice, ecost, equantity, emin_stock, esupplier, selected_id),
#                                 )
#                                 conn.commit()
#                             add_log(st.session_state.user["id"], "UPDATE", "products",
#                                     f"Updated product: {ename} ({esku})")
#                             st.success("Product updated!")
#                             st.rerun()
#                 else:
#                     st.warning("You don't have edit permission.")

#             with tab_del:
#                 if check_permission("products", "can_delete"):
#                     st.warning(f"⚠️ Are you sure you want to delete **{prod['name']}**? This action cannot be undone.")
#                     if st.button("🗑️ Delete Product", type="primary"):
#                         with get_db() as conn:
#                             c = conn.cursor()
#                             c.execute("DELETE FROM products WHERE id=?", (selected_id,))
#                             conn.commit()
#                         add_log(st.session_state.user["id"], "DELETE", "products",
#                                 f"Deleted product: {prod['name']} ({prod['sku']})")
#                         st.success("Product deleted!")
#                         st.rerun()
#                 else:
#                     st.warning("You don't have delete permission.")
#     else:
#         st.info("No products found. Add your first product above!")

# # ──────────────────────────────────────────────
# #  SALES PAGE
# # ──────────────────────────────────────────────

# def render_sales():
#     if not require_permission("sales"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">💰</div>
#         <div>
#             <h1>Sales</h1>
#             <p>Record and manage sales transactions</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # New Sale
#     if check_permission("sales", "can_add"):
#         with st.expander("➕ Record New Sale", expanded=False):
#             with st.form("new_sale_form"):
#                 products = get_all_products()
#                 available = [p for p in products if p["quantity"] > 0]

#                 if not available:
#                     st.warning("No products in stock to sell.")
#                 else:
#                     sc1, sc2, sc3 = st.columns(3)
#                     with sc1:
#                         prod_options = {f"{p['name']} ({p['sku']}) — Stock: {p['quantity']}": p for p in available}
#                         sale_prod = st.selectbox("Product *", list(prod_options.keys()))
#                         selected_p = prod_options[sale_prod]
#                     with sc2:
#                         max_qty = selected_p["quantity"]
#                         sale_qty = st.number_input("Quantity *", min_value=1, max_value=max_qty, value=1, step=1)
#                     with sc3:
#                         sale_price = st.number_input("Unit Price (₹)", value=selected_p["price"], min_value=0.01, step=0.01, format="%.2f")
#                         sale_customer = st.text_input("Customer", value="Walk-in")

#                     total = sale_qty * sale_price
#                     st.markdown(f"### 💵 Total: **₹{total:,.2f}**")

#                     if st.form_submit_button("✅ Complete Sale", use_container_width=True):
#                         with get_db() as conn:
#                             c = conn.cursor()
#                             c.execute(
#                                 """INSERT INTO sales (product_id, quantity, unit_price, total, sold_by, customer_name)
#                                    VALUES (?,?,?,?,?,?)""",
#                                 (selected_p["id"], sale_qty, sale_price, total, st.session_state.user["id"], sale_customer),
#                             )
#                             c.execute(
#                                 "UPDATE products SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
#                                 (sale_qty, selected_p["id"]),
#                             )
#                             conn.commit()
#                         add_log(st.session_state.user["id"], "CREATE", "sales",
#                                 f"Sold {sale_qty}x {selected_p['name']} to {sale_customer} for ₹{total:.2f}")
#                         st.success(f"Sale recorded! ₹{total:,.2f}")
#                         st.rerun()

#     # Sales table
#     st.markdown("### 📋 Sales History")

#     filter_col1, filter_col2 = st.columns(2)
#     with filter_col1:
#         date_from = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30), key="sales_from")
#     with filter_col2:
#         date_to = st.date_input("To", value=datetime.date.today(), key="sales_to")

#     with get_db() as conn:
#         df_sales = pd.read_sql_query("""
#             SELECT s.id, p.name as product, p.sku, s.quantity, s.unit_price, s.total,
#                    s.customer_name, s.sale_date, u.full_name as sold_by_name
#             FROM sales s
#             JOIN products p ON s.product_id = p.id
#             LEFT JOIN users u ON s.sold_by = u.id
#             WHERE date(s.sale_date) BETWEEN ? AND ?
#             ORDER BY s.sale_date DESC
#         """, conn, params=(date_from.isoformat(), date_to.isoformat()))

#     if not df_sales.empty:
#         total_sales = df_sales["total"].sum()
#         total_items = df_sales["quantity"].sum()

#         sm1, sm2, sm3 = st.columns(3)
#         with sm1:
#             st.metric("Total Revenue", f"₹{total_sales:,.2f}")
#         with sm2:
#             st.metric("Items Sold", f"{total_items:,}")
#         with sm3:
#             st.metric("Transactions", f"{len(df_sales)}")

#         df_display = df_sales.copy()
#         df_display["unit_price"] = df_display["unit_price"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["total"] = df_display["total"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["sale_date"] = df_display["sale_date"].apply(lambda x: str(x)[:16])

#         st.dataframe(df_display, use_container_width=True, hide_index=True)

#         # Delete sale
#         if check_permission("sales", "can_delete"):
#             with st.expander("🗑️ Delete Sale Record"):
#                 sale_id = st.number_input("Sale ID to Delete", min_value=1, step=1, key="del_sale_id")
#                 if st.button("Delete Sale"):
#                     with get_db() as conn:
#                         c = conn.cursor()
#                         c.execute("SELECT * FROM sales WHERE id=?", (sale_id,))
#                         sale = c.fetchone()
#                         if sale:
#                             c.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?",
#                                       (sale["quantity"], sale["product_id"]))
#                             c.execute("DELETE FROM sales WHERE id=?", (sale_id,))
#                             conn.commit()
#                             add_log(st.session_state.user["id"], "DELETE", "sales", f"Deleted sale #{sale_id}")
#                             st.success("Sale deleted and stock restored!")
#                             st.rerun()
#                         else:
#                             st.error("Sale ID not found.")
#     else:
#         st.info("No sales in the selected date range.")

# # ──────────────────────────────────────────────
# #  PURCHASES PAGE
# # ──────────────────────────────────────────────

# def render_purchases():
#     if not require_permission("purchases"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">🛒</div>
#         <div>
#             <h1>Purchases</h1>
#             <p>Track incoming inventory purchases</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # New Purchase
#     if check_permission("purchases", "can_add"):
#         with st.expander("➕ Record New Purchase", expanded=False):
#             with st.form("new_purchase_form"):
#                 products = get_all_products()

#                 if not products:
#                     st.warning("No products available. Add products first from the Products page.")
#                 else:
#                     pc1, pc2, pc3 = st.columns(3)
#                     with pc1:
#                         prod_options = {f"{p['name']} ({p['sku']})": p for p in products}
#                         pur_prod = st.selectbox("Product *", list(prod_options.keys()))
#                         selected_p = prod_options[pur_prod]
#                     with pc2:
#                         pur_qty = st.number_input("Quantity *", min_value=1, value=1, step=1)
#                         pur_cost = st.number_input("Unit Cost (₹) *", value=selected_p["cost"], min_value=0.01, step=0.01, format="%.2f")
#                     with pc3:
#                         pur_supplier = st.text_input("Supplier", value=selected_p.get("supplier", ""))

#                     total = pur_qty * pur_cost
#                     st.markdown(f"### 💰 Total Cost: **₹{total:,.2f}**")

#                     if st.form_submit_button("✅ Record Purchase", use_container_width=True):
#                         with get_db() as conn:
#                             c = conn.cursor()
#                             c.execute(
#                                 """INSERT INTO purchases (product_id, quantity, unit_cost, total, purchased_by, supplier)
#                                    VALUES (?,?,?,?,?,?)""",
#                                 (selected_p["id"], pur_qty, pur_cost, total, st.session_state.user["id"], pur_supplier),
#                             )
#                             c.execute(
#                                 "UPDATE products SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
#                                 (pur_qty, selected_p["id"]),
#                             )
#                             conn.commit()
#                         add_log(st.session_state.user["id"], "CREATE", "purchases",
#                                 f"Purchased {pur_qty}x {selected_p['name']} from {pur_supplier} for ₹{total:.2f}")
#                         st.success(f"Purchase recorded! ₹{total:,.2f}")
#                         st.rerun()

#     # Purchases table
#     st.markdown("### 📋 Purchase History")

#     filter_col1, filter_col2 = st.columns(2)
#     with filter_col1:
#         date_from = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30), key="pur_from")
#     with filter_col2:
#         date_to = st.date_input("To", value=datetime.date.today(), key="pur_to")

#     with get_db() as conn:
#         df_pur = pd.read_sql_query("""
#             SELECT pu.id, p.name as product, p.sku, pu.quantity, pu.unit_cost, pu.total,
#                    pu.supplier, pu.purchase_date, u.full_name as purchased_by_name
#             FROM purchases pu
#             JOIN products p ON pu.product_id = p.id
#             LEFT JOIN users u ON pu.purchased_by = u.id
#             WHERE date(pu.purchase_date) BETWEEN ? AND ?
#             ORDER BY pu.purchase_date DESC
#         """, conn, params=(date_from.isoformat(), date_to.isoformat()))

#     if not df_pur.empty:
#         total_cost = df_pur["total"].sum()
#         total_items = df_pur["quantity"].sum()

#         pm1, pm2, pm3 = st.columns(3)
#         with pm1:
#             st.metric("Total Purchases", f"₹{total_cost:,.2f}")
#         with pm2:
#             st.metric("Items Received", f"{total_items:,}")
#         with pm3:
#             st.metric("Purchase Orders", f"{len(df_pur)}")

#         df_display = df_pur.copy()
#         df_display["unit_cost"] = df_display["unit_cost"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["total"] = df_display["total"].apply(lambda x: f"₹{x:,.2f}")
#         df_display["purchase_date"] = df_display["purchase_date"].apply(lambda x: str(x)[:16])

#         st.dataframe(df_display, use_container_width=True, hide_index=True)
#     else:
#         st.info("No purchases in the selected date range.")

# # ──────────────────────────────────────────────
# #  LOGS PAGE
# # ──────────────────────────────────────────────

# def render_logs():
#     if not require_permission("logs"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">📋</div>
#         <div>
#             <h1>Activity Logs</h1>
#             <p>Track all system activities and changes</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     # Filters
#     fc1, fc2, fc3, fc4 = st.columns(4)
#     with fc1:
#         log_user = st.selectbox("User", ["All"] + [u["full_name"] for u in get_all_users()], key="log_user")
#     with fc2:
#         log_action = st.selectbox("Action", ["All", "LOGIN", "LOGOUT", "CREATE", "UPDATE", "DELETE", "VIEW"], key="log_action")
#     with fc3:
#         log_module = st.selectbox("Module", ["All", "auth", "products", "sales", "purchases", "staff", "reports"], key="log_module")
#     with fc4:
#         log_limit = st.selectbox("Show", [50, 100, 200, 500], index=1, key="log_limit")

#     query = """
#         SELECT l.id, u.full_name as user, l.action, l.module, l.details, l.timestamp
#         FROM logs l LEFT JOIN users u ON l.user_id = u.id
#         WHERE 1=1
#     """
#     params = []

#     if log_user != "All":
#         query += " AND u.full_name = ?"
#         params.append(log_user)
#     if log_action != "All":
#         query += " AND l.action = ?"
#         params.append(log_action)
#     if log_module != "All":
#         query += " AND l.module = ?"
#         params.append(log_module)

#     query += f" ORDER BY l.timestamp DESC LIMIT {log_limit}"

#     with get_db() as conn:
#         df_logs = pd.read_sql_query(query, conn, params=params)

#     if not df_logs.empty:
#         # Color code actions
#         action_colors = {
#             "LOGIN": "#6366f1", "LOGOUT": "#64748b", "CREATE": "#10b981",
#             "UPDATE": "#f59e0b", "DELETE": "#f43f5e", "VIEW": "#06b6d4"
#         }

#         for _, row in df_logs.iterrows():
#             color = action_colors.get(row["action"], "#64748b")
#             st.markdown(f"""
#             <div style="display:flex;align-items:center;gap:0.75rem;padding:0.6rem 0;border-bottom:1px solid #1e293b;">
#                 <div style="min-width:6px;height:6px;border-radius:50%;background:{color};"></div>
#                 <div style="min-width:60px;font-size:0.75rem;color:#64748b;">#{row['id']}</div>
#                 <div style="min-width:120px;font-weight:600;color:#e2e8f0;font-size:0.9rem;">{row['user'] or 'System'}</div>
#                 <div style="min-width:80px;">
#                     <span style="background:{color}22;color:{color};padding:0.15rem 0.6rem;border-radius:12px;font-size:0.75rem;font-weight:600;">
#                         {row['action']}
#                     </span>
#                 </div>
#                 <div style="min-width:80px;font-size:0.8rem;color:#94a3b8;">{row['module']}</div>
#                 <div style="flex:1;font-size:0.85rem;color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
#                     {row['details'][:80]}
#                 </div>
#                 <div style="font-size:0.75rem;color:#475569;white-space:nowrap;">{str(row['timestamp'])[:16]}</div>
#             </div>
#             """, unsafe_allow_html=True)

#         st.markdown(f"<div style='text-align:center;color:#64748b;padding:1rem;font-size:0.85rem;'>"
#                     f"Showing {len(df_logs)} log entries</div>", unsafe_allow_html=True)
#     else:
#         st.info("No log entries match your filters.")

# # ──────────────────────────────────────────────
# #  REPORTS PAGE
# # ──────────────────────────────────────────────

# def render_reports():
#     if not require_permission("reports"):
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">📈</div>
#         <div>
#             <h1>Reports</h1>
#             <p>Detailed analytics and reporting</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     report_tabs = st.tabs(["💰 Revenue", "📦 Inventory", "🏆 Top Products", "📊 Sales Trend"])

#     with report_tabs[0]:
#         st.markdown("### 💰 Revenue Analysis")

#         rc1, rc2 = st.columns(2)
#         with rc1:
#             rev_period = st.selectbox("Period", ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year", "All Time"], key="rev_period")
#         with rc2:
#             period_map = {
#                 "Last 7 Days": "7 days", "Last 30 Days": "30 days",
#                 "Last 90 Days": "90 days", "This Year": "365 days", "All Time": "10000 days"
#             }
#             period_days = period_map[rev_period]

#         with get_db() as conn:
#             df_rev = pd.read_sql_query(f"""
#                 SELECT date(sale_date) as date,
#                        COUNT(*) as transactions,
#                        SUM(quantity) as items,
#                        SUM(total) as revenue
#                 FROM sales
#                 WHERE sale_date >= date('now', '-{period_days}')
#                 GROUP BY date(sale_date)
#                 ORDER BY date
#             """, conn)

#         if not df_rev.empty:
#             total_rev = df_rev["revenue"].sum()
#             avg_daily = df_rev["revenue"].mean()
#             best_day = df_rev.loc[df_rev["revenue"].idxmax()]

#             rm1, rm2, rm3 = st.columns(3)
#             with rm1:
#                 st.metric("Total Revenue", f"₹{total_rev:,.2f}")
#             with rm2:
#                 st.metric("Daily Average", f"₹{avg_daily:,.2f}")
#             with rm3:
#                 st.metric("Best Day", f"₹{best_day['revenue']:,.2f}", f"{best_day['date']}")

#             fig = px.area(df_rev, x="date", y="revenue", color_discrete_sequence=["#6366f1"])
#             fig.update_layout(
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=350,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
#             )
#             fig.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.1)")
#             st.plotly_chart(fig, use_container_width=True)
#         else:
#             st.info("No revenue data for the selected period.")

#     with report_tabs[1]:
#         st.markdown("### 📦 Inventory Valuation")

#         with get_db() as conn:
#             df_inv = pd.read_sql_query("""
#                 SELECT category,
#                        COUNT(*) as product_count,
#                        SUM(quantity) as total_units,
#                        SUM(quantity * cost) as stock_value,
#                        SUM(quantity * price) as retail_value,
#                        AVG((price - cost) / price * 100) as avg_margin
#                 FROM products
#                 GROUP BY category
#             """, conn)

#         if not df_inv.empty:
#             total_stock_val = df_inv["stock_value"].sum()
#             total_retail_val = df_inv["retail_value"].sum()

#             iv1, iv2 = st.columns(2)
#             with iv1:
#                 st.metric("Total Stock Value (Cost)", f"₹{total_stock_val:,.2f}")
#             with iv2:
#                 st.metric("Total Retail Value", f"₹{total_retail_val:,.2f}")

#             fig_inv = px.bar(df_inv, x="category", y=["stock_value", "retail_value"],
#                             barmode="group", color_discrete_sequence=["#6366f1", "#10b981"])
#             fig_inv.update_layout(
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=350,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
#             )
#             st.plotly_chart(fig_inv, use_container_width=True)

#             df_inv_display = df_inv.copy()
#             df_inv_display["stock_value"] = df_inv_display["stock_value"].apply(lambda x: f"₹{x:,.2f}")
#             df_inv_display["retail_value"] = df_inv_display["retail_value"].apply(lambda x: f"₹{x:,.2f}")
#             df_inv_display["avg_margin"] = df_inv_display["avg_margin"].apply(lambda x: f"{x:.1f}%")
#             st.dataframe(df_inv_display, use_container_width=True, hide_index=True)
#         else:
#             st.info("No inventory data available. Add products first.")

#     with report_tabs[2]:
#         st.markdown("### 🏆 Top Selling Products")

#         with get_db() as conn:
#             df_top = pd.read_sql_query("""
#                 SELECT p.name, p.sku, p.category,
#                        SUM(s.quantity) as total_sold,
#                        SUM(s.total) as total_revenue,
#                        AVG(s.unit_price) as avg_price
#                 FROM sales s
#                 JOIN products p ON s.product_id = p.id
#                 GROUP BY s.product_id
#                 ORDER BY total_revenue DESC
#                 LIMIT 15
#             """, conn)

#         if not df_top.empty:
#             fig_top = px.bar(df_top, x="name", y="total_revenue",
#                             color="category", color_discrete_sequence=["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#06b6d4"])
#             fig_top.update_layout(
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=400,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 xaxis=dict(gridcolor="#1e293b", tickangle=-30), yaxis=dict(gridcolor="#1e293b"),
#             )
#             fig_top.update_traces(marker_line_width=0, marker_cornerradius=6)
#             st.plotly_chart(fig_top, use_container_width=True)

#             df_top_display = df_top.copy()
#             df_top_display["total_revenue"] = df_top_display["total_revenue"].apply(lambda x: f"₹{x:,.2f}")
#             df_top_display["avg_price"] = df_top_display["avg_price"].apply(lambda x: f"₹{x:,.2f}")
#             st.dataframe(df_top_display, use_container_width=True, hide_index=True)
#         else:
#             st.info("No sales data available.")

#     with report_tabs[3]:
#         st.markdown("### 📊 Sales Trend & Forecast")

#         with get_db() as conn:
#             df_trend = pd.read_sql_query("""
#                 SELECT date(sale_date) as date, SUM(total) as revenue, COUNT(*) as orders
#                 FROM sales
#                 WHERE sale_date >= date('now', '-90 days')
#                 GROUP BY date(sale_date)
#                 ORDER BY date
#             """, conn)

#         if not df_trend.empty and len(df_trend) > 3:
#             df_trend["date"] = pd.to_datetime(df_trend["date"])
#             df_trend["rolling_avg"] = df_trend["revenue"].rolling(window=7, min_periods=1).mean()

#             fig_trend = go.Figure()
#             fig_trend.add_trace(go.Scatter(
#                 x=df_trend["date"], y=df_trend["revenue"],
#                 mode="lines", name="Daily Revenue",
#                 line=dict(color="#6366f1", width=1.5), opacity=0.6
#             ))
#             fig_trend.add_trace(go.Scatter(
#                 x=df_trend["date"], y=df_trend["rolling_avg"],
#                 mode="lines", name="7-Day Average",
#                 line=dict(color="#f59e0b", width=2.5)
#             ))
#             fig_trend.update_layout(
#                 plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
#                 font_color="#94a3b8", height=400,
#                 margin=dict(l=10, r=10, t=10, b=10),
#                 xaxis=dict(gridcolor="#1e293b"), yaxis=dict(gridcolor="#1e293b"),
#                 legend=dict(orientation="h", yanchor="bottom", y=1.02),
#             )
#             st.plotly_chart(fig_trend, use_container_width=True)
#         else:
#             st.info("Need at least a few days of sales data to show trends.")

# # ──────────────────────────────────────────────
# #  STAFF ACCESS PAGE (ADMIN ONLY)
# # ──────────────────────────────────────────────

# def render_staff_access():
#     if not require_permission("staff_access"):
#         return

#     user = st.session_state.user
#     if user["role"] != "admin":
#         st.error("Only administrators can access this section.")
#         return

#     st.markdown("""
#     <div class="section-header">
#         <div class="icon-box">👥</div>
#         <div>
#             <h1>Staff Access</h1>
#             <p>Manage users, roles, and permissions</p>
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     staff_tabs = st.tabs(["👥 Users", "🔑 Permissions", "➕ Add User"])

#     # ── Users Tab ──
#     with staff_tabs[0]:
#         users = get_all_users()
#         for u in users:
#             role_cls = "badge-admin" if u["role"] == "admin" else "badge-staff"
#             role_label = "Administrator" if u["role"] == "admin" else "Staff"
#             status_cls = "badge-active" if u["is_active"] else "badge-inactive"
#             status_label = "Active" if u["is_active"] else "Disabled"

#             with st.expander(f"{'🛡️' if u['role'] == 'admin' else '👤'} {u['full_name']} (@{u['username']})"):
#                 uc1, uc2, uc3, uc4 = st.columns(4)
#                 with uc1:
#                     st.markdown(f"**Email/Username:** {u['username']}")
#                 with uc2:
#                     st.markdown(f"**Role:** <span class='badge {role_cls}'>{role_label}</span>", unsafe_allow_html=True)
#                 with uc3:
#                     st.markdown(f"**Status:** <span class='badge {status_cls}'>{status_label}</span>", unsafe_allow_html=True)
#                 with uc4:
#                     st.markdown(f"**Joined:** {str(u['created_at'])[:10]}")

#                 # Quick actions
#                 if u["username"] != "admin":
#                     ac1, ac2, ac3 = st.columns(3)
#                     with ac1:
#                         if u["is_active"]:
#                             if st.button("🚫 Disable", key=f"disable_{u['id']}", use_container_width=True):
#                                 with get_db() as conn:
#                                     c = conn.cursor()
#                                     c.execute("UPDATE users SET is_active=0 WHERE id=?", (u["id"],))
#                                     conn.commit()
#                                 add_log(user["id"], "UPDATE", "staff", f"Disabled user: {u['username']}")
#                                 st.success("User disabled.")
#                                 st.rerun()
#                         else:
#                             if st.button("✅ Enable", key=f"enable_{u['id']}", use_container_width=True):
#                                 with get_db() as conn:
#                                     c = conn.cursor()
#                                     c.execute("UPDATE users SET is_active=1 WHERE id=?", (u["id"],))
#                                     conn.commit()
#                                 add_log(user["id"], "UPDATE", "staff", f"Enabled user: {u['username']}")
#                                 st.success("User enabled.")
#                                 st.rerun()
#                     with ac2:
#                         new_role = "staff" if u["role"] == "admin" else "admin"
#                         if st.button(f"🔄 Make {new_role.title()}", key=f"role_{u['id']}", use_container_width=True):
#                             with get_db() as conn:
#                                 c = conn.cursor()
#                                 c.execute("UPDATE users SET role=? WHERE id=?", (new_role, u["id"]))
#                                 if new_role == "admin":
#                                     modules = ["dashboard", "sales", "products", "purchases", "logs", "reports", "staff_access"]
#                                     for mod in modules:
#                                         c.execute(
#                                             "INSERT OR REPLACE INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)",
#                                             (u["id"], mod, 1, 1, 1, 1),
#                                         )
#                                 conn.commit()
#                             add_log(user["id"], "UPDATE", "staff", f"Changed {u['username']} role to {new_role}")
#                             st.success(f"Role changed to {new_role}.")
#                             st.rerun()
#                     with ac3:
#                         if st.button("🗑️ Delete", key=f"del_{u['id']}", use_container_width=True):
#                             with get_db() as conn:
#                                 c = conn.cursor()
#                                 c.execute("DELETE FROM permissions WHERE user_id=?", (u["id"],))
#                                 c.execute("DELETE FROM users WHERE id=?", (u["id"],))
#                                 conn.commit()
#                             add_log(user["id"], "DELETE", "staff", f"Deleted user: {u['username']}")
#                             st.success("User deleted.")
#                             st.rerun()

#                 # Show current permissions
#                 perms = get_user_permissions(u["id"])
#                 if perms:
#                     st.markdown("**Current Permissions:**")
#                     perm_cols = st.columns(min(len(perms), 4))
#                     for idx, (mod, p) in enumerate(perms.items()):
#                         with perm_cols[idx % len(perm_cols)]:
#                             mod_label = mod.replace("_", " ").title()
#                             st.markdown(f"""
#                             <div style="background:rgba(30,41,59,0.6);border-radius:10px;padding:0.75rem;border:1px solid rgba(99,102,241,0.1);margin-bottom:0.5rem;">
#                                 <div style="font-weight:600;color:#e2e8f0;font-size:0.85rem;margin-bottom:0.5rem;">📂 {mod_label}</div>
#                                 <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
#                                     <span class="perm-item {'perm-on' if p['can_view'] else 'perm-off'}">👁️ View</span>
#                                     <span class="perm-item {'perm-on' if p['can_add'] else 'perm-off'}">➕ Add</span>
#                                     <span class="perm-item {'perm-on' if p['can_edit'] else 'perm-off'}">✏️ Edit</span>
#                                     <span class="perm-item {'perm-on' if p['can_delete'] else 'perm-off'}">🗑️ Delete</span>
#                                 </div>
#                             </div>
#                             """, unsafe_allow_html=True)

#     # ── Permissions Tab ──
#     with staff_tabs[1]:
#         st.markdown("### 🔑 Manage Permissions")
#         staff_users = [u for u in get_all_users() if u["role"] != "admin"]

#         if not staff_users:
#             st.info("No staff users to manage. Add one first.")
#         else:
#             perm_user = st.selectbox(
#                 "Select Staff Member",
#                 [f"{u['full_name']} (@{u['username']})" for u in staff_users],
#                 key="perm_user_select",
#             )
#             selected_user = staff_users[
#                 [f"{u['full_name']} (@{u['username']})" for u in staff_users].index(perm_user)
#             ]

#             current_perms = get_user_permissions(selected_user["id"])

#             modules = ["dashboard", "sales", "products", "purchases", "logs", "reports"]
#             module_labels = {
#                 "dashboard": "📊 Dashboard", "sales": "💰 Sales", "products": "📦 Products",
#                 "purchases": "🛒 Purchases", "logs": "📋 Logs", "reports": "📈 Reports"
#             }

#             st.markdown(f"**Setting permissions for {selected_user['full_name']}:**")

#             updated_perms = {}
#             for mod in modules:
#                 current = current_perms.get(mod, {"can_view": 0, "can_add": 0, "can_edit": 0, "can_delete": 0})
#                 with st.expander(f"{module_labels[mod]} — {mod.title()}", expanded=False):
#                     vc, ac, ec, dc = st.columns(4)
#                     with vc:
#                         pv = st.checkbox("👁️ View", value=bool(current["can_view"]), key=f"perm_{mod}_view")
#                     with ac:
#                         pa = st.checkbox("➕ Add", value=bool(current["can_add"]), key=f"perm_{mod}_add")
#                     with ec:
#                         pe = st.checkbox("✏️ Edit", value=bool(current["can_edit"]), key=f"perm_{mod}_edit")
#                     with dc:
#                         pd_del = st.checkbox("🗑️ Delete", value=bool(current["can_delete"]), key=f"perm_{mod}_delete")
#                     updated_perms[mod] = {"can_view": pv, "can_add": pa, "can_edit": pe, "can_delete": pd_del}

#             if st.button("💾 Save Permissions", type="primary", use_container_width=True):
#                 with get_db() as conn:
#                     c = conn.cursor()
#                     for mod, perms in updated_perms.items():
#                         c.execute(
#                             """INSERT OR REPLACE INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete)
#                                VALUES (?,?,?,?,?,?)""",
#                             (selected_user["id"], mod,
#                              int(perms["can_view"]), int(perms["can_add"]),
#                              int(perms["can_edit"]), int(perms["can_delete"])),
#                         )
#                     conn.commit()
#                 add_log(user["id"], "UPDATE", "staff",
#                         f"Updated permissions for {selected_user['username']}")
#                 st.success("Permissions updated successfully!")

#                 # Update session if editing self
#                 if selected_user["id"] == user["id"]:
#                     st.session_state.permissions = get_user_permissions(user["id"])

#     # ── Add User Tab ──
#     with staff_tabs[2]:
#         st.markdown("### ➕ Add New Staff Member")
#         with st.form("add_user_form"):
#             auc1, auc2 = st.columns(2)
#             with auc1:
#                 new_username = st.text_input("Username *", placeholder="e.g., john.doe")
#                 new_fullname = st.text_input("Full Name *", placeholder="e.g., John Doe")
#             with auc2:
#                 new_password = st.text_input("Password *", type="password", placeholder="Min 6 characters")
#                 new_role = st.selectbox("Role", ["staff", "admin"])

#             st.markdown("**Initial Permissions:**")
#             init_mods = ["dashboard", "sales", "products", "purchases", "logs", "reports"]
#             init_perms = {}
#             im_cols = st.columns(3)
#             for idx, mod in enumerate(init_mods):
#                 with im_cols[idx % 3]:
#                     init_perms[mod] = st.checkbox(f"Grant access to {mod.title()}", value=True, key=f"init_{mod}")

#             if st.form_submit_button("✅ Create User", use_container_width=True):
#                 if not new_username or not new_fullname or not new_password:
#                     st.error("All fields marked with * are required.")
#                 elif len(new_password) < 6:
#                     st.error("Password must be at least 6 characters.")
#                 else:
#                     try:
#                         with get_db() as conn:
#                             c = conn.cursor()
#                             c.execute(
#                                 "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
#                                 (new_username, hash_password(new_password), new_fullname, new_role),
#                             )
#                             new_user_id = c.lastrowid

#                             # Default: view dashboard
#                             if new_role == "admin":
#                                 for mod in init_mods + ["staff_access"]:
#                                     c.execute(
#                                         "INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)",
#                                         (new_user_id, mod, 1, 1, 1, 1),
#                                     )
#                             else:
#                                 for mod, granted in init_perms.items():
#                                     if granted:
#                                         c.execute(
#                                             "INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)",
#                                             (new_user_id, mod, 1, 1, 1, 0),  # view, add, edit but no delete by default
#                                         )
#                             conn.commit()
#                         add_log(user["id"], "CREATE", "staff", f"Created user: {new_username} ({new_role})")
#                         st.success(f"User '{new_username}' created successfully!")
#                         st.rerun()
#                     except sqlite3.IntegrityError:
#                         st.error(f"Username '{new_username}' already exists!")

# # ──────────────────────────────────────────────
# #  MAIN APP
# # ──────────────────────────────────────────────

# def main():
#     st.set_page_config(
#         page_title="InvenTrack — Inventory Management",
#         page_icon="🗄️",
#         layout="wide",
#         initial_sidebar_state="expanded",
#     )

#     load_custom_css()
#     init_database()

#     # Session state initialization
#     if "current_page" not in st.session_state:
#         st.session_state.current_page = "dashboard"

#     # Auth check
#     if "user" not in st.session_state:
#         render_login()
#         return

#     # Render sidebar navigation
#     render_sidebar()

#     # Page router
#     page_renderers = {
#         "dashboard": render_dashboard,
#         "sales": render_sales,
#         "products": render_products,
#         "purchases": render_purchases,
#         "logs": render_logs,
#         "reports": render_reports,
#         "staff_access": render_staff_access,
#     }

#     renderer = page_renderers.get(st.session_state.current_page, render_dashboard)
#     renderer()

#     # Footer
#     st.markdown("""
#     <div style="text-align:center;padding:2rem 0 1rem;color:#334155;font-size:0.75rem;border-top:1px solid #1e293b;margin-top:3rem;">
#         InvenTrack Inventory Management System v1.0 — Built with Streamlit
#     </div>
#     """, unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()