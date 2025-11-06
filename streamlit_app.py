import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(
    page_title="Last Balance Report PDF Extractor",
    layout="wide",
    page_icon="📄",
)

st.title("📄 Last Balance Report PDF Table Extractor")
st.write("Upload a PDF and extract tables from all pages automatically.")

# --- Sidebar ---
st.sidebar.header("Settings")
show_raw_tables = st.sidebar.checkbox("Show page-level tables", False)
clean_column_names = st.sidebar.checkbox("Clean column names", True)

# --- File Upload ---
uploaded = st.file_uploader("Upload Pdf file", type=["pdf"])

def extract_pdf_tables(pdf_bytes):
    tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table)
                df.columns = df.iloc[0]      # first row = header
                df = df[1:]                  # remove header row
                df["__page__"] = page_no
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

# --- Processing ---
if uploaded:
    pdf_bytes = uploaded.read()
    
    with st.spinner("Extracting tables from PDF…"):
        tables = extract_pdf_tables(pdf_bytes)

    if not tables:
        st.error("No tables found in the PDF.")
        st.stop()

    st.success(f"✅ Extracted {len(tables)} tables from {len(set(t.__len__() for t in tables))} pages")

    # Combined table
    combined = pd.concat(tables, ignore_index=True)

    if clean_column_names:
        combined = clean_columns(combined)

    st.subheader("📊 Combined Extracted Data")
    st.dataframe(combined, use_container_width=True)

    # --- Export buttons ---
    st.download_button(
        "⬇️ Download CSV",
        combined.to_csv(index=False).encode("utf-8"),
        "sbgen_extracted.csv",
        "text/csv",
    )

    excel_buffer = io.BytesIO()
    combined.to_excel(excel_buffer, index=False)
    st.download_button(
        "⬇️ Download Excel",
        excel_buffer.getvalue(),
        "sbgen_extracted.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # --- Optional Page-level views ---
    if show_raw_tables:
        st.subheader("📄 Page-level table preview")
        for i, df in enumerate(tables, start=1):
            st.markdown(f"### Page {i}")
            st.dataframe(df, use_container_width=True)
