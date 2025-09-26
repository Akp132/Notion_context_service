"""Notion API client wrapper."""

from notion_client import Client
from typing import Optional, Dict, Any
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class NotionClient:
    """Wrapper for Notion API client with error handling."""
    
    def __init__(self, api_key: str):
        """Initialize the Notion client.
        
        Args:
            api_key: Notion integration API key
        """
        if not api_key:
            raise ValueError("Notion API key is required")
        
        self.client = Client(auth=api_key)
        self._test_connection()
    
    def _test_connection(self) -> None:
        """Test the connection to Notion API."""
        try:
            # Test connection by getting user info
            self.client.users.me()
            logger.info("Successfully connected to Notion API")
        except Exception as e:
            logger.error(f"Failed to connect to Notion API: {e}")
            raise ConnectionError(f"Could not connect to Notion API: {e}")
    
    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a specific page by ID.
        
        Args:
            page_id: The ID of the page to retrieve
            
        Returns:
            Dictionary containing page data
            
        Raises:
            Exception: If page retrieval fails
        """
        try:
            return self.client.pages.retrieve(page_id=page_id)
        except Exception as e:
            logger.error(f"Failed to retrieve page {page_id}: {e}")
            raise Exception(f"Could not retrieve page {page_id}: {e}")
    
    def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """Retrieve the content blocks of a page.
        
        Args:
            page_id: The ID of the page to retrieve content for
            
        Returns:
            Dictionary containing page content blocks
            
        Raises:
            Exception: If content retrieval fails
        """
        try:
            return self.client.blocks.children.list(block_id=page_id)
        except Exception as e:
            logger.error(f"Failed to retrieve content for page {page_id}: {e}")
            raise Exception(f"Could not retrieve content for page {page_id}: {e}")
    
    def search_pages(self, query: str, database_id: Optional[str] = None, 
                    filter_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search for pages in Notion.
        
        Args:
            query: Search query string
            database_id: Optional database ID to limit search
            filter_properties: Optional properties to filter by
            
        Returns:
            Dictionary containing search results
            
        Raises:
            Exception: If search fails
        """
        try:
            search_params = {
                "query": query,
                "page_size": 100  # Maximum page size
            }
            
            if database_id:
                search_params["filter"] = {
                    "property": "object",
                    "value": "page"
                }
            
            if filter_properties:
                if "filter" not in search_params:
                    search_params["filter"] = {}
                search_params["filter"].update(filter_properties)
            
            return self.client.search(**search_params)
        except Exception as e:
            logger.error(f"Failed to search pages with query '{query}': {e}")
            raise Exception(f"Search failed: {e}")
    
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Retrieve database information.
        
        Args:
            database_id: The ID of the database to retrieve
            
        Returns:
            Dictionary containing database data
            
        Raises:
            Exception: If database retrieval fails
        """
        try:
            return self.client.databases.retrieve(database_id=database_id)
        except Exception as e:
            logger.error(f"Failed to retrieve database {database_id}: {e}")
            raise Exception(f"Could not retrieve database {database_id}: {e}")


def create_notion_client() -> NotionClient:
    """Create and return a Notion client instance using the configured API key.
    
    This helper function creates a NotionClient instance using the API key
    loaded from the configuration settings.
    
    Returns:
        NotionClient: Configured Notion client instance
        
    Raises:
        ValueError: If the Notion API key is not configured
        ConnectionError: If the connection to Notion API fails
    """
    if not settings.is_notion_configured:
        raise ValueError(
            "Notion API key not configured. Please set NOTION_API_KEY in your .env file. "
            "Get your integration token from: https://www.notion.so/my-integrations"
        )
    
    logger.info("Creating Notion client with configured API key")
    return NotionClient(api_key=settings.notion_api_key)


def get_notion_client() -> NotionClient:
    """Get a Notion client instance (alias for create_notion_client for consistency).
    
    Returns:
        NotionClient: Configured Notion client instance
    """
    return create_notion_client()
