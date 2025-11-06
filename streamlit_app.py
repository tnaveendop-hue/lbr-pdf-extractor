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

uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# ------------------------------------------------------
# ✅ Utility Functions
# ------------------------------------------------------

def extract_pdf_tables(pdf_bytes):
    tables = []
    pages_with_data = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table)
                df.columns = df.iloc[0]
                df = df[1:]
                df["__page__"] = page_no
                tables.append(df)
                pages_with_data.append(page_no)
    return tables, pages_with_data


def clean_columns(df):
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("
", " ", regex=False)
        .str.replace("  +", " ", regex=True)
        .str.strip()
        .str.title()
    )
    return df


def auto_convert_numeric(df):
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = df[col].apply(lambda x: re.sub(r"[^0-9.-]", "", x) if re.match(r".*[0-9].*", x) else x)
        try:
            df[col] = pd.to_numeric(df[col])
        except:
            pass
    return df


def filter_table(df, query):
    if not query:
        return df
    q = query.lower()
    return df[df.apply(lambda row: row.astype(str).str.lower().str.contains(q).any(), axis=1)]


# ------------------------------------------------------
# ✅ Main Processing
# ------------------------------------------------------

if uploaded_files:
    st.info(f"📥 Processing {len(uploaded_files)} file(s)…")

    all_tables = []
    all_pages = []

    # Loop through uploaded PDFs
    for uploaded in uploaded_files:
        pdf_bytes = uploaded.read()
        tables, pages = extract_pdf_tables(pdf_bytes)
        all_tables.extend(tables)
        all_pages.extend(pages)

    if not all_tables:
        st.error("No tables found in uploaded PDFs.")
        st.stop()

    # Merge
    combined = pd.concat(all_tables, ignore_index=True)
    combined = clean_columns(combined)
    combined = auto_convert_numeric(combined)

    # Remove internal column
    if "__page__" in combined.columns:
        combined.drop(columns=["__page__"], inplace=True)

    # ---------------------------------------
    # ✅ Summary Metrics
    # ---------------------------------------
    st.subheader("📌 Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rows", len(combined))
    col2.metric("Pages With Tables", len(set(all_pages)))

    # Balance summary if column exists
    balance_col_candidates = [c for c in combined.columns if "Balance" in c or "Amount" in c]
    if balance_col_candidates:
        bal_col = balance_col_candidates[0]
        total_balance = combined[bal_col].sum(numeric_only=True)
        avg_balance = combined[bal_col].mean(numeric_only=True)

        col3.metric("Total Balance", f"{total_balance:,.2f}")
        col4.metric("Average Balance", f"{avg_balance:,.2f}")
    else:
        col3.metric("Total Balance", "N/A")
        col4.metric("Average Balance", "N/A")


    # ---------------------------------------
    # ✅ Search & Filter Section
    # ---------------------------------------
    st.subheader("🔍 Search & Filter")
    query = st.text_input("Search across all columns", placeholder="Type to filter…")

    filtered_df = filter_table(combined, query)

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
