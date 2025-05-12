import os
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InternalAPIClient:
    """Client for interacting with the internal Perigon API."""
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = "https://api.perigon.io/v1/internal"
        self.shared_secret = os.environ.get("SHARED_SECRET")
        
        if not self.shared_secret:
            logger.warning("SHARED_SECRET environment variable is not set.")
        
    def get_review_categories(self, page=0, size=10, sort_by="id", sort_order="asc"):
        """
        Fetch review categories from the internal API.
        
        Parameters:
        -----------
        page : int
            Page number for pagination (0-indexed)
        size : int
            Number of items per page
        sort_by : str
            Field to sort by
        sort_order : str
            Sort order ('asc' or 'desc')
            
        Returns:
        --------
        dict or None
            API response data or None if request failed
        """
        if not self.shared_secret:
            logger.error("Cannot make API request: SHARED_SECRET is not set")
            return {
                "error": "API authentication is not configured. Please set the SHARED_SECRET environment variable."
            }
        
        # Endpoint for review categories with sharedSecret as query parameter
        endpoint = f"{self.base_url}/ca/reviewCategory/"
        
        # Request headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Pagination parameters matching the PaginationSortParams structure
        params = {
            "sharedSecret": self.shared_secret,  # Using sharedSecret as query parameter
            "page": page,
            "size": size,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        try:
            # Make the API request
            response = requests.get(endpoint, headers=headers, params=params)
            
            # Check if request was successful
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"API request failed with status {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                "error": "Error connecting to the API",
                "details": str(e)
            }
        except json.JSONDecodeError:
            logger.error("Error decoding API response")
            return {
                "error": "Error decoding API response",
                "details": "The API response was not valid JSON"
            }
            
    def get_review_categories_paginated(self, max_pages=5, sort_by="id", sort_order="asc"):
        """
        Fetch all review categories with pagination.
        
        Parameters:
        -----------
        max_pages : int
            Maximum number of pages to fetch
        sort_by : str
            Field to sort by (default: "id")
        sort_order : str
            Sort order, "asc" or "desc" (default: "asc")
            
        Returns:
        --------
        list
            Combined results from all pages with expected fields:
            - id (int)
            - createdAt (datetime string)
            - updatedAt (datetime string)
            - name (string)
            - caCategoryId (string)
            - rulesPath (string, nullable)
            - aspects (list of CAReviewAspectDto)
        """
        all_results = []
        page = 0
        size = 20  # Reasonable page size
        
        while page < max_pages:
            response = self.get_review_categories(
                page=page, 
                size=size, 
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            if isinstance(response, dict) and "error" in response:
                return response
            
            # Check if we got valid content (API response structure)
            if not isinstance(response, dict) or "content" not in response:
                return {
                    "error": "Unexpected API response format",
                    "details": "The 'content' field is missing from the response"
                }
                
            # Add results to our collection
            content = response.get("content", [])
            if content:
                all_results.extend(content)
            
            # Check if this is the last page
            try:
                total_pages = int(response.get("totalPages", 0))
                if page >= total_pages - 1:
                    break
            except (ValueError, TypeError):
                # If totalPages is not convertible to int, just continue to next page
                pass
                
            page += 1
            
        # Process the results to ensure all expected fields are present
        processed_results = []
        for item in all_results:
            processed_item = {
                'id': item.get('id'),
                'name': item.get('name', ''),
                'createdAt': item.get('createdAt', ''),
                'updatedAt': item.get('updatedAt', ''),
                'caCategoryId': item.get('caCategoryId', ''),
                'rulesPath': item.get('rulesPath', ''),
                'aspectsCount': len(item.get('aspects', []))
            }
            
            # Optionally include aspects if present
            if 'aspects' in item and item['aspects']:
                processed_item['aspects'] = [aspect.get('name', '') for aspect in item['aspects']]
                
            processed_results.append(processed_item)
            
        return processed_results