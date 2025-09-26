#!/usr/bin/env python3
"""Example usage of the Notion Context Service client helper."""

import sys
import os
import logging

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Import with absolute paths
from app.notion.client import create_notion_client, get_notion_client
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demonstrate how to use the Notion client helper functions."""
    
    print("=== Notion Context Service - Client Helper Example ===\n")
    
    # Check if Notion is configured
    if not settings.is_notion_configured:
        print("❌ Notion API key not configured!")
        print("Please set NOTION_API_KEY in your .env file")
        print("Get your integration token from: https://www.notion.so/my-integrations")
        return
    
    print("✅ Notion API key is configured")
    print(f"Database ID: {'✅ Configured' if settings.notion_database_id else '❌ Not configured'}")
    print()
    
    try:
        # Method 1: Using create_notion_client()
        print("Creating Notion client using create_notion_client()...")
        client1 = create_notion_client()
        print("✅ Client created successfully")
        
        # Method 2: Using get_notion_client() (alias)
        print("\nCreating Notion client using get_notion_client()...")
        client2 = get_notion_client()
        print("✅ Client created successfully")
        
        # Test the connection
        print("\nTesting connection to Notion API...")
        user_info = client1.client.users.me()
        print(f"✅ Connected successfully! User: {user_info.get('name', 'Unknown')}")
        
        # Example: Search for pages
        print("\nSearching for pages...")
        search_results = client1.search_pages("test")
        print(f"✅ Found {len(search_results.get('results', []))} pages")
        
        print("\n🎉 All tests passed! Your Notion integration is working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your NOTION_API_KEY is correct")
        print("2. Ensure your integration has access to the pages you're trying to access")
        print("3. Check that your integration token starts with 'secret_'")

if __name__ == "__main__":
    main()
