import os
import streamlit as st
import hashlib
import hmac
import time
from datetime import datetime, timedelta

def verify_api_key(api_key):
    """
    Verify that the provided API key matches the expected value.
    
    Parameters:
    -----------
    api_key : str
        The API key provided by the user
        
    Returns:
    --------
    bool
        True if the key is valid, False otherwise
    """
    # Get the expected API key from environment
    expected_key = os.environ.get("API_KEY", "default_dev_key")
    
    # Compare using constant-time comparison to prevent timing attacks
    return hmac.compare_digest(api_key, expected_key)

def check_authentication():
    """
    Check if the user is authenticated.
    
    Returns:
    --------
    bool
        True if authenticated, False otherwise
    """
    # Check if auth status is in session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.auth_time = None
    
    # Check if authentication has expired (24 hours)
    if st.session_state.auth_time:
        expiry_time = st.session_state.auth_time + timedelta(hours=24)
        if datetime.now() > expiry_time:
            st.session_state.authenticated = False
            st.session_state.auth_time = None
    
    return st.session_state.authenticated

def authenticate(api_key):
    """
    Authenticate a user using an API key.
    
    Parameters:
    -----------
    api_key : str
        The API key to verify
        
    Returns:
    --------
    bool
        True if authentication was successful, False otherwise
    """
    if verify_api_key(api_key):
        st.session_state.authenticated = True
        st.session_state.auth_time = datetime.now()
        return True
    else:
        st.session_state.authenticated = False
        st.session_state.auth_time = None
        return False

def logout():
    """Log the user out by clearing authentication status"""
    st.session_state.authenticated = False
    st.session_state.auth_time = None

def display_login_page():
    """Display the login page and handle authentication"""
    st.title("Login Required")
    st.markdown("""
    ### Authentication Required
    
    This application requires authentication to access. 
    Please enter your API key to continue.
    """)
    
    # API key input
    api_key = st.text_input("API Key", type="password")
    
    # Login button
    if st.button("Login"):
        if authenticate(api_key):
            st.success("✅ Authentication successful!")
            st.rerun()  # Rerun the app to show content
        else:
            st.error("❌ Invalid API key. Please try again.")

def auth_required(func):
    """
    Decorator to require authentication for a function.
    
    Parameters:
    -----------
    func : callable
        The function to protect with authentication
        
    Returns:
    --------
    callable
        A wrapped function that checks authentication before execution
    """
    def wrapper(*args, **kwargs):
        if check_authentication():
            return func(*args, **kwargs)
        else:
            display_login_page()
    
    return wrapper