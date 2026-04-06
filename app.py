"""
💰 Household Finance Tracker — Streamlit Dashboard
===================================================
Upload card PDF statements → auto-parse & categorize → track spending,
investments, and savings month-by-month with charts.

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import tempfile, os, calendar
from datetime import datetime, date

from config import (
    CURRENCIES, DEFAULT_CURRENCY,
    SPENDING_CATEGORIES, INVESTMENT_CATEGORIES, SAVINGS_CATEGORIES,
)
from parsers.pdf_parser import parse_pdf_statement, extract_statement_period
from categorizer import categorize_dataframe, get_all_categories
from data_manager import (
    load_transactions, append_transactions, save_transactions,
    load_investments, add_investment,
    load_savings, add_saving,
    monthly_spending_summary, monthly_investment_summary,
    monthly_savings_summary, grand_totals,
)

# ─── Page Config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Household Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-card h3 { margin: 0; font-size: 14px; opacity: 0.9; }
    .metric-card h1 { margin: 5px 0 0 0; font-size: 28px; }
    .spend-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .invest-card { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
    .save-card { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
    .credit-card { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); color: #333; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────
st.sidebar.title("💰 Finance Tracker")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📄 Upload Statement", "💳 Transactions",
     "📈 Investments", "🏦 Savings", "⚙️ Manage Categories"],
)


# =====================================================================
# DASHBOARD PAGE
# =====================================================================
if page == "📊 Dashboard":
    st.title("📊 Monthly Household Finance Dashboard")

    # Currency filter
    col_curr, col_month = st.columns([1, 2])
    with col_curr:
        currency = st.selectbox("Currency", CURRENCIES, index=0)

    # Load data
    txn_df = load_transactions()
    inv_df = load_investments()
    sav_df = load_savings()

    # Month filter
    all_months = set()
    for df in [txn_df, inv_df, sav_df]:
        if not df.empty and "month_year" in df.columns:
            all_months.update(df["month_year"].dropna().unique())
    all_months = sorted(all_months, reverse=True)

    with col_month:
        selected_month = st.selectbox(
            "Month",
            ["All Time"] + all_months,
            index=0,
        )

    st.markdown("---")

    # Filter helper
    def filter_df(df, curr, month):
        if df.empty:
            return df
        out = df.copy()
        if "currency" in out.columns:
            out = out[out["currency"] == curr]
        if month != "All Time" and "month_year" in out.columns:
            out = out[out["month_year"] == month]
        return out

    f_txn = filter_df(txn_df, currency, selected_month)
    f_inv = filter_df(inv_df, currency, selected_month)
    f_sav = filter_df(sav_df, currency, selected_month)

    # Metrics
    spending = f_txn[f_txn["type"] == "debit"]["amount"].sum() if not f_txn.empty else 0
    credits = f_txn[f_txn["type"] == "credit"]["amount"].sum() if not f_txn.empty else 0
    investing = f_inv["amount"].sum() if not f_inv.empty else 0
    saving = f_sav["amount"].sum() if not f_sav.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="metric-card spend-card">
            <h3>Total Spending</h3><h1>{currency} {spending:,.2f}</h1></div>""",
            unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card credit-card">
            <h3>Credits / Refunds</h3><h1>{currency} {credits:,.2f}</h1></div>""",
            unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card invest-card">
            <h3>Investments</h3><h1>{currency} {investing:,.2f}</h1></div>""",
            unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card save-card">
            <h3>Savings</h3><h1>{currency} {saving:,.2f}</h1></div>""",
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────
    tab_spend, tab_invest, tab_save, tab_trend = st.tabs(
        ["🛒 Spending Breakdown", "📈 Investment Breakdown",
         "🏦 Savings Breakdown", "📉 Monthly Trends"]
    )

    with tab_spend:
        if not f_txn.empty:
            debits = f_txn[f_txn["type"] == "debit"]
            if not debits.empty:
                cat_sum = debits.groupby("category")["amount"].sum().reset_index()
                cat_sum = cat_sum.sort_values("amount", ascending=False)

                col_pie, col_bar = st.columns(2)
                with col_pie:
                    fig = px.pie(cat_sum, values="amount", names="category",
                                 title="Spending by Category",
                                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3)
                    st.plotly_chart(fig, use_container_width=True)
                with col_bar:
                    fig = px.bar(cat_sum, x="category", y="amount",
                                 title="Category-wise Spending",
                                 color="category",
                                 color_discrete_sequence=px.colors.qualitative.Set3)
                    fig.update_layout(showlegend=False, xaxis_tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

                st.subheader("📋 Category Summary Table")
                cat_sum.columns = ["Category", f"Amount ({currency})"]
                cat_sum[f"Amount ({currency})"] = cat_sum[f"Amount ({currency})"].apply(
                    lambda x: f"{x:,.2f}"
                )
                st.dataframe(cat_sum, use_container_width=True, hide_index=True)
        else:
            st.info("No spending data yet. Upload a statement to get started!")

    with tab_invest:
        if not f_inv.empty:
            cat_sum = f_inv.groupby("category")["amount"].sum().reset_index()
            cat_sum = cat_sum.sort_values("amount", ascending=False)

            col_pie, col_bar = st.columns(2)
            with col_pie:
                fig = px.pie(cat_sum, values="amount", names="category",
                             title="Investment by Category",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig, use_container_width=True)
            with col_bar:
                fig = px.bar(cat_sum, x="category", y="amount",
                             title="Category-wise Investments",
                             color="category",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Investment Summary Table")
            cat_sum.columns = ["Category", f"Amount ({currency})"]
            cat_sum[f"Amount ({currency})"] = cat_sum[f"Amount ({currency})"].apply(
                lambda x: f"{x:,.2f}"
            )
            st.dataframe(cat_sum, use_container_width=True, hide_index=True)
        else:
            st.info("No investment data yet. Add investments from the sidebar!")

    with tab_save:
        if not f_sav.empty:
            cat_sum = f_sav.groupby("category")["amount"].sum().reset_index()
            cat_sum = cat_sum.sort_values("amount", ascending=False)

            col_pie, col_bar = st.columns(2)
            with col_pie:
                fig = px.pie(cat_sum, values="amount", names="category",
                             title="Savings by Category",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                st.plotly_chart(fig, use_container_width=True)
            with col_bar:
                fig = px.bar(cat_sum, x="category", y="amount",
                             title="Category-wise Savings",
                             color="category",
                             color_discrete_sequence=px.colors.qualitative.Safe)
                fig.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Savings Summary Table")
            cat_sum.columns = ["Category", f"Amount ({currency})"]
            cat_sum[f"Amount ({currency})"] = cat_sum[f"Amount ({currency})"].apply(
                lambda x: f"{x:,.2f}"
            )
            st.dataframe(cat_sum, use_container_width=True, hide_index=True)
        else:
            st.info("No savings data yet. Add savings from the sidebar!")

    with tab_trend:
        # Monthly trend chart — spending, investment, savings over time
        trend_data = []

        if not txn_df.empty:
            t = txn_df[(txn_df["type"] == "debit") & (txn_df["currency"] == currency)]
            if not t.empty:
                g = t.groupby("month_year")["amount"].sum().reset_index()
                g["type"] = "Spending"
                trend_data.append(g)

        if not inv_df.empty:
            t = inv_df[inv_df["currency"] == currency]
            if not t.empty:
                g = t.groupby("month_year")["amount"].sum().reset_index()
                g["type"] = "Investment"
                trend_data.append(g)

        if not sav_df.empty:
            t = sav_df[sav_df["currency"] == currency]
            if not t.empty:
                g = t.groupby("month_year")["amount"].sum().reset_index()
                g["type"] = "Savings"
                trend_data.append(g)

        if trend_data:
            trend_df = pd.concat(trend_data, ignore_index=True)
            fig = px.line(trend_df, x="month_year", y="amount", color="type",
                          title="Monthly Trends",
                          markers=True,
                          labels={"month_year": "Month", "amount": f"Amount ({currency})"})
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for trends yet.")


# =====================================================================
# UPLOAD STATEMENT PAGE
# =====================================================================
elif page == "📄 Upload Statement":
    st.title("📄 Upload Card / Bank Statement (PDF)")

    col1, col2, col3 = st.columns(3)
    with col1:
        currency = st.selectbox("Statement Currency", CURRENCIES, index=0)
    with col2:
        stmt_year = st.number_input(
            "Statement Year", min_value=2020, max_value=2030,
            value=datetime.now().year, step=1
        )
    with col3:
        month_names = [
            "All (auto-detect)", "January", "February", "March", "April",
            "May", "June", "July", "August", "September", "October",
            "November", "December",
        ]
        stmt_month = st.selectbox("Statement Month", month_names, index=0)

    uploaded_files = st.file_uploader(
        "Upload one or more PDF statements",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.subheader(f"📎 {uploaded_file.name}")

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                # Parse
                with st.spinner(f"Parsing {uploaded_file.name}..."):
                    df = parse_pdf_statement(tmp_path, currency=currency,
                                             statement_year=stmt_year)

                if df.empty:
                    st.warning(f"⚠️ Could not extract transactions from {uploaded_file.name}. "
                               "The PDF format may not be supported. Try a different statement format.")
                    continue

                # Filter by selected month if specified
                if stmt_month != "All (auto-detect)":
                    month_num = month_names.index(stmt_month)  # 1-12
                    df = df[df["date"].dt.month == month_num]
                    if df.empty:
                        st.warning(f"⚠️ No transactions found for {stmt_month} in {uploaded_file.name}.")
                        continue

                # Auto-categorize
                df = categorize_dataframe(df)
                df["source_file"] = uploaded_file.name
                df["month_year"] = df["date"].dt.strftime("%Y-%m")

                st.success(f"✅ Found **{len(df)}** transactions!")

                # Show extracted data with editable categories
                st.markdown("**Review & Edit Categories** (click any category cell to change it):")

                all_cats = get_all_categories()

                edited_df = st.data_editor(
                    df[["date", "description", "amount", "type", "category", "currency"]],
                    column_config={
                        "category": st.column_config.SelectboxColumn(
                            "Category",
                            options=all_cats,
                            required=True,
                        ),
                        "amount": st.column_config.NumberColumn(
                            "Amount", format="%.2f"
                        ),
                        "type": st.column_config.SelectboxColumn(
                            "Type", options=["debit", "credit"], required=True,
                        ),
                    },
                    use_container_width=True,
                    num_rows="dynamic",
                    key=f"editor_{uploaded_file.name}",
                )

                if st.button(f"💾 Save Transactions from {uploaded_file.name}",
                             key=f"save_{uploaded_file.name}"):
                    # Merge edits back
                    df["category"] = edited_df["category"].values
                    df["type"] = edited_df["type"].values
                    df["amount"] = edited_df["amount"].values

                    result = append_transactions(df)
                    st.success(f"✅ Saved! Total transactions in database: **{len(result)}**")
                    st.balloons()

            finally:
                os.unlink(tmp_path)


# =====================================================================
# TRANSACTIONS PAGE
# =====================================================================
elif page == "💳 Transactions":
    st.title("💳 All Transactions")

    txn_df = load_transactions()

    if txn_df.empty:
        st.info("No transactions yet. Upload a statement to get started!")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            currency = st.selectbox("Currency", CURRENCIES, index=0)
        with col2:
            months = sorted(txn_df["month_year"].dropna().unique(), reverse=True)
            month_filter = st.selectbox("Month", ["All"] + list(months))
        with col3:
            cat_filter = st.selectbox("Category", ["All"] + get_all_categories())

        filtered = txn_df[txn_df["currency"] == currency]
        if month_filter != "All":
            filtered = filtered[filtered["month_year"] == month_filter]
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]

        # Summary metrics
        c1, c2, c3 = st.columns(3)
        debits = filtered[filtered["type"] == "debit"]["amount"].sum()
        credits = filtered[filtered["type"] == "credit"]["amount"].sum()
        with c1:
            st.metric("Total Debits", f"{currency} {debits:,.2f}")
        with c2:
            st.metric("Total Credits", f"{currency} {credits:,.2f}")
        with c3:
            st.metric("Net", f"{currency} {debits - credits:,.2f}")

        # Editable table
        st.markdown("---")
        all_cats = get_all_categories()

        edited = st.data_editor(
            filtered[["date", "description", "amount", "type", "category", "currency", "month_year"]],
            column_config={
                "category": st.column_config.SelectboxColumn(
                    "Category", options=all_cats, required=True,
                ),
            },
            use_container_width=True,
            key="txn_editor",
        )

        if st.button("💾 Save Changes"):
            # Apply edits back to master dataframe
            txn_df.loc[filtered.index, "category"] = edited["category"].values
            save_transactions(txn_df)
            st.success("✅ Changes saved!")
            st.rerun()

        # Export
        st.markdown("---")
        csv = filtered.to_csv(index=False)
        st.download_button("📥 Download as CSV", csv, "transactions.csv", "text/csv")


# =====================================================================
# INVESTMENTS PAGE
# =====================================================================
elif page == "📈 Investments":
    st.title("📈 Investment Tracker")

    # Add new investment
    with st.expander("➕ Add New Investment", expanded=False):
        with st.form("add_investment"):
            col1, col2 = st.columns(2)
            with col1:
                inv_date = st.date_input("Date", value=date.today())
                inv_cat = st.selectbox("Category", INVESTMENT_CATEGORIES)
                inv_currency = st.selectbox("Currency", CURRENCIES, index=0)
            with col2:
                inv_desc = st.text_input("Description", placeholder="e.g. SIP - HDFC Equity Fund")
                inv_amount = st.number_input("Amount", min_value=0.0, step=100.0)
                inv_platform = st.text_input("Platform", placeholder="e.g. Groww, Tiger Brokers")

            submitted = st.form_submit_button("Add Investment")
            if submitted and inv_amount > 0:
                record = {
                    "date": inv_date,
                    "category": inv_cat,
                    "description": inv_desc,
                    "amount": inv_amount,
                    "currency": inv_currency,
                    "platform": inv_platform,
                }
                add_investment(record)
                st.success(f"✅ Added {inv_currency} {inv_amount:,.2f} to {inv_cat}")
                st.rerun()

    # Show investments
    inv_df = load_investments()

    if not inv_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            currency = st.selectbox("Filter Currency", CURRENCIES, index=0, key="inv_curr")
        with col2:
            months = sorted(inv_df["month_year"].dropna().unique(), reverse=True)
            month_filter = st.selectbox("Filter Month", ["All"] + list(months), key="inv_month")

        filtered = inv_df[inv_df["currency"] == currency]
        if month_filter != "All":
            filtered = filtered[filtered["month_year"] == month_filter]

        if not filtered.empty:
            total = filtered["amount"].sum()
            st.metric("Total Investments", f"{currency} {total:,.2f}")

            # Category summary
            cat_sum = filtered.groupby("category")["amount"].sum().reset_index()
            cat_sum = cat_sum.sort_values("amount", ascending=False)

            col_pie, col_table = st.columns(2)
            with col_pie:
                fig = px.pie(cat_sum, values="amount", names="category",
                             title="Investment Allocation", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col_table:
                st.subheader("Category Summary")
                display = cat_sum.copy()
                display.columns = ["Category", f"Amount ({currency})"]
                display[f"Amount ({currency})"] = display[f"Amount ({currency})"].apply(
                    lambda x: f"{x:,.2f}"
                )
                st.dataframe(display, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("📋 All Investment Records")
            st.dataframe(filtered, use_container_width=True, hide_index=True)

            csv = filtered.to_csv(index=False)
            st.download_button("📥 Download as CSV", csv, "investments.csv", "text/csv")
        else:
            st.info("No investments found for the selected filters.")
    else:
        st.info("No investments recorded yet. Use the form above to add one!")


# =====================================================================
# SAVINGS PAGE
# =====================================================================
elif page == "🏦 Savings":
    st.title("🏦 Savings Tracker")

    # Add new saving
    with st.expander("➕ Add New Saving", expanded=False):
        with st.form("add_saving"):
            col1, col2 = st.columns(2)
            with col1:
                sav_date = st.date_input("Date", value=date.today())
                sav_cat = st.selectbox("Category", SAVINGS_CATEGORIES)
                sav_currency = st.selectbox("Currency", CURRENCIES, index=0)
            with col2:
                sav_desc = st.text_input("Description", placeholder="e.g. Monthly emergency fund contribution")
                sav_amount = st.number_input("Amount", min_value=0.0, step=100.0)

            submitted = st.form_submit_button("Add Saving")
            if submitted and sav_amount > 0:
                record = {
                    "date": sav_date,
                    "category": sav_cat,
                    "description": sav_desc,
                    "amount": sav_amount,
                    "currency": sav_currency,
                }
                add_saving(record)
                st.success(f"✅ Added {sav_currency} {sav_amount:,.2f} to {sav_cat}")
                st.rerun()

    # Show savings
    sav_df = load_savings()

    if not sav_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            currency = st.selectbox("Filter Currency", CURRENCIES, index=0, key="sav_curr")
        with col2:
            months = sorted(sav_df["month_year"].dropna().unique(), reverse=True)
            month_filter = st.selectbox("Filter Month", ["All"] + list(months), key="sav_month")

        filtered = sav_df[sav_df["currency"] == currency]
        if month_filter != "All":
            filtered = filtered[filtered["month_year"] == month_filter]

        if not filtered.empty:
            total = filtered["amount"].sum()
            st.metric("Total Savings", f"{currency} {total:,.2f}")

            cat_sum = filtered.groupby("category")["amount"].sum().reset_index()
            cat_sum = cat_sum.sort_values("amount", ascending=False)

            col_pie, col_table = st.columns(2)
            with col_pie:
                fig = px.pie(cat_sum, values="amount", names="category",
                             title="Savings Allocation", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col_table:
                st.subheader("Category Summary")
                display = cat_sum.copy()
                display.columns = ["Category", f"Amount ({currency})"]
                display[f"Amount ({currency})"] = display[f"Amount ({currency})"].apply(
                    lambda x: f"{x:,.2f}"
                )
                st.dataframe(display, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("📋 All Savings Records")
            st.dataframe(filtered, use_container_width=True, hide_index=True)

            csv = filtered.to_csv(index=False)
            st.download_button("📥 Download as CSV", csv, "savings.csv", "text/csv")
        else:
            st.info("No savings found for the selected filters.")
    else:
        st.info("No savings recorded yet. Use the form above to add one!")


# =====================================================================
# MANAGE CATEGORIES PAGE
# =====================================================================
elif page == "⚙️ Manage Categories":
    st.title("⚙️ Manage Auto-Categorization Keywords")

    st.markdown("""
    The auto-categorizer matches transaction descriptions against keywords.
    Below are the current keyword mappings. To permanently add keywords,
    edit `config.py`.
    """)

    for category, keywords in SPENDING_CATEGORIES.items():
        with st.expander(f"**{category}** ({len(keywords)} keywords)"):
            if keywords:
                st.write(", ".join(keywords))
            else:
                st.write("_No keywords — this is the catch-all category._")

    st.markdown("---")
    st.subheader("Re-categorize Existing Transactions")
    st.markdown("Go to the **💳 Transactions** page to edit categories on existing records.")

    st.markdown("---")
    st.subheader("Investment Categories")
    for cat in INVESTMENT_CATEGORIES:
        st.markdown(f"- {cat}")

    st.subheader("Savings Categories")
    for cat in SAVINGS_CATEGORIES:
        st.markdown(f"- {cat}")


# ─── Footer ──────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Household Finance Tracker** v1.0\n\n"
    "Currencies: SGD 🇸🇬 & INR 🇮🇳\n\n"
    f"📅 {datetime.now().strftime('%b %Y')}"
)
