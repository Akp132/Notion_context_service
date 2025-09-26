"""Notion content searcher for finding relevant pages."""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from .client import NotionClient
from .parser import NotionParser
from ..models.schema import NotionPage, SearchQuery, SearchResponse

logger = logging.getLogger(__name__)

class NotionSearcher:
    """Searcher for finding relevant Notion pages."""
    
    def __init__(self, notion_client: NotionClient):
        """Initialize the searcher.
        
        Args:
            notion_client: Initialized Notion client
        """
        self.client = notion_client
        self.parser = NotionParser()
    
    def search_pages(self, search_query: SearchQuery) -> SearchResponse:
        """Search for pages matching the query.
        
        Args:
            search_query: Search query parameters
            
        Returns:
            SearchResponse with matching pages
            
        Raises:
            Exception: If search fails
        """
        try:
            # Perform the search
            search_results = self.client.search_pages(
                query=search_query.query,
                filter_properties=search_query.filter_properties
            )
            
            # Process results
            pages = []
            results = search_results.get("results", [])
            
            for result in results[:search_query.max_results]:
                try:
                    page = self._process_search_result(result)
                    if page:
                        pages.append(page)
                except Exception as e:
                    logger.warning(f"Failed to process search result: {e}")
                    continue
            
            return SearchResponse(
                results=pages,
                total_count=len(pages),
                query=search_query.query
            )
            
        except Exception as e:
            logger.error(f"Search failed for query '{search_query.query}': {e}")
            raise Exception(f"Search failed: {e}")
    
    def search_by_database(self, database_id: str, search_query: SearchQuery) -> SearchResponse:
        """Search for pages within a specific database.
        
        Args:
            database_id: ID of the database to search
            search_query: Search query parameters
            
        Returns:
            SearchResponse with matching pages from the database
            
        Raises:
            Exception: If search fails
        """
        try:
            # Add database filter to search
            if search_query.filter_properties is None:
                search_query.filter_properties = {}
            
            search_query.filter_properties["database_id"] = database_id
            
            return self.search_pages(search_query)
            
        except Exception as e:
            logger.error(f"Database search failed for database {database_id}: {e}")
            raise Exception(f"Database search failed: {e}")
    
    def _process_search_result(self, result: Dict[str, Any]) -> Optional[NotionPage]:
        """Process a single search result into a NotionPage.
        
        Args:
            result: Single search result from Notion API
            
        Returns:
            NotionPage object or None if processing fails
        """
        try:
            page_id = result.get("id")
            if not page_id:
                return None
            
            # Extract basic information
            title = self._extract_title_from_result(result)
            url = result.get("url", "")
            created_time = self._parse_datetime(result.get("created_time"))
            last_edited_time = self._parse_datetime(result.get("last_edited_time"))
            
            # Parse properties
            properties = self.parser.parse_page_properties(result)
            
            # For search results, we don't fetch full content by default
            # This can be done separately if needed
            content = ""
            
            return NotionPage(
                id=page_id,
                title=title,
                content=content,
                url=url,
                created_time=created_time,
                last_edited_time=last_edited_time,
                properties=properties
            )
            
        except Exception as e:
            logger.warning(f"Failed to process search result: {e}")
            return None
    
    def _extract_title_from_result(self, result: Dict[str, Any]) -> str:
        """Extract title from search result.
        
        Args:
            result: Search result data
            
        Returns:
            Page title or fallback
        """
        properties = result.get("properties", {})
        
        # Look for title property
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_rich_text = prop_data.get("title", [])
                title = self.parser._extract_rich_text(title_rich_text)
                if title:
                    return title
        
        # Fallback to page ID if no title found
        return f"Untitled Page ({result.get('id', 'unknown')})"
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> 'datetime':
        """Parse datetime string from Notion API.
        
        Args:
            datetime_str: ISO datetime string from Notion
            
        Returns:
            Parsed datetime object or current time as fallback
        """
        from datetime import datetime
        
        if not datetime_str:
            return datetime.now()
        
        try:
            # Notion uses ISO format with timezone info
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse datetime: {datetime_str}")
            return datetime.now()
    
    def get_recent_pages(self, max_results: int = 10) -> SearchResponse:
        """Get recently edited pages.
        
        Args:
            max_results: Maximum number of pages to return
            
        Returns:
            SearchResponse with recent pages
        """
        try:
            # Search with empty query to get recent pages
            search_results = self.client.search_pages(query="")
            
            # Sort by last edited time (most recent first)
            results = search_results.get("results", [])
            results.sort(
                key=lambda x: x.get("last_edited_time", ""),
                reverse=True
            )
            
            # Process results
            pages = []
            for result in results[:max_results]:
                page = self._process_search_result(result)
                if page:
                    pages.append(page)
            
            return SearchResponse(
                results=pages,
                total_count=len(pages),
                query="recent pages"
            )
            
        except Exception as e:
            logger.error(f"Failed to get recent pages: {e}")
            raise Exception(f"Could not get recent pages: {e}")
    
    def search_pages_and_databases(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search for both pages and databases matching the query.
        
        This function performs a comprehensive search across both pages and databases
        in the Notion workspace, filtering by object type and matching against titles.
        Results are sorted by last_edited_time (most recent first).
        
        Args:
            query: Search query string (e.g., 'Company A financial logs September')
            max_results: Maximum number of results to return (default: 20)
            
        Returns:
            List of metadata dictionaries containing:
            - id: Notion object ID
            - title: Object title
            - object_type: 'page' or 'database'
            - last_edited: Last edited timestamp
            - url: Notion URL
            - created_time: Creation timestamp
            
        Raises:
            ValueError: If query is empty or invalid
            ConnectionError: If Notion API connection fails
            Exception: If search operation fails
            
        Example:
            >>> searcher = NotionSearcher(notion_client)
            >>> results = searcher.search_pages_and_databases("Company A financial logs September")
            >>> for result in results:
            ...     print(f"{result['object_type']}: {result['title']} (edited: {result['last_edited']})")
        """
        if not query or not query.strip():
            raise ValueError("Query string cannot be empty")
        
        query = query.strip()
        logger.info(f"Searching for pages and databases with query: '{query}'")
        
        try:
            # Perform search with filter for both pages and databases
            search_results = self.client.client.search(
                query=query,
                filter={
                    "property": "object",
                    "value": "page"
                },
                page_size=100  # Get more results to filter and sort
            )
            
            # Also search for databases
            database_results = self.client.client.search(
                query=query,
                filter={
                    "property": "object", 
                    "value": "database"
                },
                page_size=100
            )
            
            # Combine and process results
            all_results = []
            
            # Process page results
            page_results = search_results.get("results", [])
            for result in page_results:
                metadata = self._extract_metadata(result, "page")
                if metadata:
                    all_results.append(metadata)
            
            # Process database results
            db_results = database_results.get("results", [])
            for result in db_results:
                metadata = self._extract_metadata(result, "database")
                if metadata:
                    all_results.append(metadata)
            
            # Sort by last_edited_time (most recent first)
            all_results.sort(
                key=lambda x: x.get("last_edited", datetime.min),
                reverse=True
            )
            
            # Limit results
            limited_results = all_results[:max_results]
            
            logger.info(f"Found {len(limited_results)} matching objects (pages and databases)")
            return limited_results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise ConnectionError(f"Notion API authentication failed: {e}")
            elif "403" in str(e) or "forbidden" in str(e).lower():
                raise ConnectionError(f"Notion API access forbidden: {e}")
            else:
                raise Exception(f"Search operation failed: {e}")
    
    def _extract_metadata(self, result: Dict[str, Any], object_type: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from a Notion search result.
        
        Args:
            result: Search result from Notion API
            object_type: Type of object ('page' or 'database')
            
        Returns:
            Metadata dictionary or None if extraction fails
        """
        try:
            object_id = result.get("id")
            if not object_id:
                logger.warning("Search result missing ID, skipping")
                return None
            
            # Extract title based on object type
            title = self._extract_title_for_search(result, object_type)
            
            # Extract timestamps
            created_time = self._parse_datetime(result.get("created_time"))
            last_edited_time = self._parse_datetime(result.get("last_edited_time"))
            
            # Extract URL
            url = result.get("url", "")
            
            metadata = {
                "id": object_id,
                "title": title,
                "object_type": object_type,
                "last_edited": last_edited_time,
                "url": url,
                "created_time": created_time
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {object_type} result: {e}")
            return None
    
    def _extract_title_for_search(self, result: Dict[str, Any], object_type: str) -> str:
        """Extract title from search result based on object type.
        
        Args:
            result: Search result from Notion API
            object_type: Type of object ('page' or 'database')
            
        Returns:
            Extracted title or fallback
        """
        try:
            if object_type == "page":
                # For pages, look in properties for title
                properties = result.get("properties", {})
                for prop_name, prop_data in properties.items():
                    if prop_data.get("type") == "title":
                        title_rich_text = prop_data.get("title", [])
                        title = self.parser._extract_rich_text(title_rich_text)
                        if title:
                            return title
                            
            elif object_type == "database":
                # For databases, title is in the title array
                title_array = result.get("title", [])
                if title_array:
                    title = self.parser._extract_rich_text(title_array)
                    if title:
                        return title
            
            # Fallback to object ID if no title found
            object_id = result.get("id", "unknown")
            return f"Untitled {object_type.title()} ({object_id})"
            
        except Exception as e:
            logger.warning(f"Failed to extract title for {object_type}: {e}")
            object_id = result.get("id", "unknown")
            return f"Untitled {object_type.title()} ({object_id})"
