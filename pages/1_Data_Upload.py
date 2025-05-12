import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
import os
import glob
import json
import requests
from internal_api import InternalAPIClient
from utils import (
    generate_example_csv, 
    get_csv_download_link, 
    process_csv, 
    fetch_internal_api_data,
    get_api_uploaded_files
)

# Page configuration
st.set_page_config(
    page_title="Data Upload - Review Aspect Analyzer",
    page_icon="📤",
    layout="wide"
)

# App title and description
st.title("Data Upload Options")
st.markdown("""
This page provides multiple ways to import your review data for analysis.
""")

# Create tabs for different upload methods
tabs = st.tabs([
    "Upload CSV", 
    "Import from API", 
    "API Uploads", 
    "Test API Integration"
])

# Tab 1: CSV Upload
with tabs[0]:
    st.header("Upload CSV File")
    st.markdown("""
    Upload a CSV file containing review data with the required columns:
    - review_id: Unique identifier for each review
    - review_text: The text content of the review
    - category: The category assigned to the review
    - aspects: Comma-separated list of aspects found in the review
    """)
    
    # Example data download option
    with st.expander("Need sample data?"):
        st.markdown("Download example data to see the expected format:")
        example_data = generate_example_csv()
        example_data.seek(0)
        st.download_button(
            label="Download Example CSV",
            data=example_data.getvalue(),
            file_name="example_reviews.csv",
            mime="text/csv"
        )
    
    # File uploader
    uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
    
    if uploaded_file is not None:
        # Process the uploaded file
        df = process_csv(uploaded_file)
        
        if df is not None:
            st.success(f"Successfully loaded {len(df)} reviews!")
            
            # Display raw data sample with expander
            with st.expander("View Raw Data Sample"):
                st.dataframe(df.head(10))
            
            # Option to save to session state for analysis
            if st.button("Use This Data for Analysis"):
                st.session_state['uploaded_data'] = df
                st.success("Data saved for analysis! Go to the Analytics & Charts page to view insights.")
                st.markdown("[Go to Analytics & Charts](/Analytics_Charts)")

