import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from utils import generate_example_csv, get_csv_download_link

# Page configuration
st.set_page_config(
    page_title="Review Aspect Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# App title and description
st.title("Customer Review Aspect Analyzer")
st.markdown("""
This application helps product managers analyze aspect and category tagging in customer reviews.
Upload or import review data to see aspects organized by category and gain insights into your review pipeline.

### Features:
- Upload CSV files with review data
- Import data directly from your internal API
- Analyze aspects by category
- Identify underrepresented aspects (< 5%)
- Visualize aspect distributions with charts
- Export results for further analysis
""")

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
    st.warning("3. Analyze Aspects")
    st.markdown("""
    - Categorize aspects
    - Calculate percentages
    - Identify patterns
    """)
with cols[3]:
    st.error("4. Visualize & Export")
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
    
    ### Required CSV Format:
    - review_id: Unique identifier for each review
    - review_text: The text content of the review
    - category: The category assigned to the review
    - aspects: Comma-separated list of aspects found in the review
    """)
    
    # Example data download option
    st.markdown("#### Example Data")
    st.markdown("Download example data to see the expected format:")
    example_data = generate_example_csv()
    example_data.seek(0)
    st.download_button(
        label="Download Example CSV",
        data=example_data.getvalue(),
        file_name="example_reviews.csv",
        mime="text/csv"
    )

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
    st.markdown("### 📊 Analytics & Charts")
    st.markdown("""
    The Analytics & Charts page helps you visualize your review data:
    - See aspects distribution by category
    - Identify underrepresented aspects
    - View percentage breakdowns
    - Export results for further analysis
    
    [Go to Analytics & Charts](/Analytics_Charts)
    """)

with col3:
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