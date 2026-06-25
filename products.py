import sqlite3
import pandas as pd
import streamlit as st

from database import add_log, check_permission, get_all_products, get_db, require_permission, get_next_sku

def render_products():
    if not require_permission("products"):
        return

    st.markdown("""
    <div class="section-header">
        <div class="icon-box">📦</div>
        <div><h1>Products</h1><p>Manage your product inventory</p></div>
    </div>""", unsafe_allow_html=True)

    col_search, col_cat, col_btn = st.columns([3, 2, 1])
    with col_search:
        search = st.text_input("🔍 Search", placeholder="Search by name or SKU...", key="prod_search")
    with col_cat:
        categories = ["All"] + list(set(p["category"] for p in get_all_products()))
        cat_filter = st.selectbox("Category", categories, key="prod_cat_filter")
    with col_btn:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if check_permission("products", "can_add"):
            if st.button("➕ Add Product", type="primary",width='stretch'):
                st.session_state.show_add_product = True

    # ──────────────────────────────────────────
    #  ADD PRODUCT FORM (Auto SKU)
    # ──────────────────────────────────────────
    if st.session_state.get("show_add_product", False):
        # Generate SKU once when form opens
        if "auto_sku" not in st.session_state:
            st.session_state.auto_sku = get_next_sku()

        with st.expander("➕ New Product", expanded=True):
            with st.form("add_product_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    pname = st.text_input("Product Name *")
                    # ✅ Auto-generated SKU (disabled, non-editable)
                    psku = st.text_input(
                        "SKU (Auto)", 
                        value=st.session_state.auto_sku,
                        disabled=True,
                        help="SKU is auto-generated. You cannot edit it."
                    )
                with c2:
                    existing_cats = list(set(p["category"] for p in get_all_products()))
                    default_cats = ["Electronics", "Furniture", "Stationery", "Clothing", "Food & Beverages", "Hardware", "General"]
                    all_cat_options = sorted(set(default_cats + existing_cats))
                    all_cat_options.append("➕ Add New Category")
                    pcategory_choice = st.selectbox("Category", all_cat_options)
                    if pcategory_choice == "➕ Add New Category":
                        pcategory = st.text_input("New Category Name *", placeholder="Type new category...")
                    else:
                        pcategory = pcategory_choice
                    psupplier = st.text_input("Supplier")
                with c3:
                    pprice = st.number_input("Selling Price (₹) *", min_value=0.01, step=0.01, format="%.2f")
                    pcost = st.number_input("Cost Price (₹) *", min_value=0.01, step=0.01, format="%.2f")
                c4, c5 = st.columns(2)
                with c4:
                    pquantity = st.number_input("Quantity", min_value=0, step=1)
                with c5:
                    pmin_stock = st.number_input("Min Stock Level", min_value=0, value=10, step=1)

                submitted = st.form_submit_button("✅ Create Product",width='stretch')
                if submitted:
                    if not pname:
                        st.error("Product name is required.")
                    elif not pcategory or pcategory == "➕ Add New Category":
                        st.error("Please enter a category name.")
                    else:
                        try:
                            # ✅ Use auto-generated SKU from session state
                            final_sku = st.session_state.auto_sku
                            with get_db() as conn:
                                c = conn.cursor()
                                c.execute(
                                    "INSERT INTO products (name, sku, category, price, cost, quantity, min_stock, supplier) VALUES (?,?,?,?,?,?,?,?)",
                                    (pname, final_sku, pcategory, pprice, pcost, pquantity, pmin_stock, psupplier)
                                )
                                conn.commit()
                            add_log(st.session_state.user["id"], "CREATE", "products", f"Added product: {pname} ({final_sku})")
                            st.success(f"Product '{pname}' created with SKU: {final_sku}")
                            # Clear session state so next time new SKU generates
                            if "auto_sku" in st.session_state:
                                del st.session_state.auto_sku
                            st.session_state.show_add_product = False
                            st.rerun()
                        except sqlite3.IntegrityError:
                            # Fallback: if SKU collision, generate new one
                            st.session_state.auto_sku = get_next_sku()
                            st.error(f"SKU conflict. Try again — new SKU generated: {st.session_state.auto_sku}")

            if st.button("Cancel"):
                if "auto_sku" in st.session_state:
                    del st.session_state.auto_sku
                st.session_state.show_add_product = False
                st.rerun()

    # ──────────────────────────────────────────
    #  PRODUCTS TABLE
    # ──────────────────────────────────────────
    products = get_all_products()
    if search:
        search_lower = search.lower()
        products = [p for p in products if search_lower in p["name"].lower() or search_lower in p["sku"].lower()]
    if cat_filter != "All":
        products = [p for p in products if p["category"] == cat_filter]

    if products:
        df = pd.DataFrame(products)
        display_cols = ["id", "name", "sku", "category", "price", "cost", "quantity", "min_stock", "supplier"]
        df_display = df[display_cols].copy()
        df_display["price"] = df_display["price"].apply(lambda x: f"₹{x:,.2f}")
        df_display["cost"] = df_display["cost"].apply(lambda x: f"₹{x:,.2f}")
        df_display["status"] = df.apply(
            lambda r: "🔴 Out" if r["quantity"] == 0 else ("🟡 Low" if r["quantity"] <= r["min_stock"] else "🟢 OK"), 
            axis=1
        )
        df_display["margin"] = df.apply(
            lambda r: f"{((r['price'] - r['cost']) / r['price'] * 100):.1f}%" if r['price'] > 0 else "0%", 
            axis=1
        )
        st.dataframe(df_display,width='stretch', hide_index=True)

        # ──────────────────────────────────────────
        #  EDIT / DELETE PRODUCT
        # ──────────────────────────────────────────
        if check_permission("products", "can_edit") or check_permission("products", "can_delete"):
            st.markdown("---")
            st.markdown("### ✏️ Manage Product")
            col_sel, col_act = st.columns([1, 2])
            with col_sel:
                prod_names = {f"{p['name']} ({p['sku']})": p["id"] for p in get_all_products()}
                selected_prod = st.selectbox("Select Product", list(prod_names.keys()), key="prod_select")
                selected_id = prod_names[selected_prod]

            with get_db() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM products WHERE id=?", (selected_id,))
                prod = dict(c.fetchone())

            tab_edit, tab_del = st.tabs(["✏️ Edit", "🗑️ Delete"])

            with tab_edit:
                if check_permission("products", "can_edit"):
                    with st.form("edit_product_form"):
                        ec1, ec2, ec3 = st.columns(3)
                        with ec1:
                            ename = st.text_input("Name", value=prod["name"])
                            # ✅ SKU shown but disabled in edit too
                            esku = st.text_input("SKU", value=prod["sku"], disabled=True, help="SKU cannot be changed after creation.")
                        with ec2:
                            existing_cats_edit = list(set(p["category"] for p in get_all_products()))
                            default_cats_edit = ["Electronics", "Furniture", "Stationery", "Clothing", "Food & Beverages", "Hardware", "General"]
                            all_cat_options_edit = sorted(set(default_cats_edit + existing_cats_edit))
                            all_cat_options_edit.append("➕ Add New Category")
                            ecategory_choice = st.selectbox(
                                "Category", all_cat_options_edit,
                                index=all_cat_options_edit.index(prod["category"]) if prod["category"] in all_cat_options_edit else 0
                            )
                            if ecategory_choice == "➕ Add New Category":
                                ecategory = st.text_input("New Category Name", value=prod["category"])
                            else:
                                ecategory = ecategory_choice
                            esupplier = st.text_input("Supplier", value=prod["supplier"])
                        with ec3:
                            eprice = st.number_input("Price (₹)", value=prod["price"], min_value=0.01, step=0.01, format="%.2f")
                            ecost = st.number_input("Cost (₹)", value=prod["cost"], min_value=0.01, step=0.01, format="%.2f")
                        ec4, ec5 = st.columns(2)
                        with ec4:
                            equantity = st.number_input("Quantity", value=prod["quantity"], min_value=0, step=1)
                        with ec5:
                            emin_stock = st.number_input("Min Stock", value=prod["min_stock"], min_value=0, step=1)

                        if st.form_submit_button("💾 Save Changes",width='stretch'):
                            with get_db() as conn:
                                c = conn.cursor()
                                # ✅ SKU not included in UPDATE — stays locked
                                c.execute(
                                    "UPDATE products SET name=?, category=?, price=?, cost=?, quantity=?, min_stock=?, supplier=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                    (ename, ecategory, eprice, ecost, equantity, emin_stock, esupplier, selected_id)
                                )
                                conn.commit()
                            add_log(st.session_state.user["id"], "UPDATE", "products", f"Updated product: {ename} ({prod['sku']})")
                            st.success("Product updated!")
                            st.rerun()
                else:
                    st.warning("You don't have edit permission.")

            with tab_del:
                if check_permission("products", "can_delete"):
                    st.warning(f"⚠️ Are you sure you want to delete **{prod['name']}** ({prod['sku']})? This cannot be undone.")
                    if st.button("🗑️ Delete Product", type="primary"):
                        with get_db() as conn:
                            c = conn.cursor()
                            c.execute("DELETE FROM products WHERE id=?", (selected_id,))
                            conn.commit()
                        add_log(st.session_state.user["id"], "DELETE", "products", f"Deleted product: {prod['name']} ({prod['sku']})")
                        st.success("Product deleted!")
                        st.rerun()
                else:
                    st.warning("You don't have delete permission.")
    else:
        st.info("No products found. Add your first product above!")