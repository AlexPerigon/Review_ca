import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import json
import base64
import ast
from utils import fetch_internal_api_data, get_csv_download_link, get_json_download_link

# Page configuration
st.set_page_config(
    page_title="Data Upload - Review Aspect Analyzer",
    page_icon="📤",
    layout="wide"
)

# App title and description
st.title("Data Upload")
st.markdown("""
Upload your review data to start the analysis. You can upload a CSV file directly,
import from our internal API, or send data programmatically via our API.
""")

# Create tabs for different upload methods
tabs = st.tabs(["CSV Upload", "Import from API", "API Integration"])

# Tab 1: CSV Upload
with tabs[0]:
    st.header("Upload CSV File")
    
    # Instructions
    st.markdown("""
    ### CSV Format Requirements
    Your CSV file should include the following columns:
    - `review_id`: Unique identifier for each review
    - `review_text`: The full text of the review
    - `category`: Product/service category the review belongs to
    - `aspects`: Comma-separated list of aspects mentioned in the review
    
    Example row: `101,Great product with excellent battery life,Electronics,battery,price,design`
    """)
    
    # Use example data option
    if st.checkbox("Use example data for testing"):
        st.markdown("Using example data with pre-defined reviews and aspects.")
        from utils import generate_example_csv
        example_data = generate_example_csv()
        
        # Create a download link for the example data
        st.download_button(
            label="Download Example CSV",
            data=example_data.getvalue(),
            file_name="example_reviews.csv",
            mime="text/csv"
        )
        
        # Process the example data
        example_data.seek(0)  # Reset position to start of stream
        df = pd.read_csv(example_data)
        
        st.success("✅ Example data loaded successfully!")
        
        # Display data
        st.subheader("Data Preview")
        st.dataframe(df.head())
        
        # Process aspects
        if 'aspects' in df.columns:
            df['aspects_list'] = df['aspects'].str.split(',')
        
        # Option to save to session state for analysis
        if st.button("Use Example Data for Analysis"):
            st.session_state['uploaded_data'] = df
            st.success("✅ Example data saved for analysis!")
            
            # Set redirection in session state
            if 'redirect_to' not in st.session_state:
                st.session_state['redirect_to'] = '/Analytics_Charts'
            
            # Auto-navigation
            st.info("You will be automatically redirected to the Analytics page.")
            st.markdown("<meta http-equiv='refresh' content='2; url=/Analytics_Charts'>", unsafe_allow_html=True)
            st.markdown("[Click here if not redirected](/Analytics_Charts)")
    
    else:
        # File uploader
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        
        if uploaded_file is not None:
            # Process the uploaded file
            from utils import process_csv
            df = process_csv(uploaded_file)
            
            if df is None:
                st.error("Failed to process the uploaded file. Please ensure it follows the required format.")
            else:
                st.success("✅ File uploaded and processed successfully!")
                
                # Display data preview
                st.subheader("Data Preview")
                st.dataframe(df.head())
                
                # Display raw data sample with expander
                with st.expander("View Raw Data Sample"):
                    st.dataframe(df.head(10))
                
                # Option to save to session state for analysis
                if st.button("Use This Data for Analysis"):
                    st.session_state['uploaded_data'] = df
                    st.success("✅ Data saved for analysis!")
                    
                    # Set redirection in session state
                    if 'redirect_to' not in st.session_state:
                        st.session_state['redirect_to'] = '/Analytics_Charts'
                    
                    # Auto-navigation button
                    st.info("You will be automatically redirected to the Analytics page.")
                    st.markdown("<meta http-equiv='refresh' content='2; url=/Analytics_Charts'>", unsafe_allow_html=True)
                    st.markdown("[Click here if not redirected](/Analytics_Charts)")