# Tab 2: Import from API
with tabs[1]:
    st.header("Import from Internal API")
    
    # Expand section about the API
    with st.expander("About the Internal API Integration"):
        st.markdown("""
        ### Internal API Integration
        
        This app can connect to your internal API endpoint at:
        ```
        https://api.perigon.io/v1/internal/ca/reviewCategory/
        ```
        
        **Authentication**:
        - Uses the SHARED_SECRET as a query parameter
        
        **Pagination Parameters**:
        - page (default: 0) - The page number to retrieve
        - size (default: 20) - Number of items per page
        - sortBy (default: "id") - Field to sort by
        - sortOrder (default: "asc") - Sort order
        
        **Response Structure**:
        ```json
        {
          "total": 123,  // Total number of records
          "data": [      // Array of CAReviewCategoryDto objects
            {
              "id": 1,
              "name": "Category Name",
              "createdAt": "2023-01-01T12:00:00Z",
              "updatedAt": "2023-01-02T12:00:00Z",
              "caCategoryId": "cat123",
              "rulesPath": "/path/to/rules",
              "aspects": [
                {"name": "Aspect 1"},
                {"name": "Aspect 2"}
              ]
            },
            // more categories...
          ]
        }
        ```
        """)
    
    # API fetch options
    col1, col2 = st.columns(2)
    with col1:
        sort_by = st.selectbox(
            "Sort by field", 
            options=["id", "name", "createdAt", "updatedAt"],
            index=0
        )
    with col2:
        sort_order = st.selectbox(
            "Sort order", 
            options=["asc", "desc"],
            index=0
        )
    
    # Button to fetch data
    if st.button("Fetch Categories from Internal API"):
        with st.spinner("Fetching data from internal API..."):
            # Fetch categories from the API
            categories = fetch_internal_api_data(
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if isinstance(categories, dict) and "error" in categories:
                st.error(f"Error fetching categories: {categories['error']}")
                if "details" in categories:
                    st.error(f"Details: {categories['details']}")
            else:
                # Successfully fetched categories
                st.success(f"Successfully fetched {len(categories)} categories from the API")
                
                # Convert to DataFrame for easier handling
                categories_df = pd.DataFrame(categories)
                
                # Display the categories in a dataframe
                if not categories_df.empty:
                    # Show a preview of the data
                    st.subheader("Category Data Preview")
                    st.dataframe(categories_df)
                    
                    # Option to save as CSV
                    csv_data = categories_df.to_csv(index=False)
                    csv_b64 = base64.b64encode(csv_data.encode()).decode()
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(
                            f'<a href="data:file/csv;base64,{csv_b64}" download="review_categories.csv">Download Categories as CSV</a>', 
                            unsafe_allow_html=True
                        )
                    
                    with col2:
                        # Option to create a review analysis template
                        if st.button("Create Analysis Template from Categories"):
                            # Create a template CSV with review_id, review_text, category, and aspects columns
                            # using the fetched category names
                            if 'name' in categories_df.columns:
                                categories_list = categories_df['name'].tolist()
                                
                                # Create template data
                                template_data = []
                                for i, category in enumerate(categories_list[:5]):  # Limit to 5 examples
                                    template_data.append({
                                        'review_id': i+1,
                                        'review_text': f"Example review for {category}",
                                        'category': category,
                                        'aspects': "aspect1,aspect2"
                                    })
                                
                                template_df = pd.DataFrame(template_data)
                                
                                # Save template as CSV
                                template_csv = template_df.to_csv(index=False)
                                template_b64 = base64.b64encode(template_csv.encode()).decode()
                                
                                st.success("Created analysis template based on your categories!")
                                st.markdown(
                                    f'<a href="data:file/csv;base64,{template_b64}" download="review_analysis_template.csv">Download Analysis Template</a>', 
                                    unsafe_allow_html=True
                                )

# Tab 3: API Uploads
with tabs[2]:
    st.header("API Uploads")
    st.markdown("""
    Files uploaded through the API endpoint will appear here. You can select a file to use for analysis.
    """)
    
    # Check for files in the uploads directory (from API)
    api_uploaded_files = get_api_uploaded_files()
    
    if api_uploaded_files:
        st.success(f"Found {len(api_uploaded_files)} files uploaded via API")
        
        selected_api_file = st.selectbox(
            "Select an API-uploaded file to analyze:",
            options=api_uploaded_files,
            format_func=lambda x: os.path.basename(x)
        )
        
        if selected_api_file:
            st.info(f"Selected file: {os.path.basename(selected_api_file)}")
            
            # Process the selected file
            df = process_csv(selected_api_file)
            
            if df is not None:
                st.success(f"Successfully loaded {len(df)} reviews from the API-uploaded file!")
                
                # Display raw data sample with expander
                with st.expander("View Raw Data Sample"):
                    st.dataframe(df.head(10))
                
                # Option to save to session state for analysis
                if st.button("Use This API Data for Analysis"):
                    st.session_state['uploaded_data'] = df
                    st.success("API data saved for analysis! Go to the Analytics & Charts page to view insights.")
                    st.markdown("[Go to Analytics & Charts](/Analytics_Charts)")
    else:
        st.warning("No files have been uploaded via the API yet.")
        
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
                http://your-app-url/api/upload
            ```
            
            Uploaded files will appear in this tab for analysis.
            """)

# Tab 4: Test API Integration
with tabs[3]:
    st.header("Test API Integration")
    st.markdown("""
    This tab allows you to test the API integration by making direct requests to the API endpoints.
    """)
    
    # Test API options
    api_test_option = st.radio(
        "Select an API to test",
        options=[
            "Internal API (GET /ca/reviewCategory/)",
            "Upload API (POST /api/upload)"
        ]
    )
    
    if api_test_option == "Internal API (GET /ca/reviewCategory/)":
        st.subheader("Test Internal API Connection")
        
        # Parameters for the internal API
        with st.form("internal_api_test_form"):
            # Form for testing internal API
            st.markdown("#### Request Parameters")
            
            col1, col2 = st.columns(2)
            with col1:
                test_sort_by = st.selectbox(
                    "sortBy", 
                    options=["id", "name", "createdAt", "updatedAt"],
                    index=0
                )
            with col2:
                test_sort_order = st.selectbox(
                    "sortOrder", 
                    options=["asc", "desc"],
                    index=0
                )
            
            col1, col2 = st.columns(2)
            with col1:
                test_page = st.number_input("page", min_value=0, value=0)
            with col2:
                test_size = st.number_input("size", min_value=1, max_value=100, value=10)
            
            submit_button = st.form_submit_button("Send Test Request")
            
            if submit_button:
                with st.spinner("Sending request to internal API..."):
                    # Construct the request
                    api_client = InternalAPIClient()
                    response = api_client.get_review_categories(
                        page=test_page,
                        size=test_size,
                        sort_by=test_sort_by,
                        sort_order=test_sort_order
                    )
                    
                    # Display the results
                    st.subheader("API Response")
                    if isinstance(response, dict) and "error" in response:
                        st.error(f"Error from API: {response['error']}")
                        if "details" in response:
                            st.error(f"Details: {response['details']}")
                    else:
                        st.success("Successfully received response from the API")
                        
                        # Show the raw response
                        with st.expander("View Raw API Response"):
                            st.json(response)
                        
                        # Show data count if available
                        if "total" in response:
                            st.metric("Total Records", response["total"])
                        
                        # Show data if available
                        if "data" in response and response["data"]:
                            st.subheader("Data Preview")
                            st.dataframe(pd.DataFrame(response["data"]).head(10))
    
    else:  # Upload API test
        st.subheader("Test Upload API")
        st.markdown("""
        This form allows you to test uploading a file via the API endpoint without using curl or external tools.
        """)
        
        # Form for testing upload API
        with st.form("upload_api_test_form"):
            st.markdown("#### Upload Test File")
            
            # File upload field
            test_file = st.file_uploader("Select a CSV file to upload", type=["csv"])
            
            # API key field
            api_key = st.text_input("API Key", value=os.environ.get("API_KEY", ""))
            
            submit_button = st.form_submit_button("Send Upload Request")
            
            if submit_button:
                if not test_file:
                    st.error("Please select a file to upload")
                elif not api_key:
                    st.error("Please enter an API key")
                else:
                    with st.spinner("Sending upload request..."):
                        try:
                            # Construct the upload request
                            url = "http://localhost:5001/api/upload"
                            headers = {"X-API-Key": api_key}
                            files = {"file": test_file}
                            
                            # Send the request
                            response = requests.post(url, headers=headers, files=files)
                            
                            # Display the result
                            st.subheader("API Response")
                            
                            try:
                                response_json = response.json()
                                st.json(response_json)
                                
                                if response.status_code == 200:
                                    st.success(f"File successfully uploaded with status code: {response.status_code}")
                                    if "row_count" in response_json:
                                        st.metric("Rows Processed", response_json["row_count"])
                                else:
                                    st.error(f"Upload failed with status code: {response.status_code}")
                            except:
                                st.error(f"Could not parse JSON response. Status code: {response.status_code}")
                                st.text(response.text)
                        
                        except Exception as e:
                            st.error(f"Error sending request: {str(e)}")
                            st.info("Make sure the API server is running on port 5001")