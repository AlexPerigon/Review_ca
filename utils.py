import os
import pandas as pd
import io
import base64
import json
import ast
import datetime
import streamlit as st
from collections import Counter
from internal_api import InternalAPIClient


# Function to prepare example CSV data
def generate_example_csv():
    # Read the CSV from the file path
    df = pd.read_csv("example_data/review_categories.csv")

    # Convert DataFrame to CSV in memory (StringIO)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return output


# Function to download dataframe as CSV
def get_csv_download_link(df, filename="analysis_export.csv"):
    """Generates a link to download the dataframe as a CSV file"""
    if df is None or df.empty:
        return "No data to download"

    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV file</a>'
    return href


def get_json_download_link(data, filename="analysis_export.json"):
    """Generates a link to download data as a JSON file."""
    if data is None:
        return "No data to download"

    try:
        if isinstance(data, pd.DataFrame):
            json_str = data.to_json(orient='records', date_format='iso')
        else:
            def json_serial(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
            json_str = json.dumps(data, default=json_serial)

        if not isinstance(json_str, str):
            raise ValueError("JSON serialization failed, got non-string output.")

        b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        href = f'<a href="data:file/json;base64,{b64}" download="{filename}">Download JSON file</a>'
        return href
    except Exception as e:
        return f"Error generating JSON download link: {str(e)}"


# Function to process a CSV file
def process_csv(uploaded_file):
    """Process the uploaded CSV file and return a DataFrame
    
    Parameters:
    -----------
    uploaded_file : Union[UploadedFile, str]
        Either a Streamlit UploadedFile object or a path to a file
    
    Returns:
    --------
    DataFrame or None
        The processed DataFrame or None if an error occurred
    """
    try:
        # Check if uploaded_file is a string (path to a file uploaded via API)
        if isinstance(uploaded_file, str):
            df = pd.read_csv(uploaded_file)
        else:
            # Regular Streamlit file upload
            df = pd.read_csv(uploaded_file)

        # Check if required columns exist
        required_columns = ['review_id', 'review_text', 'category', 'aspects']
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]

        if missing_columns:
            st.error(
                f"Error: The following required columns are missing: {', '.join(missing_columns)}"
            )
            return None

        # Convert aspects column to list if it's string
        if df['aspects'].dtype == 'object':
            # Split aspects string into a list
            df['aspects_list'] = df['aspects'].str.split(',').apply(
                lambda x: [item.strip() for item in x]
                if isinstance(x, list) else [])
        else:
            st.error(
                "Error: The 'aspects' column format is incorrect. It should be a comma-separated string."
            )
            return None

        return df

    except Exception as e:
        st.error(f"Error processing the file: {str(e)}")
        return None


# Function to analyze aspects by category
def analyze_aspects(df):
    """Analyze aspects by category and return analysis DataFrames"""
    if df is None or len(df) == 0:
        return None, None

    # Get unique categories and all aspects
    categories = df['category'].unique()
    all_aspects = set()

    # Collect all unique aspects
    for aspects_list in df['aspects_list']:
        all_aspects.update(aspects_list)

    # Create a DataFrame to store aspect counts and percentages by category
    analysis_data = []

    for category in categories:
        # Get reviews for this category
        category_reviews = df[df['category'] == category]
        total_category_reviews = len(category_reviews)

        # Count aspects in this category
        aspect_counts = {}
        for aspect_list in category_reviews['aspects_list']:
            for aspect in aspect_list:
                aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1

        # Calculate percentages and add to analysis data
        for aspect, count in aspect_counts.items():
            percentage = (count / total_category_reviews) * 100
            is_low = percentage < 5.0  # Flag if aspect appears in less than 5% of reviews

            analysis_data.append({
                'category': category,
                'aspect': aspect,
                'count': count,
                'total_reviews': total_category_reviews,
                'percentage': percentage,
                'is_low_percentage': is_low
            })

    # Create analysis DataFrame
    analysis_df = pd.DataFrame(analysis_data)

    # Create a pivot table for easier viewing
    if not analysis_df.empty:
        pivot_df = analysis_df.pivot_table(index='aspect',
                                           columns='category',
                                           values='percentage',
                                           fill_value=0).reset_index()

        return analysis_df, pivot_df

    return None, None


