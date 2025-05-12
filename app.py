import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from utils import generate_example_csv, get_csv_download_link

# Show a visual workflow
st.subheader("How It Works")
cols = st.columns(4)
with cols[0]:
    st.info("1. Import Data")
    st.markdown("""
    - Upload a CSV file
    - Import from internal API
    - Upload via API endpoint
    """)
with cols[1]:
    st.success("2. Process & Validate")
    st.markdown("""
    - Verify required columns
    - Format checking
    - Data preparation
    """)
with cols[2]:
    st.error("3. Visualize & Export")
    st.markdown("""
    - View analytics charts
    - Filter results
    - Export as CSV
    """)

# Sidebar information
with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    This tool helps identify which aspects are well-represented or underrepresented in your review categories.
    """)

# Information about pages
st.subheader("Pages")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 📤 Data Upload")
    st.markdown("""
    The Data Upload page provides multiple ways to import your review data:
    - Upload CSV files directly from your computer
    - Import data from your internal API
    - Send data via API requests
    
    [Go to Data Upload](/Data_Upload)
    """)

with col2:
    st.markdown("### 🔍 Category Analysis")
    st.markdown("""
    The Category Analysis page focuses on the categories and aspects from your internal API:
    - What aspects are in each category?
    - Which aspects are most/least used?
    - Which categories have no aspects?
    - Visualize aspect distribution across categories
    
    [Go to Category Analysis](/Category_Analysis)
    """)

# Footer
st.markdown("---")
st.caption("Review Aspect Analyzer Tool v1.0")
