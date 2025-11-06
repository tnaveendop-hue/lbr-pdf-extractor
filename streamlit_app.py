import streamlit as st
import pdfplumber
import pandas as pd
import io
import os

st.set_page_config(page_title="Last Balance Report PDF Extractor", layout="wide")

st.title("📄 LBR PDF Table Extractor")

uploaded = st.file_uploader("Upload a PDF file", type=["pdf"])

def extract_pdf_tables(pdf_bytes):
    tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table)
                df.columns = df.iloc[0]      # first row = header
                df = df[1:]                  # remove header row
                tables.append(df)
    return tables

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
        tables = extract_pdf_tables(pdf_bytes)

    if not tables:
        st.error("No tables found in the PDF.")
        st.stop()

    # Combine
    combined = pd.concat(tables, ignore_index=True)
    combined = clean_columns(combined)

    total_rows = len(combined)
    total_pages_with_tables = len({df["__page__"].iloc[0] for df in tables})

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
