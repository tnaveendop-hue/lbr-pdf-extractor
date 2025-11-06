import streamlit as st
import pdfplumber
import pandas as pd
import io
import os

st.set_page_config(
    page_title="Last Balance Report Extractor",
    layout="wide",
    page_icon="📄",
)

st.title("📄 Last Balance Report Extractor")
st.write("Upload your Last Balance Report PDF and extract all data in clean tabular form.")

uploaded = st.file_uploader("Upload PDF file", type=["pdf"])

def extract_pdf_tables(pdf_bytes):
    tables = []
    pages_with_data = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table)
                df.columns = df.iloc[0]      # first row = headers
                df = df[1:]                  # remove header row
                pages_with_data.append(page_no)
                tables.append(df)

    return tables, pages_with_data

def clean_columns(df):
    df.columns = (
        df.columns
        .str.replace("\n", " ", regex=False)
        .str.replace("  ", " ", regex=False)
        .str.strip()
    )
    return df

if uploaded:
    pdf_bytes = uploaded.read()
    input_filename = os.path.splitext(uploaded.name)[0]

    with st.spinner("Extracting tables from PDF…"):
        tables, pages_with_data = extract_pdf_tables(pdf_bytes)

    if not tables:
        st.error("No tables found in this PDF.")
        st.stop()

    # Combine without __page__
    combined = pd.concat(tables, ignore_index=True)
    combined = clean_columns(combined)

    total_rows = len(combined)
    total_pages_with_tables = len(pages_with_data)

    st.success(
        f"✅ Extracted **{total_rows} rows** from **{total_pages_with_tables} page(s)**"
    )

    st.subheader("📊 Extracted Data")
    st.dataframe(combined, use_container_width=True)

    # Export filenames
    csv_filename = f"{input_filename}_extracted.csv"
    xlsx_filename = f"{input_filename}_extracted.xlsx"

    # CSV download
    st.download_button(
        "⬇️ Download CSV",
        combined.to_csv(index=False).encode("utf-8"),
        csv_filename,
        "text/csv",
    )

    # Excel download
    excel_buffer = io.BytesIO()
    combined.to_excel(excel_buffer, index=False)
    st.download_button(
        "⬇️ Download Excel",
        excel_buffer.getvalue(),
        xlsx_filename,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Optional: Show tables page-by-page (without page column)
    with st.expander("📄 Page-level tables (optional)"):
        for i, df in enumerate(tables, start=1):
            st.markdown(f"### Page {pages_with_data[i-1]}")
            st.dataframe(df, use_container_width=True)
