import os
import json
import pandas as pd
from flask import Flask, request, jsonify
import io

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

if __name__ == '__main__':
    port = int(os.environ.get('API_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)