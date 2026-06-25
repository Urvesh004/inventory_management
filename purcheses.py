import streamlit as st
import pandas as pd
import datetime

# ✅ Changed from: from main import ...
from database import add_log, check_permission, get_all_products, get_db, require_permission

def render_purchases():
    if not require_permission("purchases"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">🛒</div>
        <div><h1>Purchases</h1><p>Track incoming inventory purchases</p></div>
    </div>""", unsafe_allow_html=True)

    if check_permission("purchases", "can_add"):
        with st.expander("➕ Record New Purchase", expanded=False):
            with st.form("new_purchase_form"):
                products = get_all_products()
                if not products:
                    st.warning("No products available. Add products first.")
                else:
                    pc1, pc2, pc3 = st.columns(3)
                    with pc1:
                        prod_options = {f"{p['name']} ({p['sku']})": p for p in products}
                        pur_prod = st.selectbox("Product *", list(prod_options.keys()))
                        selected_p = prod_options[pur_prod]
                    with pc2:
                        pur_qty = st.number_input("Quantity *", min_value=1, value=1, step=1)
                        pur_cost = st.number_input("Unit Cost (₹) *", value=selected_p["cost"], min_value=0.01, step=0.01, format="%.2f")
                    with pc3:
                        pur_supplier = st.text_input("Supplier", value=selected_p.get("supplier", ""))
                    total = pur_qty * pur_cost
                    st.markdown(f"### 💰 Total Cost: **₹{total:,.2f}**")
                    if st.form_submit_button("✅ Record Purchase", width='stretch'):
                        with get_db() as conn:
                            c = conn.cursor()
                            c.execute("INSERT INTO purchases (product_id, quantity, unit_cost, total, purchased_by, supplier) VALUES (?,?,?,?,?,?)", (selected_p["id"], pur_qty, pur_cost, total, st.session_state.user["id"], pur_supplier))
                            c.execute("UPDATE products SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (pur_qty, selected_p["id"]))
                            conn.commit()
                        add_log(st.session_state.user["id"], "CREATE", "purchases", f"Purchased {pur_qty}x {selected_p['name']} from {pur_supplier} for ₹{total:.2f}")
                        st.success(f"Purchase recorded! ₹{total:,.2f}")
                        st.rerun()

    st.markdown("### 📋 Purchase History")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        date_from = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30), key="pur_from")
    with filter_col2:
        date_to = st.date_input("To", value=datetime.date.today(), key="pur_to")

    with get_db() as conn:
        df_pur = pd.read_sql_query("SELECT pu.id, p.name as product, p.sku, pu.quantity, pu.unit_cost, pu.total, pu.supplier, pu.purchase_date, u.full_name as purchased_by_name FROM purchases pu JOIN products p ON pu.product_id = p.id LEFT JOIN users u ON pu.purchased_by = u.id WHERE date(pu.purchase_date) BETWEEN ? AND ? ORDER BY pu.purchase_date DESC", conn, params=(date_from.isoformat(), date_to.isoformat()))

    if not df_pur.empty:
        total_cost = df_pur["total"].sum()
        total_items = df_pur["quantity"].sum()
        pm1, pm2, pm3 = st.columns(3)
        with pm1: st.metric("Total Purchases", f"₹{total_cost:,.2f}")
        with pm2: st.metric("Items Received", f"{total_items:,}")
        with pm3: st.metric("Purchase Orders", f"{len(df_pur)}")
        df_display = df_pur.copy()
        df_display["unit_cost"] = df_display["unit_cost"].apply(lambda x: f"₹{x:,.2f}")
        df_display["total"] = df_display["total"].apply(lambda x: f"₹{x:,.2f}")
        df_display["purchase_date"] = df_display["purchase_date"].apply(lambda x: str(x)[:16])
        st.dataframe(df_display, width='stretch', hide_index=True)
    else:
        st.info("No purchases in the selected date range.")