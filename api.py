import os
import json
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify
import io
from utils import (
    process_csv, 
    analyze_aspects, 
    get_top_aspects, 
    get_low_percentage_aspects,
    get_aspect_distribution,
    load_category_data,
    analyze_category_aspects,
    create_aspect_category_matrix
)
from internal_api import InternalAPIClient

# Create Flask app
app = Flask(__name__)

# Configuration - you'll need to set this in environment variables
API_KEY = os.environ.get('API_KEY', 'default_dev_key')  # Default for development only

# Directory for storing uploaded files
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route('/api/upload', methods=['POST'])
def upload_data():
    # Check API key authentication
    provided_key = request.headers.get('X-API-Key')
    if not provided_key or provided_key != API_KEY:
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    # Check if file was included in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Check if filename exists
    if not file.filename:
        return jsonify({"error": "Invalid filename"}), 400
        
    # Check file extension
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400
    
    try:
        # Read the uploaded CSV
        file_content = file.read()
        file_stream = io.BytesIO(file_content)
        
        # Validate the CSV format
        df = pd.read_csv(file_stream)
        
        # Check required columns
        required_columns = ['review_id', 'review_text', 'category', 'aspects']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({
                "error": f"Missing required columns: {', '.join(missing_columns)}"
            }), 400
        
        # Save file to uploads directory
        filename = f"api_upload_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Reset file stream position and save
        file_stream.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return jsonify({
            "success": True,
            "message": "File uploaded successfully",
            "filename": filename,
            "row_count": len(df)
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

# Helper function to verify API key
def verify_api_key():
    """Check if the provided API key is valid"""
    provided_key = request.headers.get('X-API-Key')
    if not provided_key or provided_key != API_KEY:
        return False
    return True
    
# Helper function to json serialize objects
def json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (pd.Timestamp, pd.Series)):
        return str(obj)
    return str(obj)

# Upload review categories via CSV
@app.route('/api/upload/review_categories/csv', methods=['POST'])
def upload_categories_csv():
    """Process uploaded category data from CSV and return analytics"""
    # Check authentication
    if not verify_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    # Check if file was included
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Check filename
    if not file.filename:
        return jsonify({"error": "Invalid filename"}), 400
    
    # Check file extension
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400
    
    try:
        # Read the uploaded CSV
        file_content = file.read()
        file_stream = io.BytesIO(file_content)
        
        # Parse the CSV
        df = pd.read_csv(file_stream)
        
        # Save file to example_data directory
        os.makedirs("example_data", exist_ok=True)
        filename = f"review_categories_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path = os.path.join("example_data", filename)
        
        # Reset file stream position and save
        file_stream.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
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
        
        # Run the analysis
        analysis = analyze_category_aspects(df)
        
        # Create the result
        result = {
            "success": True,
            "message": "Categories processed successfully",
            "filename": filename,
            "row_count": len(df),
            "categories_count": len(df),
            "categories_with_aspects": len(df[df['aspectsCount'] > 0]) if 'aspectsCount' in df.columns else "unknown",
            "categories_without_aspects": len(df[df['aspectsCount'] == 0]) if 'aspectsCount' in df.columns else "unknown",
            "analysis": {
                "aspect_freq": analysis["aspect_freq"].to_dict(orient='records') if analysis and "aspect_freq" in analysis else [],
                "categories_no_aspects": analysis["categories_no_aspects"].to_dict(orient='records') if analysis and "categories_no_aspects" in analysis else []
            }
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

# Upload review categories via JSON
@app.route('/api/upload/review_categories/json', methods=['POST'])
def upload_categories_json():
    """Process uploaded category data from JSON and return analytics"""
    # Check authentication
    if not verify_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    try:
        # Check if JSON data is provided
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        # Get the JSON data
        data = request.get_json()
        
        # Validate required fields
        if not isinstance(data, list):
            return jsonify({"error": "JSON data must be an array of category objects"}), 400
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Save to file
        os.makedirs("example_data", exist_ok=True)
        filename = f"review_categories_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join("example_data", filename)
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        # Process aspects if needed
        if 'aspects' in df.columns:
            df['aspects_parsed'] = df['aspects']
        
        # Run the analysis
        analysis = analyze_category_aspects(df)
        
        # Create the result
        result = {
            "success": True,
            "message": "Categories processed successfully",
            "filename": filename,
            "row_count": len(df),
            "categories_count": len(df),
            "categories_with_aspects": len(df[df['aspectsCount'] > 0]) if 'aspectsCount' in df.columns else "unknown",
            "categories_without_aspects": len(df[df['aspectsCount'] == 0]) if 'aspectsCount' in df.columns else "unknown",
            "analysis": {
                "aspect_freq": analysis["aspect_freq"].to_dict(orient='records') if analysis and "aspect_freq" in analysis else [],
                "categories_no_aspects": analysis["categories_no_aspects"].to_dict(orient='records') if analysis and "categories_no_aspects" in analysis else []
            }
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": f"Error processing JSON data: {str(e)}"}), 500

# Get category analytics
@app.route('/api/analytics/categories', methods=['GET'])
def get_category_analytics():
    """Return analytics for category data"""
    # Check authentication
    if not verify_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    try:
        # Load the category data
        df = load_category_data()
        
        if df is None or len(df) == 0:
            return jsonify({"error": "No category data available"}), 404
            
        # Run the analysis
        analysis = analyze_category_aspects(df)
        
        if analysis is None:
            return jsonify({"error": "Failed to analyze category data"}), 500
            
        # Get the matrix
        matrix = create_aspect_category_matrix(df)
        
        # Create the result
        result = {
            "success": True,
            "categories_count": len(df),
            "categories_with_aspects": len(df[df['aspectsCount'] > 0]),
            "categories_without_aspects": len(df[df['aspectsCount'] == 0]),
            "unique_aspects_count": len(analysis["all_aspects"]) if "all_aspects" in analysis else 0,
            "top_aspects": analysis["aspect_freq"].head(10).to_dict(orient='records') if "aspect_freq" in analysis else [],
            "categories_no_aspects": analysis["categories_no_aspects"].to_dict(orient='records') if "categories_no_aspects" in analysis else [],
            "aspect_matrix_sample": matrix.head(10).to_dict(orient='records') if matrix is not None else []
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": f"Error generating analytics: {str(e)}"}), 500

# Get reviews analytics
@app.route('/api/analytics/reviews', methods=['GET'])
def get_review_analytics():
    """Return analytics for review data"""
    # Check authentication
    if not verify_api_key():
        return jsonify({"error": "Invalid or missing API key"}), 403
    
    try:
        # Get list of uploaded files
        files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.csv')]
        
        if not files:
            return jsonify({"error": "No review data available"}), 404
            
        # Use the most recent file
        latest_file = sorted(files)[-1]
        file_path = os.path.join(UPLOAD_DIR, latest_file)
        
        # Load the data
        df = process_csv(file_path)
        
        if df is None or len(df) == 0:
            return jsonify({"error": "Failed to process review data"}), 500
            
        # Run the analysis
        analysis_df, counts_df = analyze_aspects(df)
        
        if analysis_df is None:
            return jsonify({"error": "Failed to analyze review data"}), 500
            
        # Get top aspects
        top_aspects = get_top_aspects(analysis_df)
        
        # Get low percentage aspects
        low_aspects = get_low_percentage_aspects(analysis_df)
        
        # Get aspect distribution
        distribution = get_aspect_distribution(analysis_df)
        
        # Create the result
        result = {
            "success": True,
            "file": latest_file,
            "reviews_count": len(df),
            "categories_count": len(df['category'].unique()),
            "top_aspects": top_aspects.to_dict(orient='records') if top_aspects is not None else [],
            "low_percentage_aspects": low_aspects.to_dict(orient='records') if low_aspects is not None else [],
            "aspect_distribution": distribution.to_dict(orient='records') if distribution is not None else []
        }
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": f"Error generating analytics: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('API_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)