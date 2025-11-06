import streamlit as st
import pdfplumber
import pandas as pd
import io
import os
import re

st.set_page_config(
    page_title="Last Balance Report Extractor",
    layout="wide",
    page_icon="📄",
)

st.title("📄 Last Balance Report Extractor")
st.write("Upload one or more Last Balance Report PDFs and extract all rows into a clean table.")


# =========================================================
# ✅ Utility Functions
# =========================================================

def extract_pdf_tables(pdf_bytes):
    """Extract tables from each page of the PDF."""
    tables = []
    pages_with_data = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table)
                df.columns = df.iloc[0]       # first row = header
                df = df[1:]                   # remove header
                df["__page__"] = page_no
                tables.append(df)
                pages_with_data.append(page_no)

    return tables, pages_with_data


def clean_columns(df):
    """Clean column names: remove breaks, normalize spaces, title case."""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.title()
    )
    return df


def auto_convert_numeric(df):
    """Convert numeric-like columns to numbers automatically."""
    for col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(r"[^0-9.\-]", "", regex=True)
        )
        try:
            df[col] = pd.to_numeric(df[col])
        except:
            pass
    return df


def filter_table(df, query):
    """Global search across all columns."""
    if not query:
        return df
    query = query.lower()
    return df[df.apply(lambda row: row.astype(str).str.lower().str.contains(query).any(), axis=1)]


# =========================================================
# ✅ Main App Logic
# =========================================================

uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

if uploaded_files:

    st.info(f"📥 Processing {len(uploaded_files)} file(s)…")

    all_tables = []
    all_pages = []

    for uploaded in uploaded_files:
        pdf_bytes = uploaded.read()
        tables, pages = extract_pdf_tables(pdf_bytes)
        all_tables.extend(tables)
        all_pages.extend(pages)

    if not all_tables:
        st.error("No tables found in the uploaded PDFs.")
        st.stop()

    # Combine all tables
    combined = pd.concat(all_tables, ignore_index=True)
    combined = clean_columns(combined)
    combined = auto_convert_numeric(combined)

    # Remove page number from final result
    if "__page__" in combined.columns:
        combined.drop(columns=["__page__"], inplace=True)

    # =====================================================
    # ✅ Summary Metrics
    # =====================================================
    st.subheader("📌 Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Rows", len(combined))
    col2.metric("Pages With Tables", len(set(all_pages)))

    # Detect any numeric column that may represent balance
    balance_candidates = [c for c in combined.columns if "balance" in c.lower() or "amount" in c.lower()]

    if balance_candidates:
        bal = balance_candidates[0]
        total_balance = combined[bal].sum()
        avg_balance = combined[bal].mean()

        col3.metric("Total Balance", f"{total_balance:,.2f}")
        col4.metric("Average Balance", f"{avg_balance:,.2f}")
    else:
        col3.metric("Total Balance", "N/A")
        col4.metric("Average Balance", "N/A")

    # =====================================================
    # ✅ Search & Filter
    # =====================================================
    st.subheader("🔍 Search & Filter")
    query = st.text_input("Search across all columns", placeholder="Type to filter…")

    filtered_df = filter_table(combined, query)

    # =====================================================
    # ✅ Data Table
    # =====================================================
    st.subheader("📊 Extracted Data")
    st.dataframe(filtered_df, use_container_width=True, height=500)

    # =====================================================
    # ✅ Export Section
    # =====================================================
    st.subheader("⬇️ Export Extracted Data")

    base_name = os.path.splitext(uploaded_files[0].name)[0]
    csv_filename = f"{base_name}_extracted.csv"
    xlsx_filename = f"{base_name}_extracted.xlsx"

    st.download_button(
        "Download CSV",
        filtered_df.to_csv(index=False).encode("utf-8"),
        csv_filename,
        "text/csv",
    )

    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False)
    st.download_button(
        "Download Excel",
        excel_buffer.getvalue(),
        xlsx_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


    # =====================================================
    # ✅ Page-Level Tables (Optional)
    # =====================================================
    with st.expander("📄 View Page-Level Tables"):
        for i, df in enumerate(all_tables, start=1):
            st.write(f"### Page {all_pages[i-1]}")
            df_preview = df.drop(columns=["__page__"]) if "__page__" in df.columns else df
            st.dataframe(df_preview, use_container_width=True)
    st.subheader("📊 Extracted Data")
    st.dataframe(filtered_df, use_container_width=True, height=500)


    # ---------------------------------------
    # ✅ Export Section
    # ---------------------------------------
    st.subheader("⬇️ Export Extracted Data")

    # Use first filename as base
    base_name = os.path.splitext(uploaded_files[0].name)[0]
    csv_filename = f"{base_name}_extracted.csv"
    xlsx_filename = f"{base_name}_extracted.xlsx"

    st.download_button(
        "Download CSV",
        filtered_df.to_csv(index=False).encode("utf-8"),
        csv_filename,
        "text/csv",
    )

    excel_buffer = io.BytesIO()
    filtered_df.to_excel(excel_buffer, index=False)
    st.download_button(
        "Download Excel",
        excel_buffer.getvalue(),
        xlsx_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