# Function to get API uploaded files
def get_api_uploaded_files():
    UPLOAD_DIR = 'uploads'
    os.makedirs(UPLOAD_DIR,
                exist_ok=True)  # Create directory if it doesn't exist
    return [
        os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR)
        if f.endswith('.csv')
    ]


# Function to fetch data from internal API
def fetch_internal_api_data(sort_by="id", sort_order="asc"):
    """
    Fetch category data from the internal API
    
    Parameters:
    -----------
    sort_by : str
        Field to sort by
    sort_order : str
        Sort order ('asc' or 'desc')
    use_all_endpoint : bool
        If True, use the /reviewCategory/all endpoint without pagination
        If False, use the paginated endpoint with automatic page fetching
        
    Returns:
    --------
    list or dict
        List of categories or error dict
    """
    api_client = InternalAPIClient()

    return api_client.get_review_categories_paginated(sort_by=sort_by,
                                                      sort_order=sort_order)


def fetch_internal_all_api_data():
    api_client = InternalAPIClient()
    return api_client.get_all_review_categories()


# Get top aspects overall
def get_top_aspects(analysis_df, top_n=10):
    if analysis_df is None or analysis_df.empty:
        return None

    # Group by aspect and sum the counts
    aspect_totals = analysis_df.groupby('aspect')['count'].sum().reset_index()
    aspect_totals = aspect_totals.sort_values('count',
                                              ascending=False).head(top_n)
    return aspect_totals


# Get aspects with low percentage (under 5%) across categories
def get_low_percentage_aspects(analysis_df):
    if analysis_df is None or analysis_df.empty:
        return None

    return analysis_df[analysis_df['is_low_percentage'] == True].sort_values(
        'percentage')


# Calculate aspect distribution by category
def get_aspect_distribution(analysis_df):
    if analysis_df is None or analysis_df.empty:
        return None

    # Group by category and count unique aspects
    category_aspect_counts = analysis_df.groupby(
        'category')['aspect'].nunique().reset_index()
    category_aspect_counts.columns = ['category', 'unique_aspects']

    return category_aspect_counts


# Load the category data from file
@st.cache_data
def load_category_data(file_path="example_data/review_categories.csv", max_rows=500):
    try:
        df = pd.read_csv(file_path)

        # Limit rows to `max_rows` if the dataset is large
        if len(df) > max_rows:
            df = df.sample(n=max_rows, random_state=42)

        # Parse aspects once here
        if 'aspects' in df.columns:
            df['aspects_parsed'] = df['aspects'].apply(
                lambda x: ast.literal_eval(x)
                if isinstance(x, str) and x.strip().startswith("[") else [])

        return df
    except Exception as e:
        st.error(f"Error loading category data: {str(e)}")
        return None


# Analyze aspects across categories
@st.cache_data
def analyze_category_aspects(df):
    """Optimize aspect analysis for large datasets."""
    if df is None or 'aspects_parsed' not in df.columns:
        return None

    aspect_counts = Counter()
    for aspects_list in df['aspects_parsed']:
        if isinstance(aspects_list, list):
            aspect_counts.update(aspects_list)

    aspect_freq = pd.DataFrame({
        'aspect': [aspect for aspect, _ in aspect_counts.most_common()],
        'count': [count for _, count in aspect_counts.most_common()]
    })

    return aspect_freq


# Create a matrix of aspects by category
@st.cache_data
def create_aspect_category_matrix(df, max_aspects=1000, max_categories=500):
    if df is None or 'aspects_parsed' not in df.columns:
        return None

    # Count all aspects
    aspect_counts = Counter()
    for aspects_list in df['aspects_parsed']:
        if isinstance(aspects_list, list):
            aspect_counts.update(aspects_list)

    # Select top aspects and top categories
    top_aspects = [aspect for aspect, _ in aspect_counts.most_common(max_aspects)]
    top_categories = df.nlargest(max_categories, 'aspectsCount')

    # Build matrix data
    matrix_data = []
    for aspect in top_aspects:
        row = {'aspect': aspect}
        for category in top_categories['name']:
            # Get aspects for the category
            aspects_in_category = df.loc[df['name'] == category, 'aspects_parsed'].values
            if aspects_in_category.size > 0 and isinstance(aspects_in_category[0], list):
                row[category] = 1 if aspect in aspects_in_category[0] else 0
            else:
                row[category] = 0
        matrix_data.append(row)

    # Create DataFrame with 'aspect' as a **column**, not index
    matrix = pd.DataFrame(matrix_data)

    return matrix 