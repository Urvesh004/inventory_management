from contextlib import contextmanager
import hashlib
import sqlite3
import streamlit as st
import datetime

DB_PATH = "inventory.db"

# ──────────────────────────────────────────────
#  DATABASE CONNECTION
# ──────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ──────────────────────────────────────────────
#  PASSWORD HELPERS
# ──────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

# ──────────────────────────────────────────────
#  DATABASE INITIALIZATION
# ──────────────────────────────────────────────

def init_database():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'staff',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            can_view INTEGER DEFAULT 0,
            can_add INTEGER DEFAULT 0,
            can_edit INTEGER DEFAULT 0,
            can_delete INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, module)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            category TEXT DEFAULT 'General',
            price REAL NOT NULL,
            cost REAL NOT NULL,
            quantity INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 10,
            supplier TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_by INTEGER NOT NULL,
            customer_name TEXT DEFAULT 'Walk-in',
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(sold_by) REFERENCES users(id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_cost REAL NOT NULL,
            total REAL NOT NULL,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            purchased_by INTEGER NOT NULL,
            supplier TEXT DEFAULT '',
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(purchased_by) REFERENCES users(id)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            module TEXT NOT NULL,
            details TEXT DEFAULT '',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""")

        # Create default admin
        c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
        if c.fetchone()[0] == 0:
            admin_hash = hash_password("admin123")
            c.execute(
                "INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)",
                ("admin", admin_hash, "System Administrator", "admin"),
            )
            admin_id = c.lastrowid
            modules = ["dashboard", "sales", "products", "purchases", "logs", "reports", "staff_access"]
            for mod in modules:
                c.execute(
                    "INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)",
                    (admin_id, mod, 1, 1, 1, 1),
                )

        conn.commit()

# ──────────────────────────────────────────────
#  AUTH FUNCTIONS
# ──────────────────────────────────────────────

def authenticate_user(username, password):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username,))
        user = c.fetchone()
        if user and verify_password(password, user["password_hash"]):
            return dict(user)
    return None

def get_user_permissions(user_id):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM permissions WHERE user_id=?", (user_id,))
        rows = c.fetchall()
        perms = {}
        for row in rows:
            perms[row["module"]] = {
                "can_view": bool(row["can_view"]),
                "can_add": bool(row["can_add"]),
                "can_edit": bool(row["can_edit"]),
                "can_delete": bool(row["can_delete"]),
            }
        return perms

# ──────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────

def add_log(user_id, action, module, details=""):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO logs (user_id, action, module, details) VALUES (?,?,?,?)",
            (user_id, action, module, details),
        )
        conn.commit()

# ──────────────────────────────────────────────
#  DATA FETCHING
# ──────────────────────────────────────────────

def get_all_users():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in c.fetchall()]

def get_all_products():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM products ORDER BY updated_at DESC")
        return [dict(row) for row in c.fetchall()]

def get_low_stock_products():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE quantity <= min_stock ORDER BY quantity ASC")
        return [dict(row) for row in c.fetchall()]

# ──────────────────────────────────────────────
#  AUTO SKU GENERATOR
# ──────────────────────────────────────────────

def get_next_sku():
    """Generate next SKU like SKU-001, SKU-002, etc."""
    with get_db() as conn:
        c = conn.cursor()
        # Get the highest numeric part from existing SKU-XXX patterns
        c.execute("SELECT sku FROM products WHERE sku LIKE 'SKU-%' ORDER BY sku DESC LIMIT 1")
        row = c.fetchone()
        if row:
            try:
                last_num = int(row["sku"].split("-")[1])
                next_num = last_num + 1
            except (IndexError, ValueError):
                # Fallback if format is weird
                c.execute("SELECT COUNT(*) as cnt FROM products")
                next_num = c.fetchone()["cnt"] + 1
        else:
            # No SKU-XXX products exist yet
            c.execute("SELECT COUNT(*) as cnt FROM products")
            count = c.fetchone()["cnt"]
            next_num = count + 1

        return f"SKU-{next_num:03d}"

# ──────────────────────────────────────────────
#  PERMISSION HELPERS
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