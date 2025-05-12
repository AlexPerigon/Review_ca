#!/usr/bin/env python3
import os
import subprocess
import threading
import time
import signal
import sys

def run_streamlit():
    """Run the Streamlit app"""
    print("Starting Streamlit server...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", "app.py", "--server.port", "5000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Print output from Streamlit if stdout is available
    if streamlit_process.stdout:
        while True:
            line = streamlit_process.stdout.readline()
            if not line:
                break
            print(f"[Streamlit] {line.strip()}")
    
    streamlit_process.wait()

def run_api():
    """Run the Flask API server"""
    print("Starting API server...")
    api_process = subprocess.Popen(
        ["python", "api.py"],
        env={**os.environ, "API_PORT": "5001"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Print output from API server if stdout is available
    if api_process.stdout:
        while True:
            line = api_process.stdout.readline()
            if not line:
                break
            print(f"[API] {line.strip()}")
    
    api_process.wait()

def signal_handler(sig, frame):
    """Handle termination signals"""
    print("Shutting down servers...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Set API key from environment or use default
    if "API_KEY" not in os.environ:
        print("WARNING: API_KEY environment variable not set. Using default development key.")
        print("Set API_KEY environment variable for production use.")
        os.environ["API_KEY"] = "default_dev_key"
    
    # Create uploads directory if it doesn't exist
    os.makedirs("uploads", exist_ok=True)
    
    # Start servers in separate threads
    streamlit_thread = threading.Thread(target=run_streamlit)
    api_thread = threading.Thread(target=run_api)
    
    streamlit_thread.daemon = True
    api_thread.daemon = True
    
    streamlit_thread.start()
    api_thread.start()
    
    # Print usage information
    time.sleep(2)  # Wait for servers to start
    print("\n" + "=" * 50)
    print("Review Aspect Analyzer is running!")
    print("=" * 50)
    print(f"Streamlit UI: http://localhost:5000")
    print(f"API Endpoint: http://localhost:5001/api/upload")
    print("API Usage Example:")
    print(f"curl -X POST -H \"X-API-Key: {os.environ['API_KEY']}\" -F \"file=@your_file.csv\" http://localhost:5001/api/upload")
    print("=" * 50 + "\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")