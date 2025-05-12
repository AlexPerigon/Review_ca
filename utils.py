import os
import pandas as pd
import numpy as np
import io
import base64
import json
import ast
import datetime
import streamlit as st
from internal_api import InternalAPIClient

# Function to prepare example CSV data
def generate_example_csv():
    data = io.StringIO()
    data.write("review_id,review_text,category,aspects\n")
    data.write("1,This laptop has a great screen but poor battery life.,Electronics,screen quality,battery life\n")
    data.write("2,The camera takes amazing photos even in low light.,Electronics,photo quality,low light performance\n")
    data.write("3,The headphones are comfortable but sound quality is average.,Electronics,comfort,sound quality\n")
    data.write("4,The restaurant had excellent service but the food was mediocre.,Restaurant,service,food quality\n")
    data.write("5,The hotel room was clean but the wifi was slow.,Hotel,cleanliness,wifi speed\n")
    data.write("6,The sneakers are durable but not very comfortable.,Footwear,durability,comfort\n")
    data.write("7,This phone has incredible battery life and fast charging.,Electronics,battery life,charging speed\n")
    data.write("8,The app interface is intuitive but it crashes frequently.,Software,user interface,stability\n")
    data.write("9,The restaurant's ambiance was great but service was slow.,Restaurant,ambiance,service\n")
    data.write("10,This book has engaging characters but a predictable plot.,Books,characters,plot\n")
    return data

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
    """Generates a link to download data as a JSON file
    
    Parameters:
    -----------
    data : dict, list, DataFrame
        The data to convert to JSON and download
    filename : str
        The name of the downloaded file
        
    Returns:
    --------
    str
        HTML link for downloading the JSON data
    """
    if data is None:
        return "No data to download"
        
    try:
        if isinstance(data, pd.DataFrame):
            # Convert DataFrame to dictionary
            # Handle datetime conversion
            json_str = data.to_json(orient='records', date_format='iso')
        else:
            # Convert dict or list to JSON with date handling
            def json_serial(obj):
                """JSON serializer for objects not serializable by default json code"""
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")
                
            json_str = json.dumps(data, default=json_serial)
            
        # Base64 encode the JSON string
        b64 = base64.b64encode(json_str.encode()).decode()
        
        # Create download link
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
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Error: The following required columns are missing: {', '.join(missing_columns)}")
            return None
        
        # Convert aspects column to list if it's string
        if df['aspects'].dtype == 'object':
            # Split aspects string into a list
            df['aspects_list'] = df['aspects'].str.split(',').apply(lambda x: [item.strip() for item in x] if isinstance(x, list) else [])
        else:
            st.error("Error: The 'aspects' column format is incorrect. It should be a comma-separated string.")
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
        pivot_df = analysis_df.pivot_table(
            index='aspect',
            columns='category',
            values='percentage',
            fill_value=0
        ).reset_index()
        
        return analysis_df, pivot_df
    
    return None, None

# Function to get API uploaded files
def get_api_uploaded_files():
    UPLOAD_DIR = 'uploads'
    os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create directory if it doesn't exist
    return [os.path.join(UPLOAD_DIR, f) for f in os.listdir(UPLOAD_DIR) if f.endswith('.csv')]

# Function to fetch data from internal API
def fetch_internal_api_data(sort_by="id", sort_order="asc"):
    api_client = InternalAPIClient()
    return api_client.get_review_categories_paginated(
        sort_by=sort_by,
        sort_order=sort_order
    )

# Get top aspects overall
def get_top_aspects(analysis_df, top_n=10):
    if analysis_df is None or analysis_df.empty:
        return None
    
    # Group by aspect and sum the counts
    aspect_totals = analysis_df.groupby('aspect')['count'].sum().reset_index()
    aspect_totals = aspect_totals.sort_values('count', ascending=False).head(top_n)
    return aspect_totals

# Get aspects with low percentage (under 5%) across categories
def get_low_percentage_aspects(analysis_df):
    if analysis_df is None or analysis_df.empty:
        return None
    
    return analysis_df[analysis_df['is_low_percentage'] == True].sort_values('percentage')

# Calculate aspect distribution by category
def get_aspect_distribution(analysis_df):
    if analysis_df is None or analysis_df.empty:
        return None
    
    # Group by category and count unique aspects
    category_aspect_counts = analysis_df.groupby('category')['aspect'].nunique().reset_index()
    category_aspect_counts.columns = ['category', 'unique_aspects']
    
    return category_aspect_counts

# Load the category data from file
def load_category_data(file_path="example_data/review_categories.csv"):
    """Load and process category data from CSV file"""
    try:
        df = pd.read_csv(file_path)
        
        # Process the 'aspects' column which contains stringified lists
        df['aspects_parsed'] = df['aspects'].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else []
        )
        
        return df
    except Exception as e:
        st.error(f"Error loading category data: {str(e)}")
        return None

# Analyze aspects across categories
def analyze_category_aspects(df):
    """Analyze the distribution of aspects across categories"""
    if df is None:
        return None
    
    # Count categories with no aspects
    categories_no_aspects = df[df['aspectsCount'] == 0]
    
    # Get all unique aspects across all categories
    all_aspects = set()
    aspect_counts = {}
    
    for aspects_list in df['aspects_parsed']:
        for aspect in aspects_list:
            all_aspects.add(aspect)
            aspect_counts[aspect] = aspect_counts.get(aspect, 0) + 1
    
    # Create a DataFrame with aspect frequencies
    aspect_freq = pd.DataFrame({
        'aspect': list(aspect_counts.keys()),
        'count': list(aspect_counts.values())
    }).sort_values('count', ascending=False)
    
    return {
        'all_aspects': all_aspects,
        'aspect_counts': aspect_counts,
        'aspect_freq': aspect_freq,
        'categories_no_aspects': categories_no_aspects
    }

# Create a matrix of aspects by category
def create_aspect_category_matrix(df):
    """Create a matrix showing which aspects are used in which categories"""
    if df is None:
        return None
    
    # Get all unique aspects
    all_aspects = set()
    for aspects_list in df['aspects_parsed']:
        all_aspects.update(aspects_list)
    
    # Create a dictionary of category -> aspects
    category_aspects = {}
    for _, row in df.iterrows():
        if row['aspects_parsed']:
            category_aspects[row['name']] = set(row['aspects_parsed'])
        else:
            category_aspects[row['name']] = set()
    
    # Create a matrix (aspects as rows, categories as columns)
    matrix_data = []
    for aspect in sorted(all_aspects):
        row = {'aspect': aspect}
        for category, aspects in category_aspects.items():
            row[category] = 1 if aspect in aspects else 0
        matrix_data.append(row)
    
    return pd.DataFrame(matrix_data)