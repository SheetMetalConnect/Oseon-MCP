#!/usr/bin/env python3
"""
Simple test script to verify TRUMPF Oseon API connection
"""

import os
import base64
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_connection():
    """Test the TRUMPF Oseon API connection"""
    
    # Get configuration from environment
    base_url = os.getenv('OSEON_BASE_URL')
    username = os.getenv('OSEON_USERNAME')
    password = os.getenv('OSEON_PASSWORD')
    api_version = os.getenv('OSEON_API_VERSION', '2.0')
    
    print(f"Testing connection to: {base_url}")
    print(f"Username: {username}")
    print(f"API Version: {api_version}")
    
    # Create Basic Auth header
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    auth_header = f"Basic {encoded_credentials}"
    
    # Set up headers
    headers = {
        "accept": "application/json",
        "api-version": api_version,
        "authorization": auth_header
    }
    
    # Test endpoint
    test_url = f"{base_url}/api/v2/sales/customerOrders?size=5"
    
    try:
        print(f"\nMaking request to: {test_url}")
        with httpx.Client(timeout=10.0) as client:
            response = client.get(test_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API connection successful!")
                print(f"Response status: {response.status_code}")
                print(f"Records returned: {data.get('records', 'N/A')}")
                print(f"Total pages: {data.get('pages', 'N/A')}")
                print(f"Orders in response: {len(data.get('collection', []))}")
                return True
            else:
                print(f"❌ API request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Testing TRUMPF Oseon API Connection")
    print("=" * 50)
    
    success = test_api_connection()
    
    if success:
        print("\n✅ API connection test passed!")
        print("The MCP server should work correctly with these credentials.")
    else:
        print("\n❌ API connection test failed!")
        print("Please check your network connection and credentials.") 