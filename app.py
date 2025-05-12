import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import os
import glob

# Page configuration
st.set_page_config(
    page_title="Review Aspect Analyzer",
    page_icon="📊",
    layout="wide"
)

# App title and description
st.title("Customer Review Aspect Analyzer")
st.markdown("""
This application helps product managers analyze aspect and category tagging in customer reviews.
Upload a CSV file with review data to see aspects organized by category and identify underrepresented aspects.
""")

# Sidebar information
with st.sidebar:
    st.header("Instructions")
    st.markdown("""
    1. Upload a CSV file with these columns:
       - review_id
       - review_text
       - category
       - aspects (comma-separated)
    2. View the analysis table
    3. Use filters to explore specific categories
    4. Export the results as needed
    """)
    
    st.markdown("---")
    st.markdown("**About the Tool**")
    st.markdown("This tool helps identify which aspects are well-represented or underrepresented in your review categories.")

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
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV file</a>'
    return href

# Function to process the uploaded CSV file
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

# File uploader
st.header("1. Upload or Select Review Data")

# Example data download option
st.markdown("Don't have data? Download example data:")
example_data = generate_example_csv()
example_data.seek(0)
st.download_button(
    label="Download Example CSV",
    data=example_data.getvalue(),
    file_name="example_reviews.csv",
    mime="text/csv"
)

# Check for files in the uploads directory (from API)
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create directory if it doesn't exist
api_uploaded_files = glob.glob(os.path.join(UPLOAD_DIR, '*.csv'))

# Create a tab layout for different data input methods
tab1, tab2 = st.tabs(["Upload a File", "API Uploaded Files"])

with tab1:
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
with tab2:
    if api_uploaded_files:
        st.success(f"Found {len(api_uploaded_files)} files uploaded via API")
        selected_api_file = st.selectbox(
            "Select an API-uploaded file to analyze:",
            options=api_uploaded_files,
            format_func=lambda x: os.path.basename(x)
        )
        if selected_api_file:
            st.info(f"Selected file: {os.path.basename(selected_api_file)}")
            # When API file is selected, we'll load it as the uploaded_file
            uploaded_file = selected_api_file
    else:
        st.info("No files have been uploaded via the API yet. Use the API endpoint to upload files.")
        
        # Display API usage information
        with st.expander("API Usage Information"):
            st.markdown("""
            ## API Endpoint
            
            You can upload files programmatically via the API endpoint:
            
            ```
            POST /api/upload
            ```
            
            ### Headers
            - `X-API-Key`: Your API key (set in the environment variables)
            
            ### Request
            - Send the CSV file as a multipart/form-data with key 'file'
            
            ### Example (curl)
            ```bash
            curl -X POST \\
                -H "X-API-Key: your_api_key" \\
                -F "file=@your_reviews.csv" \\
                https://your-app-url/api/upload
            ```
            
            Uploaded files will appear in this tab for analysis.
            """)

# Process data if file is uploaded
if uploaded_file is not None:
    df = process_csv(uploaded_file)
    
    if df is not None:
        st.success(f"Successfully loaded {len(df)} reviews!")
        
        # Display raw data sample with expander
        with st.expander("View Raw Data Sample"):
            st.dataframe(df.head(10))
        
        # Analyze aspects by category
        analysis_df, pivot_df = analyze_aspects(df)
        
        if analysis_df is not None and pivot_df is not None:
            st.header("2. Category & Aspect Analysis")
            
            # Category filter
            st.subheader("Filter by Category")
            categories = df['category'].unique()
            selected_category = st.selectbox(
                "Select a category to focus on",
                options=["All Categories"] + list(categories)
            )
            
            # Display filtered data
            if selected_category == "All Categories":
                filtered_analysis = analysis_df
            else:
                filtered_analysis = analysis_df[analysis_df['category'] == selected_category]
            
            # Highlight low percentage aspects
            def highlight_low_percentage(row):
                if row['is_low_percentage']:
                    return ['background-color: #FFCCCC'] * len(row)
                return [''] * len(row)
            
            # Format percentage values
            filtered_analysis['percentage'] = filtered_analysis['percentage'].round(2).astype(str) + '%'
            
            # Display analysis table
            st.subheader("Aspect Analysis Table")
            st.markdown("Aspects appearing in less than 5% of reviews are highlighted in red.")
            
            # Create simplified view of data for display
            display_cols = ['category', 'aspect', 'count', 'total_reviews', 'percentage']
            
            # Create a plain table display for all data
            st.markdown("<h3>Analysis Results</h3>", unsafe_allow_html=True)
            
            # Group data by is_low_percentage status for easier display
            # Convert is_low_percentage to Python boolean values to avoid pandas Series issues
            is_low_mask = [bool(val) for val in filtered_analysis['is_low_percentage']]
            is_normal_mask = [not val for val in is_low_mask]
            
            # Since we have issues with boolean masks, let's take a different approach
            # Create lists to store the data for low percentage and normal aspects
            low_aspects_data = []
            normal_aspects_data = []
            
            # Manually iterate through filtered_analysis and separate the data
            for i in range(len(filtered_analysis)):
                row = filtered_analysis.iloc[i]
                row_data = {col: row[col] for col in display_cols}
                
                if row['is_low_percentage']:
                    low_aspects_data.append(row_data)
                else:
                    normal_aspects_data.append(row_data)
            
            # Display low percentage aspects with a warning
            if low_aspects_data:
                st.markdown("##### Low Percentage Aspects (< 5%)")
                st.markdown("These aspects appear in less than 5% of reviews for their category:")
                st.dataframe(pd.DataFrame(low_aspects_data), use_container_width=True)
            
            # Display normal aspects
            if normal_aspects_data:
                st.markdown("##### Regular Aspects")
                st.dataframe(pd.DataFrame(normal_aspects_data), use_container_width=True)
            
            # Display pivot table for all categories
            if selected_category == "All Categories" and len(categories) > 1:
                st.subheader("Aspect Percentage by Category (Pivot Table)")
                
                # Format the pivot table percentages
                formatted_pivot = pivot_df.copy()
                for category in categories:
                    if category in formatted_pivot.columns:
                        formatted_pivot[category] = formatted_pivot[category].apply(
                            lambda x: f"{x:.2f}%" if not np.isnan(x) else "0.00%"
                        )
                
                st.dataframe(formatted_pivot)
            
            # Export options
            st.header("3. Export Analysis")
            
            export_type = st.radio(
                "Select export format:",
                ["Current filtered view", "Complete analysis", "Pivot table"]
            )
            
            if st.button("Generate Export"):
                # Define export columns (without is_low_percentage)
                export_columns = ['category', 'aspect', 'count', 'total_reviews', 'percentage']
                
                if export_type == "Current filtered view":
                    export_df = filtered_analysis[export_columns]
                    filename = f"aspect_analysis_{selected_category.replace(' ', '_')}.csv"
                elif export_type == "Complete analysis":
                    export_df = analysis_df[export_columns]
                    filename = "complete_aspect_analysis.csv"
                else:  # Pivot table
                    export_df = pivot_df
                    filename = "aspect_pivot_analysis.csv"
                
                st.markdown(get_csv_download_link(export_df, filename), unsafe_allow_html=True)
        
        else:
            st.error("Could not analyze the data. Please check the format of your CSV file.")
else:
    st.info("Please upload a CSV file to begin analysis.")

# Footer
st.markdown("---")
st.markdown("Review Aspect Analyzer Tool")