# Tab 2: Import from API
with tabs[1]:
    st.header("Import from APIs")
    
    # API selection dropdown
    api_selection = st.selectbox(
        "Select API Source",
        [
            "Review Categories API (Perigon)", 
            "Custom Categories API (Upload)",
            "Review Data API (Coming Soon)"
        ]
    )
    
    # Show different content based on API selection
    if api_selection == "Review Categories API (Perigon)":
        # Expand section about the API
        with st.expander("About the Perigon Categories API"):
            st.markdown("""
            ### Perigon Review Categories API
            
            This app can connect to the following internal API endpoints:
            
            **Paginated Endpoint**:
            ```
            https://api.perigon.io/v1/internal/ca/reviewCategory/
            ```
            
            **All Categories Endpoint (Non-paginated)**:
            ```
            https://api.perigon.io/v1/internal/ca/reviewCategory/all
            ```
            
            **Authentication**:
            - Both endpoints use the SHARED_SECRET as a query parameter
            
            **Pagination Parameters** (for paginated endpoint only):
            - page (default: 0) - The page number to retrieve
            - size (default: 20) - Number of items per page
            - sortBy (default: "id") - Field to sort by
            - sortOrder (default: "asc") - Sort order
            
            **Response Structure** (paginated endpoint):
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
            
            **Response Structure** (all endpoint):
            ```json
            [
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
            ```
            """)
        
        # Fetch options
        col1, col2 = st.columns(2)
        with col1:
            use_all_endpoint = st.checkbox("Use non-paginated endpoint (/all)", value=True, 
                                      help="If checked, fetches all categories at once instead of paginating. This is more efficient but may take longer for large datasets.")
        with col2:
            use_test_data = st.checkbox("Use test data (no API call)", value=False,
                                   help="If checked, uses example data instead of making an actual API call")
        
        # Only show sorting options if not using all endpoint
        if not use_all_endpoint and not use_test_data:
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
        else:
            # Default values when using all endpoint
            sort_by = "id"
            sort_order = "asc"
        
        # Button to fetch data
        if st.button("Fetch Categories from Perigon API"):
            if use_test_data:
                with st.spinner("Loading test data from example_data/review_categories.csv..."):
                    try:
                        # Load the example data
                        example_file = "example_data/review_categories.csv"
                        categories_df = pd.read_csv(example_file)
                        categories = categories_df.to_dict(orient='records')
                        st.success(f"Successfully loaded {len(categories)} test categories")
                    except Exception as e:
                        st.error(f"Error loading test data: {str(e)}")
                        categories = {"error": f"Failed to load test data: {str(e)}"}
            else:
                with st.spinner(f"Fetching data from Perigon API ({'non-paginated /all' if use_all_endpoint else 'paginated'} endpoint)..."):
                    # Fetch categories from the API using the selected endpoint
                    categories = fetch_internal_api_data(
                        sort_by=sort_by,
                        sort_order=sort_order,
                        use_all_endpoint=use_all_endpoint
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
                    
                    # Save the data to file for later use (cached)
                    if not categories_df.empty:
                        # Create directory if it doesn't exist
                        os.makedirs("example_data", exist_ok=True)
                        
                        # Save to file
                        categories_df.to_csv("example_data/review_categories.csv", index=False)
                        st.success("✅ Saved categories data to file for analytics")
                        
                        # Show a preview of the data
                        st.subheader("Category Data Preview")
                        st.dataframe(categories_df)
                        
                        # Store in session state for immediate use
                        st.session_state['category_data'] = categories_df
                        
                        # Set redirection in session state
                        if 'redirect_to' not in st.session_state:
                            st.session_state['redirect_to'] = '/Category_Analysis'
                        
                        # Auto-navigation
                        st.info("You will be automatically redirected to the Category Analysis page.")
                        st.markdown("<meta http-equiv='refresh' content='2; url=/Category_Analysis'>", unsafe_allow_html=True)
                        st.markdown("[Click here if not redirected](/Category_Analysis)")
    
    elif api_selection == "Custom Categories API (Upload)":
        st.subheader("Upload Categories CSV/JSON File")
        st.markdown("""
        Upload your own category data in CSV or JSON format. The file should have the following columns:
        - id: Unique identifier for the category
        - name: Category name
        - aspectsCount: Number of aspects in the category
        - aspects: List of aspects (as a string representation of an array)
        """)
        
        # Option to use example data for testing
        use_example_data = st.checkbox("Use example data for testing", value=False, 
                               help="Use the included example_data/review_categories.csv file for testing")
        
        if use_example_data:
            st.success("✅ Using example category data from example_data/review_categories.csv")
            
            try:
                # Load the example data
                example_file = "example_data/review_categories.csv"
                df = pd.read_csv(example_file)
                
                # Display a preview
                st.subheader("Example Data Preview")
                st.dataframe(df.head(5))
                
                # Option to use for analysis
                if st.button("Use This Example Data for Analysis"):
                    # Store in session state
                    st.session_state['category_data'] = df
                    
                    # Auto-navigate to analysis page
                    st.success("✅ Example data loaded for analysis! Redirecting to Category Analysis page...")
                    st.markdown("<meta http-equiv='refresh' content='2; url=/Category_Analysis'>", unsafe_allow_html=True)
                    st.markdown("[Click here if not redirected](/Category_Analysis)")
            
            except Exception as e:
                st.error(f"Error loading example data: {str(e)}")
        
        # File uploader (only show if not using example data)
        uploaded_file = None
        if not use_example_data:
            uploaded_file = st.file_uploader("Choose a CSV or JSON file", type=["csv", "json"])
        
        if uploaded_file is not None:
            try:
                # Check file type and process accordingly
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    file_type = "CSV"
                else:
                    df = pd.read_json(uploaded_file)
                    file_type = "JSON"
                
                # Display success message
                st.success(f"✅ Successfully loaded {file_type} file: {uploaded_file.name}")
                
                # Process aspects column if it exists
                if 'aspects' in df.columns:
                    try:
                        df['aspects_parsed'] = df['aspects'].apply(
                            lambda x: json.loads(x) if isinstance(x, str) and x.strip() else []
                        )
                    except:
                        # Try with ast literal eval as fallback
                        import ast
                        df['aspects_parsed'] = df['aspects'].apply(
                            lambda x: ast.literal_eval(x) if isinstance(x, str) and x.strip() else []
                        )
                
                # Save to file
                os.makedirs("example_data", exist_ok=True)
                filename = f"custom_categories_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df.to_csv(f"example_data/{filename}", index=False)
                
                # Show data preview
                st.subheader("Data Preview")
                st.dataframe(df.head(10))
                
                # Store in session state
                st.session_state['category_data'] = df
                
                # Auto navigation
                st.success("Categories data saved successfully. Redirecting to analysis...")
                st.markdown("<meta http-equiv='refresh' content='2; url=/Category_Analysis'>", unsafe_allow_html=True)
                st.markdown("[Click here if not redirected](/Category_Analysis)")
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                st.info("Please ensure your file is in the correct format.")
    
    else:  # Coming Soon option
        st.info("This API source is coming soon. Please check back later.")

# Tab 3: API Integration
with tabs[2]:
    st.header("API Integration")
    
    st.markdown("""
    ### Upload data programmatically via our API
    
    You can send data to this application programmatically using our REST API. 
    This allows you to integrate with your existing systems and automate data analysis.
    
    **Base URL**: `http://localhost:5001`
    
    #### API Endpoints
    
    | Method | Endpoint | Description |
    |--------|----------|-------------|
    | POST | `/api/upload` | Upload review data (CSV) |
    | POST | `/api/upload/review_categories/csv` | Upload category data (CSV) |
    | POST | `/api/upload/review_categories/json` | Upload category data (JSON) |
    | GET | `/api/analytics/categories` | Get category analytics |
    | GET | `/api/analytics/reviews` | Get review analytics |
    """)
    
    # API Examples with tabs
    api_examples = st.tabs(["Upload CSV", "Upload JSON", "Get Analytics"])
    
    with api_examples[0]:
        st.markdown("""
        #### Upload Categories CSV Example
        
        ```bash
        # Upload a CSV file with category data
        curl -X POST -H "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990" \\
             -F "file=@example_data/review_categories.csv" \\
             http://localhost:5001/api/upload/review_categories/csv
        ```
        """)
        
        # Add a button to test this API
        if st.button("Test Upload CSV API", key="test_upload_csv"):
            with st.spinner("Testing the API - Uploading CSV..."):
                # Use subprocess to run the curl command
                import subprocess
                import json
                
                try:
                    cmd = [
                        "curl", "-s", "-X", "POST", 
                        "-H", "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990",
                        "-F", "file=@example_data/review_categories.csv",
                        "http://localhost:5001/api/upload/review_categories/csv"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        try:
                            data = json.loads(result.stdout)
                            st.success("API call successful!")
                            st.json(data)
                        except json.JSONDecodeError:
                            st.error("API response was not valid JSON")
                            st.text(result.stdout)
                    else:
                        st.error(f"API call failed: {result.stderr}")
                except Exception as e:
                    st.error(f"Error executing API call: {str(e)}")
    
    with api_examples[1]:
        st.markdown("""
        #### Upload Categories JSON Example
        
        ```bash
        # Upload category data in JSON format
        curl -X POST -H "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990" \\
             -H "Content-Type: application/json" \\
             -d '[{"id":1,"name":"Test Category","aspectsCount":2,"aspects":["Quality","Price"]}]' \\
             http://localhost:5001/api/upload/review_categories/json
        ```
        """)
        
        # Add a button to test this API
        if st.button("Test Upload JSON API", key="test_upload_json"):
            with st.spinner("Testing the API - Uploading JSON..."):
                import subprocess
                import json
                
                try:
                    # Create a simple JSON payload
                    payload = json.dumps([{
                        "id": 999, 
                        "name": "Test Category", 
                        "aspectsCount": 3,
                        "aspects": ["Quality", "Price", "Support"]
                    }])
                    
                    cmd = [
                        "curl", "-s", "-X", "POST",
                        "-H", "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990",
                        "-H", "Content-Type: application/json",
                        "-d", payload,
                        "http://localhost:5001/api/upload/review_categories/json"
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        try:
                            data = json.loads(result.stdout)
                            st.success("API call successful!")
                            st.json(data)
                        except json.JSONDecodeError:
                            st.error("API response was not valid JSON")
                            st.text(result.stdout)
                    else:
                        st.error(f"API call failed: {result.stderr}")
                except Exception as e:
                    st.error(f"Error executing API call: {str(e)}")
    
    with api_examples[2]:
        st.markdown("""
        #### Get Category Analytics Example
        
        ```bash
        # Get analytics for categories
        curl -X GET -H "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990" \\
             http://localhost:5001/api/analytics/categories
        ```
        """)
        
        # Add a button to test this API
        if st.button("Test Get Analytics API", key="test_get_analytics"):
            with st.spinner("Testing the API - Getting Analytics..."):
                import subprocess
                import json
                
                try:
                    cmd = [
                        "curl", "-s", "-X", "GET",
                        "-H", "X-API-Key: 8d84126c-4184-4c1f-a7f1-efd247bee990",
                        "http://localhost:5001/api/analytics/categories"
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        try:
                            data = json.loads(result.stdout)
                            st.success("API call successful!")
                            st.json(data)
                        except json.JSONDecodeError:
                            st.error("API response was not valid JSON")
                            st.text(result.stdout)
                    else:
                        st.error(f"API call failed: {result.stderr}")
                except Exception as e:
                    st.error(f"Error executing API call: {str(e)}")
    
    # API authentication information
    st.markdown("""
    #### Authentication
    All API requests require the `X-API-Key` header. Contact the administrator to get your API key.
    """)
    
    # Show API Key (for demo purposes)
    st.warning("For demonstration purposes, your API key is: 8d84126c-4184-4c1f-a7f1-efd247bee990")
    
    # Add some example code
    with st.expander("Python Example Code"):
        st.code("""
import requests

# API configuration
api_key = "YOUR_API_KEY"
base_url = "http://localhost:5001"

# Upload a CSV file
def upload_csv(csv_path):
    headers = {
        "X-API-Key": api_key
    }
    
    with open(csv_path, 'rb') as f:
        files = {
            'file': (csv_path, f, 'text/csv')
        }
        
        response = requests.post(
            f"{base_url}/api/upload",
            headers=headers,
            files=files
        )
        
    return response.json()

# Get analytics
def get_analytics():
    headers = {
        "X-API-Key": api_key
    }
    
    response = requests.get(
        f"{base_url}/api/analytics/reviews",
        headers=headers
    )
    
    return response.json()

# Example usage
csv_path = "reviews.csv"
result = upload_csv(csv_path)
print(result)

analytics = get_analytics()
print(analytics)
""", language="python")
    
    with st.expander("JavaScript Example Code"):
        st.code("""
// Using fetch API in JavaScript
const apiKey = "YOUR_API_KEY";
const baseUrl = "http://localhost:5001";

// Upload a CSV file
async function uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${baseUrl}/api/upload`, {
        method: 'POST',
        headers: {
            'X-API-Key': apiKey
        },
        body: formData
    });
    
    return response.json();
}

// Get analytics
async function getAnalytics() {
    const response = await fetch(`${baseUrl}/api/analytics/reviews`, {
        method: 'GET',
        headers: {
            'X-API-Key': apiKey
        }
    });
    
    return response.json();
}

// Example usage (in an async function)
async function example() {
    const fileInput = document.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    
    const uploadResult = await uploadCSV(file);
    console.log(uploadResult);
    
    const analytics = await getAnalytics();
    console.log(analytics);
}
""", language="javascript")

# Footer
st.markdown("---")
st.caption("Review Aspect Analyzer Tool - Data Upload")