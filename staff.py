import streamlit as st
import pandas as pd
import sqlite3

# ✅ Changed from: from main import ...
from database import add_log, get_all_users, get_db, get_user_permissions, hash_password, require_permission

def render_staff_access():
    if not require_permission("staff_access"):
        return

    user = st.session_state.user
    if user["role"] != "admin":
        st.error("Only administrators can access this section.")
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">👥</div>
        <div><h1>Staff Access</h1><p>Manage users, roles, and permissions</p></div>
    </div>""", unsafe_allow_html=True)

    staff_tabs = st.tabs(["👥 Users", "🔑 Permissions", "➕ Add User"])

    with staff_tabs[0]:
        users = get_all_users()
        for u in users:
            role_cls = "badge-admin" if u["role"] == "admin" else "badge-staff"
            role_label = "Administrator" if u["role"] == "admin" else "Staff"
            status_cls = "badge-active" if u["is_active"] else "badge-inactive"
            status_label = "Active" if u["is_active"] else "Disabled"
            with st.expander(f"{'🛡️' if u['role'] == 'admin' else '👤'} {u['full_name']} (@{u['username']})"):
                uc1, uc2, uc3, uc4 = st.columns(4)
                with uc1: st.markdown(f"**Username:** {u['username']}")
                with uc2: st.markdown(f"**Role:** <span class='badge {role_cls}'>{role_label}</span>", unsafe_allow_html=True)
                with uc3: st.markdown(f"**Status:** <span class='badge {status_cls}'>{status_label}</span>", unsafe_allow_html=True)
                with uc4: st.markdown(f"**Joined:** {str(u['created_at'])[:10]}")
                if u["username"] != "admin":
                    ac1, ac2, ac3 = st.columns(3)
                    with ac1:
                        if u["is_active"]:
                            if st.button("🚫 Disable", key=f"disable_{u['id']}", width="stretch"):
                                with get_db() as conn:
                                    c = conn.cursor()
                                    c.execute("UPDATE users SET is_active=0 WHERE id=?", (u["id"],))
                                    conn.commit()
                                add_log(user["id"], "UPDATE", "staff", f"Disabled user: {u['username']}")
                                st.success("User disabled.")
                                st.rerun()
                        else:
                            if st.button("✅ Enable", key=f"enable_{u['id']}", width="stretch"):
                                with get_db() as conn:
                                    c = conn.cursor()
                                    c.execute("UPDATE users SET is_active=1 WHERE id=?", (u["id"],))
                                    conn.commit()
                                add_log(user["id"], "UPDATE", "staff", f"Enabled user: {u['username']}")
                                st.success("User enabled.")
                                st.rerun()
                    with ac2:
                        new_role = "staff" if u["role"] == "admin" else "admin"
                        if st.button(f"🔄 Make {new_role.title()}", key=f"role_{u['id']}", width="stretch"):
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("UPDATE users SET role=? WHERE id=?", (new_role, u["id"]))
                                if new_role == "admin":
                                    modules = ["dashboard", "sales", "products", "purchases", "logs", "reports", "staff_access"]
                                    for mod in modules:
                                        c.execute("INSERT OR REPLACE INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)", (u["id"], mod, 1, 1, 1, 1))
                                conn.commit()
                            add_log(user["id"], "UPDATE", "staff", f"Changed {u['username']} role to {new_role}")
                            st.success(f"Role changed to {new_role}.")
                            st.rerun()
                    with ac3:
                        if st.button("🗑️ Delete", key=f"del_{u['id']}", width="stretch"):
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute("DELETE FROM permissions WHERE user_id=?", (u["id"],))
                                c.execute("DELETE FROM users WHERE id=?", (u["id"],))
                                conn.commit()
                            add_log(user["id"], "DELETE", "staff", f"Deleted user: {u['username']}")
                            st.success("User deleted.")
                            st.rerun()
                perms = get_user_permissions(u["id"])
                if perms:
                    st.markdown("**Current Permissions:**")
                    perm_cols = st.columns(min(len(perms), 4))
                    for idx, (mod, p) in enumerate(perms.items()):
                        with perm_cols[idx % len(perm_cols)]:
                            mod_label = mod.replace("_", " ").title()
                            st.markdown(f"""<div style="background:rgba(30,41,59,0.6);border-radius:10px;padding:0.75rem;border:1px solid rgba(99,102,241,0.1);margin-bottom:0.5rem;"><div style="font-weight:600;color:#e2e8f0;font-size:0.85rem;margin-bottom:0.5rem;">📂 {mod_label}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;"><span class="perm-item {'perm-on' if p['can_view'] else 'perm-off'}">👁️ View</span><span class="perm-item {'perm-on' if p['can_add'] else 'perm-off'}">➕ Add</span><span class="perm-item {'perm-on' if p['can_edit'] else 'perm-off'}">✏️ Edit</span><span class="perm-item {'perm-on' if p['can_delete'] else 'perm-off'}">🗑️ Delete</span></div></div>""", unsafe_allow_html=True)

    with staff_tabs[1]:
        st.markdown("### 🔑 Manage Permissions")
        staff_users = [u for u in get_all_users() if u["role"] != "admin"]
        if not staff_users:
            st.info("No staff users to manage.")
        else:
            perm_user = st.selectbox("Select Staff Member", [f"{u['full_name']} (@{u['username']})" for u in staff_users], key="perm_user_select")
            selected_user = staff_users[[f"{u['full_name']} (@{u['username']})" for u in staff_users].index(perm_user)]
            current_perms = get_user_permissions(selected_user["id"])
            modules = ["dashboard", "sales", "products", "purchases", "logs", "reports"]
            module_labels = {"dashboard": "📊 Dashboard", "sales": "💰 Sales", "products": "📦 Products", "purchases": "🛒 Purchases", "logs": "📋 Logs", "reports": "📈 Reports"}
            st.markdown(f"**Setting permissions for {selected_user['full_name']}:**")
            updated_perms = {}
            for mod in modules:
                current = current_perms.get(mod, {"can_view": 0, "can_add": 0, "can_edit": 0, "can_delete": 0})
                with st.expander(f"{module_labels[mod]} — {mod.title()}", expanded=False):
                    vc, ac, ec, dc = st.columns(4)
                    with vc: pv = st.checkbox("👁️ View", value=bool(current["can_view"]), key=f"perm_{mod}_view")
                    with ac: pa = st.checkbox("➕ Add", value=bool(current["can_add"]), key=f"perm_{mod}_add")
                    with ec: pe = st.checkbox("✏️ Edit", value=bool(current["can_edit"]), key=f"perm_{mod}_edit")
                    with dc: pd_del = st.checkbox("🗑️ Delete", value=bool(current["can_delete"]), key=f"perm_{mod}_delete")
                    updated_perms[mod] = {"can_view": pv, "can_add": pa, "can_edit": pe, "can_delete": pd_del}
            if st.button("💾 Save Permissions", type="primary", width="stretch"):
                with get_db() as conn:
                    c = conn.cursor()
                    for mod, perms in updated_perms.items():
                        c.execute("INSERT OR REPLACE INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)", (selected_user["id"], mod, int(perms["can_view"]), int(perms["can_add"]), int(perms["can_edit"]), int(perms["can_delete"])))
                    conn.commit()
                add_log(user["id"], "UPDATE", "staff", f"Updated permissions for {selected_user['username']}")
                st.success("Permissions updated successfully!")
                if selected_user["id"] == user["id"]:
                    st.session_state.permissions = get_user_permissions(user["id"])

    with staff_tabs[2]:
        st.markdown("### ➕ Add New Staff Member")
        with st.form("add_user_form"):
            auc1, auc2 = st.columns(2)
            with auc1:
                new_username = st.text_input("Username *", placeholder="e.g., john.doe")
                new_fullname = st.text_input("Full Name *", placeholder="e.g., John Doe")
            with auc2:
                new_password = st.text_input("Password *", type="password", placeholder="Min 6 characters")
                new_role = st.selectbox("Role", ["staff", "admin"])
            st.markdown("**Initial Permissions:**")
            init_mods = ["dashboard", "sales", "products", "purchases", "logs", "reports"]
            init_perms = {}
            im_cols = st.columns(3)
            for idx, mod in enumerate(init_mods):
                with im_cols[idx % 3]:
                    init_perms[mod] = st.checkbox(f"Grant access to {mod.title()}", value=True, key=f"init_{mod}")
            if st.form_submit_button("✅ Create User", width="stretch"):
                if not new_username or not new_fullname or not new_password:
                    st.error("All fields marked with * are required.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    try:
                        with get_db() as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO users (username, password_hash, full_name, role) VALUES (?,?,?,?)", (new_username, hash_password(new_password), new_fullname, new_role))
                            new_user_id = c.lastrowid
                            if new_role == "admin":
                                for mod in init_mods + ["staff_access"]:
                                    c.execute("INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)", (new_user_id, mod, 1, 1, 1, 1))
                            else:
                                for mod, granted in init_perms.items():
                                    if granted:
                                        c.execute("INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete) VALUES (?,?,?,?,?,?)", (new_user_id, mod, 1, 1, 1, 0))
                            conn.commit()
                        add_log(user["id"], "CREATE", "staff", f"Created user: {new_username} ({new_role})")
                        st.success(f"User '{new_username}' created successfully!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"Username '{new_username}' already exists!")