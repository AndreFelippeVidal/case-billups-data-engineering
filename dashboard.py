"""Launch the Gold-backed Streamlit analysis and data-quality pages."""

import streamlit as st


st.set_page_config(page_title="Billups transaction analysis", page_icon="📊", layout="wide")

analysis_page = st.Page("app_pages/analysis.py", title="Analysis", icon="📊", default=True)
quality_page = st.Page("app_pages/data_quality.py", title="Data Quality", icon="✅")
st.navigation([analysis_page, quality_page]).run()
