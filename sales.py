import datetime
import pandas as pd
import streamlit as st

from database import add_log, check_permission, get_all_products, get_db, require_permission

def render_sales():
    if not require_permission("sales"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">💰</div>
        <div><h1>Sales</h1><p>Record and manage sales transactions</p></div>
    </div>""", unsafe_allow_html=True)

    # ──────────────────────────────────────────
    #  NEW SALE (No st.form = Enter key is disabled)
    # ──────────────────────────────────────────
    if check_permission("sales", "can_add"):
        with st.expander("➕ Record New Sale", expanded=False):
            products = get_all_products()
            available = [p for p in products if p["quantity"] > 0]

            if not available:
                st.warning("No products in stock to sell.")
            else:
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    prod_options = {f"{p['name']} ({p['sku']}) — Stock: {p['quantity']}": p for p in available}
                    sale_prod = st.selectbox("Product *", list(prod_options.keys()), key="sale_prod_sel")
                    selected_p = prod_options[sale_prod]
                with sc2:
                    max_qty = selected_p["quantity"]
                    sale_qty = st.number_input("Quantity *", min_value=1, max_value=max_qty, value=1, step=1, key="sale_qty_inp")
                with sc3:
                    sale_price = st.number_input("Unit Price (₹)", value=selected_p["price"], min_value=0.01, step=0.01, format="%.2f", key="sale_price_inp")
                    sale_customer = st.text_input("Customer", value="Walk-in", key="sale_cust_inp")

                total = sale_qty * sale_price
                st.markdown(f"### 💵 Total: **₹{total:,.2f}**")

                # ✅ FIX: Only triggers on actual mouse click, NOT on "Enter" key
                if st.button("✅ Complete Sale", type="primary", width='stretch', key="sale_submit_btn"):
                    with get_db() as conn:
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO sales (product_id, quantity, unit_price, total, sold_by, customer_name) VALUES (?,?,?,?,?,?)", 
                            (selected_p["id"], sale_qty, sale_price, total, st.session_state.user["id"], sale_customer)
                        )
                        c.execute(
                            "UPDATE products SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                            (sale_qty, selected_p["id"])
                        )
                        conn.commit()
                    
                    add_log(st.session_state.user["id"], "CREATE", "sales", f"Sold {sale_qty}x {selected_p['name']} to {sale_customer} for ₹{total:.2f}")
                    st.success(f"Sale recorded! ₹{total:,.2f}")
                    
                    # Clear form fields by deleting their session state keys
                    for key in ["sale_prod_sel", "sale_qty_inp", "sale_price_inp", "sale_cust_inp"]:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()

    # ──────────────────────────────────────────
    #  SALES HISTORY
    # ──────────────────────────────────────────
    st.markdown("### 📋 Sales History")

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        date_from = st.date_input("From", value=datetime.date.today() - datetime.timedelta(days=30), key="sales_from")
    with filter_col2:
        date_to = st.date_input("To", value=datetime.date.today(), key="sales_to")

    with get_db() as conn:
        # ✅ FIX: Cast sale_date to TEXT for Python 3.13
        df_sales = pd.read_sql_query("""
            SELECT s.id, p.name as product, p.sku, s.quantity, s.unit_price, s.total, 
                   s.customer_name, CAST(s.sale_date AS TEXT) as sale_date, u.full_name as sold_by_name
            FROM sales s
            JOIN products p ON s.product_id = p.id
            LEFT JOIN users u ON s.sold_by = u.id
            WHERE date(s.sale_date) BETWEEN ? AND ?
            ORDER BY s.sale_date DESC
        """, conn, params=(date_from.isoformat(), date_to.isoformat()))

    if not df_sales.empty:
        total_sales = df_sales["total"].sum()
        total_items = df_sales["quantity"].sum()

        sm1, sm2, sm3 = st.columns(3)
        with sm1: st.metric("Total Revenue", f"₹{total_sales:,.2f}")
        with sm2: st.metric("Items Sold", f"{total_items:,}")
        with sm3: st.metric("Transactions", f"{len(df_sales)}")

        df_display = df_sales.copy()
        df_display["unit_price"] = df_display["unit_price"].apply(lambda x: f"₹{x:,.2f}")
        df_display["total"] = df_display["total"].apply(lambda x: f"₹{x:,.2f}")
        df_display["sale_date"] = df_display["sale_date"].apply(lambda x: str(x)[:16])

        st.dataframe(df_display, width='stretch', hide_index=True)

        # Delete sale
        if check_permission("sales", "can_delete"):
            with st.expander("🗑️ Delete Sale Record"):
                sale_id = st.number_input("Sale ID to Delete", min_value=1, step=1, key="del_sale_id")
                if st.button("Delete Sale", key="del_sale_btn"):
                    with get_db() as conn:
                        c = conn.cursor()
                        c.execute("SELECT * FROM sales WHERE id=?", (sale_id,))
                        sale = c.fetchone()
                        if sale:
                            c.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (sale["quantity"], sale["product_id"]))
                            c.execute("DELETE FROM sales WHERE id=?", (sale_id,))
                            conn.commit()
                            add_log(st.session_state.user["id"], "DELETE", "sales", f"Deleted sale #{sale_id}")
                            st.success("Sale deleted and stock restored!")
                            st.rerun()
                        else:
                            st.error("Sale ID not found.")
    else:
        st.info("No sales in the selected date range.")