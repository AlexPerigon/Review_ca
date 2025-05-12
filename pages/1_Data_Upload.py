import streamlit as st
import pandas as pd
import os
import json
import ast
from utils import fetch_internal_api_data, fetch_internal_all_api_data

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

with tabs[0]:
    st.header("Upload CSV File")

    # Instructions
    st.markdown("""
    ### CSV Format Requirements
    Your CSV file should include the following columns:
    - `id` or `review_id`: Unique identifier
    - `name` or `review_text`: Review category or full review text
    - `category` *(optional)*: Product/service category
    - `aspects`: Either:
        - Comma-separated list like `battery,price,design`, **or**
        - Python list string like `['Product/Price', 'Service/Staff']`
    """)

    # Use example data option
    if st.checkbox("Use example data instead"):
        st.markdown("Using example data with pre-defined reviews and aspects.")
        from utils import generate_example_csv
        example_data = generate_example_csv()

        # Download link
        st.download_button(
            label="Download Example CSV",
            data=example_data.getvalue(),
            file_name="example_reviews.csv",
            mime="text/csv"
        )

        # Load and process
        example_data.seek(0)
        df = pd.read_csv(example_data)

        st.success("✅ Example data loaded successfully!")
        st.subheader("Data Preview")
        st.dataframe(df)

        # Parse aspects
        if 'aspects' in df.columns:
            def parse_aspects(val):
                try:
                    if val.startswith("[") and val.endswith("]"):
                        return ast.literal_eval(val)
                    return [a.strip() for a in val.split(',') if a.strip()]
                except Exception:
                    return []

            df['aspects_list'] = df['aspects'].apply(lambda x: parse_aspects(str(x)) if pd.notnull(x) else [])

        if st.button("Use Example Data for Analysis"):
            if not df.empty:
                os.makedirs("example_data", exist_ok=True)
                data_file = "example_data/review_categories.csv"
                df.to_csv(data_file, index=False)

                num_rows = df.shape[0]

                st.success(f"✅ Full categories data ({num_rows} records) saved to file.")

                st.subheader("Category Data Preview")
                st.dataframe(df.head(100))  # Just show first 100 for performance

                # Save only file path, not entire dataframe
                st.session_state['category_data_path'] = data_file

                if 'redirect_to' not in st.session_state:
                    st.session_state['redirect_to'] = '/Category_Analysis'

                st.info("You will be automatically redirected to the Category Analysis page.")
                st.markdown("<meta http-equiv='refresh' content='2; url=/Category_Analysis'>", unsafe_allow_html=True)
                st.markdown("[Click here if not redirected](/Category_Analysis)")

    else:
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is not None:
            from utils import process_csv  # Optional: you can inline the logic if you prefer
            df = pd.read_csv(uploaded_file)

            # Parse aspects
            if 'aspects' in df.columns:
                def parse_aspects(val):
                    try:
                        if val.startswith("[") and val.endswith("]"):
                            return ast.literal_eval(val)
                        return [a.strip() for a in val.split(',') if a.strip()]
                    except Exception:
                        return []

                df['aspects_list'] = df['aspects'].apply(lambda x: parse_aspects(str(x)) if pd.notnull(x) else [])

            st.success("✅ File uploaded and processed successfully!")

            st.subheader("Data Preview")
            st.dataframe(df.head())

            with st.expander("View Raw Data Sample"):
                st.dataframe(df.head(10))

            if st.button("Use This Data for Analysis"):
                st.session_state['uploaded_data'] = df
                st.success("✅ Data saved for analysis!")

                if 'redirect_to' not in st.session_state:
                    st.session_state['redirect_to'] = '/Analytics_Charts'

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
            "Review Categories API paginated (Perigon)", 
            "Review Categories API all (Perigon)",
            "Custom Categories API (Upload)",
        ]
    )
    
    # Show different content based on API selection
    if api_selection == "Review Categories API paginated (Perigon)":
        # Expand section about the API
        with st.expander("About the Perigon Categories API"):
            st.markdown("""
            ### Perigon Review Categories API
            
            This app can connect to your internal API endpoints at:
            
            **Standard endpoint (with pagination)**
            ```
            https://api.perigon.io/v1/internal/ca/reviewCategory/
            ```
            
            **All categories endpoint (no pagination)**
            ```
            https://api.perigon.io/v1/internal/ca/reviewCategory/all
            ```
            
            **Authentication**:
            - Uses the SHARED_SECRET as a query parameter
            
            **Pagination Parameters** (standard endpoint only):
            - page (default: 0) - The page number to retrieve
            - size (default: 20) - Number of items per page
            - sortBy (default: "id") - Field to sort by
            - sortOrder (default: "asc") - Sort order
            
            **Response Structure** (standard endpoint):
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
        col1, col2, col3 = st.columns(3)
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
        fetch_button_label = "Fetch Categories (paginated)"
        if st.button(fetch_button_label):
            with st.spinner("Fetching data from Perigon API..."):
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
                    
                    # Save the data to file for later use (cached)
                    if not categories_df.empty:
                        os.makedirs("example_data", exist_ok=True)
                        data_file = "example_data/review_categories.csv"
                        categories_df.to_csv(data_file, index=False)

                        num_rows = categories_df.shape[0]

                        st.success(f"✅ Full categories data ({num_rows} records) saved to file.")

                        st.subheader("Category Data Preview")
                        st.dataframe(categories_df.head(100))  # Just show first 100 for performance

                        # Save only file path, not entire dataframe
                        st.session_state['category_data_path'] = data_file

                        if 'redirect_to' not in st.session_state:
                            st.session_state['redirect_to'] = '/Category_Analysis'

                        st.info("You will be automatically redirected to the Category Analysis page.")
                        st.markdown("<meta http-equiv='refresh' content='2; url=/Category_Analysis'>", unsafe_allow_html=True)
                        st.markdown("[Click here if not redirected](/Category_Analysis)")

    elif api_selection == "Review Categories API all (Perigon)":
        # Expand section about the API
        with st.expander("About the Perigon All Categories API"):
            st.markdown("""
            ### Perigon Review Categories API (All)
        
            This app connects to the "all categories" endpoint (no pagination):
        
            **Endpoint**:
            ```
            https://api.perigon.io/v1/internal/ca/reviewCategory/all
            ```
        
            **Authentication**:
            - Uses the SHARED_SECRET as a query parameter
        
            **Response Structure**:
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
        
        fetch_button_label = "Fetch All Categories"
        if st.button(fetch_button_label):
            with st.spinner("Fetching all categories from Perigon API..."):
                categories = fetch_internal_all_api_data()

                if isinstance(categories, dict) and "error" in categories:
                    st.error(f"Error fetching categories: {categories['error']}")
                    if "details" in categories:
                        st.error(f"Details: {categories['details']}")
                else:
                    st.success(f"Successfully fetched {len(categories)} categories from the API")
                    categories_df = pd.DataFrame(categories)

                    if not categories_df.empty:
                        os.makedirs("example_data", exist_ok=True)
                        data_file = "example_data/review_categories.csv"
                        categories_df.to_csv(data_file, index=False)

                        num_rows = categories_df.shape[0]

                        st.success(f"✅ Full categories data ({num_rows} records) saved to file.")

                        st.subheader("Category Data Preview")
                        st.dataframe(categories_df.head(100))  # Just show first 100 for performance

                        # Save only file path, not entire dataframe
                        st.session_state['category_data_path'] = data_file

                        if 'redirect_to' not in st.session_state:
                            st.session_state['redirect_to'] = '/Category_Analysis'

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
        
        # File uploader
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
    
    #### Upload CSV data via API:
    
    ```bash
    curl -X POST -H "X-API-Key: YOUR_API_KEY" \\
         -F "file=@your_file.csv" \\
         http://localhost:5001/api/upload
    ```
    
    #### API Endpoints
    
    | Method | Endpoint | Description |
    |--------|----------|-------------|
    | POST | `/api/upload` | Upload review data (CSV) |
    | POST | `/api/upload/review_categories/csv` | Upload category data (CSV) |
    | POST | `/api/upload/review_categories/json` | Upload category data (JSON) |
    | GET | `/api/analytics/categories` | Get category analytics |
    | GET | `/api/analytics/reviews` | Get review analytics |
    
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
def upload_csv(file_path):
    headers = {
        "X-API-Key": api_key
    }
    
    with open(file_path, 'rb') as f:
        files = {
            'file': (file_path, f, 'text/csv')
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