"""Notion content fetcher for retrieving pages and content."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .client import NotionClient
from .parser import NotionParser
from ..models.schema import NotionPage

logger = logging.getLogger(__name__)

class NotionFetcher:
    """Fetcher for retrieving and processing Notion content."""
    
    def __init__(self, notion_client: NotionClient):
        """Initialize the fetcher.
        
        Args:
            notion_client: Initialized Notion client
        """
        self.client = notion_client
        self.parser = NotionParser()
    
    def fetch_page(self, page_id: str, include_properties: bool = True) -> NotionPage:
        """Fetch a single page by ID.
        
        Args:
            page_id: The ID of the page to fetch
            include_properties: Whether to include page properties
            
        Returns:
            NotionPage object with page data
            
        Raises:
            Exception: If page fetch fails
        """
        try:
            # Fetch page data
            page_data = self.client.get_page(page_id)
            
            # Fetch page content
            content_data = self.client.get_page_content(page_id)
            content_blocks = content_data.get("results", [])
            
            # Extract text content
            content_text = self.parser.extract_text_from_blocks(content_blocks)
            
            # Parse properties if requested
            properties = {}
            if include_properties:
                properties = self.parser.parse_page_properties(page_data)
            
            # Extract basic page info
            title = self._extract_title(page_data)
            url = page_data.get("url", "")
            created_time = self._parse_datetime(page_data.get("created_time"))
            last_edited_time = self._parse_datetime(page_data.get("last_edited_time"))
            
            return NotionPage(
                id=page_id,
                title=title,
                content=content_text,
                url=url,
                created_time=created_time,
                last_edited_time=last_edited_time,
                properties=properties
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch page {page_id}: {e}")
            raise Exception(f"Could not fetch page {page_id}: {e}")
    
    def fetch_pages(self, page_ids: List[str], include_properties: bool = True) -> List[NotionPage]:
        """Fetch multiple pages by IDs.
        
        Args:
            page_ids: List of page IDs to fetch
            include_properties: Whether to include page properties
            
        Returns:
            List of NotionPage objects
            
        Raises:
            Exception: If any page fetch fails
        """
        pages = []
        errors = []
        
        for page_id in page_ids:
            try:
                page = self.fetch_page(page_id, include_properties)
                pages.append(page)
            except Exception as e:
                logger.error(f"Failed to fetch page {page_id}: {e}")
                errors.append(f"Page {page_id}: {str(e)}")
        
        if errors and not pages:
            # If all pages failed, raise an exception
            raise Exception(f"Failed to fetch all pages: {'; '.join(errors)}")
        elif errors:
            # If some pages failed, log warnings but return successful pages
            logger.warning(f"Some pages failed to fetch: {'; '.join(errors)}")
        
        return pages
    
    def _extract_title(self, page_data: Dict[str, Any]) -> str:
        """Extract title from page data.
        
        Args:
            page_data: Raw page data from Notion API
            
        Returns:
            Page title or fallback
        """
        properties = page_data.get("properties", {})
        
        # Look for title property
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_rich_text = prop_data.get("title", [])
                title = self.parser._extract_rich_text(title_rich_text)
                if title:
                    return title
        
        # Fallback to page ID if no title found
        return f"Untitled Page ({page_data.get('id', 'unknown')})"
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> datetime:
        """Parse datetime string from Notion API.
        
        Args:
            datetime_str: ISO datetime string from Notion
            
        Returns:
            Parsed datetime object or current time as fallback
        """
        if not datetime_str:
            return datetime.now()
        
        try:
            # Notion uses ISO format with timezone info
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse datetime: {datetime_str}")
            return datetime.now()
    
    def get_page_summary(self, page_id: str) -> Dict[str, Any]:
        """Get a summary of a page without full content.
        
        Args:
            page_id: The ID of the page to summarize
            
        Returns:
            Dictionary with page summary information
        """
        try:
            page_data = self.client.get_page(page_id)
            
            return {
                "id": page_id,
                "title": self._extract_title(page_data),
                "url": page_data.get("url", ""),
                "created_time": self._parse_datetime(page_data.get("created_time")),
                "last_edited_time": self._parse_datetime(page_data.get("last_edited_time")),
                "properties": self.parser.parse_page_properties(page_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to get page summary for {page_id}: {e}")
            raise Exception(f"Could not get page summary for {page_id}: {e}")
    
    def query_database(self, database_id: str, query_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query a database to get all page records.
        
        Uses the Notion API /databases/{database_id}/query endpoint to retrieve
        all pages in the specified database with optional filtering and sorting.
        
        Args:
            database_id: The ID of the database to query
            query_params: Optional query parameters for filtering/sorting
                         - filter: Filter criteria for pages
                         - sorts: Sort criteria for results
                         - page_size: Number of results per page (max 100)
                         - start_cursor: Pagination cursor
            
        Returns:
            List of page records from the database with metadata
            
        Raises:
            ValueError: If database_id is empty or invalid
            ConnectionError: If Notion API connection fails
            Exception: If database query fails
            
        Example:
            >>> fetcher = NotionFetcher(notion_client)
            >>> pages = fetcher.query_database("db_123", {"page_size": 50})
            >>> for page in pages:
            ...     print(f"Page: {page['title']} (ID: {page['id']})")
        """
        if not database_id or not database_id.strip():
            raise ValueError("Database ID cannot be empty")
        
        database_id = database_id.strip()
        logger.info(f"Querying database {database_id}")
        
        try:
            # Prepare query parameters with defaults
            query_data = query_params or {}
            if "page_size" not in query_data:
                query_data["page_size"] = 100  # Maximum page size
            
            # Query the database (handle pagination)
            pages: List[Dict[str, Any]] = []
            start_cursor: Optional[str] = query_data.pop("start_cursor", None)

            while True:
                resp = self.client.client.databases.query(
                    database_id=database_id,
                    start_cursor=start_cursor,
                    **query_data
                )
                pages.extend(resp.get("results", []))
                if resp.get("has_more") and resp.get("next_cursor"):
                    start_cursor = resp.get("next_cursor")
                else:
                    break
            
            # Process each page record
            processed_pages = []
            for page in pages:
                try:
                    processed_page = self._process_database_page(page)
                    if processed_page:
                        processed_pages.append(processed_page)
                except Exception as e:
                    logger.warning(f"Failed to process database page {page.get('id', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully queried database {database_id}, found {len(processed_pages)} pages")
            return processed_pages
            
        except Exception as e:
            logger.error(f"Database query failed for {database_id}: {e}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise ConnectionError(f"Notion API authentication failed: {e}")
            elif "403" in str(e) or "forbidden" in str(e).lower():
                raise ConnectionError(f"Access forbidden to database {database_id}: {e}")
            elif "404" in str(e) or "not found" in str(e).lower():
                raise ValueError(f"Database {database_id} not found: {e}")
            else:
                raise Exception(f"Database query failed: {e}")
    
    def fetch_page_with_blocks(self, page_id: str, include_properties: bool = True) -> Dict[str, Any]:
        """Fetch a page with all its blocks recursively.
        
        Retrieves a page and recursively fetches all its blocks, including
        child blocks, to provide complete content structure.
        
        Args:
            page_id: The ID of the page to fetch
            include_properties: Whether to include page properties
            
        Returns:
            Dictionary containing page data and all blocks in a structured format:
            - page: Basic page information (id, title, url, timestamps)
            - blocks: List of all blocks with recursive children
            - content_text: Flattened text content from all blocks
            - properties: Page properties (if include_properties=True)
            
        Raises:
            ValueError: If page_id is empty or invalid
            ConnectionError: If Notion API connection fails
            Exception: If page or block fetching fails
            
        Example:
            >>> fetcher = NotionFetcher(notion_client)
            >>> page_data = fetcher.fetch_page_with_blocks("page_123")
            >>> print(f"Page: {page_data['page']['title']}")
            >>> print(f"Total blocks: {len(page_data['blocks'])}")
        """
        if not page_id or not page_id.strip():
            raise ValueError("Page ID cannot be empty")
        
        page_id = page_id.strip()
        logger.info(f"Fetching page {page_id} with all blocks")
        
        try:
            # Fetch basic page information
            page_data = self.client.get_page(page_id)
            
            # Extract page metadata
            page_info = {
                "id": page_id,
                "title": self._extract_title(page_data),
                "url": page_data.get("url", ""),
                "created_time": self._parse_datetime(page_data.get("created_time")),
                "last_edited_time": self._parse_datetime(page_data.get("last_edited_time"))
            }
            
            # Add properties if requested
            properties = {}
            if include_properties:
                properties = self.parser.parse_page_properties(page_data)
            
            # Fetch all blocks recursively
            all_blocks = self._fetch_blocks_recursively(page_id)
            
            # Extract text content from all blocks
            content_text = self.parser.extract_text_from_blocks(all_blocks)
            
            result = {
                "page": page_info,
                "blocks": all_blocks,
                "content_text": content_text,
                "properties": properties,
                "total_blocks": len(all_blocks)
            }
            
            logger.info(f"Successfully fetched page {page_id} with {len(all_blocks)} blocks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch page {page_id} with blocks: {e}")
            if "401" in str(e) or "unauthorized" in str(e).lower():
                raise ConnectionError(f"Notion API authentication failed: {e}")
            elif "403" in str(e) or "forbidden" in str(e).lower():
                raise ConnectionError(f"Access forbidden to page {page_id}: {e}")
            elif "404" in str(e) or "not found" in str(e).lower():
                raise ValueError(f"Page {page_id} not found: {e}")
            else:
                raise Exception(f"Failed to fetch page with blocks: {e}")
    
    def _fetch_blocks_recursively(self, block_id: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """Recursively fetch all blocks for a given block ID.
        
        This method handles the recursive nature of Notion blocks, where blocks
        can have children that also need to be fetched. It implements several
        safety measures to prevent infinite recursion and handle edge cases.
        
        Args:
            block_id: The ID of the block to fetch children for
            max_depth: Maximum recursion depth to prevent infinite loops (default: 10)
            
        Returns:
            List of all blocks with their children flattened into a single list
            
        Edge Cases Handled:
            - Blocks without children (has_children = false)
            - Circular references (prevented by max_depth)
            - API rate limiting (handled by error catching)
            - Malformed block data (handled by try/catch)
            - Empty or missing block responses
        """
        all_blocks = []
        processed_blocks = set()  # Track processed blocks to prevent circular references
        
        def _fetch_blocks_recursive(current_block_id: str, current_depth: int = 0):
            """Internal recursive function for fetching blocks.
            
            This nested function handles the actual recursion logic while
            maintaining access to the outer scope variables.
            """
            # Safety check: prevent infinite recursion
            if current_depth >= max_depth:
                logger.warning(f"Maximum recursion depth {max_depth} reached for block {current_block_id}")
                return
            
            # Safety check: prevent circular references
            if current_block_id in processed_blocks:
                logger.warning(f"Circular reference detected for block {current_block_id}")
                return
            
            processed_blocks.add(current_block_id)
            
            try:
                # Fetch children blocks for the current block with pagination
                next_cursor: Optional[str] = None
                while True:
                    response = self.client.client.blocks.children.list(
                        block_id=current_block_id,
                        start_cursor=next_cursor
                    )
                    blocks = response.get("results", [])

                    for block in blocks:
                        try:
                            # Add the current block to our results
                            all_blocks.append(block)
                            
                            # Check if this block has children and recursively fetch them
                            if block.get("has_children", False):
                                child_id = block.get("id")
                                if child_id:
                                    # Recursive call with increased depth
                                    _fetch_blocks_recursive(child_id, current_depth + 1)
                                else:
                                    logger.warning("Block has children but missing ID, skipping")
                        except Exception as e:
                            logger.warning(f"Failed to process block {block.get('id', 'unknown')}: {e}")
                            continue
                    # Handle pagination
                    if response.get("has_more") and response.get("next_cursor"):
                        next_cursor = response.get("next_cursor")
                        continue
                    break
            except Exception as e:
                logger.warning(f"Failed to fetch children for block {current_block_id}: {e}")
                # Don't re-raise here to allow processing of other blocks
                return
        
        # Start the recursive process
        _fetch_blocks_recursive(block_id)
        
        logger.info(f"Recursively fetched {len(all_blocks)} blocks for block {block_id}")
        return all_blocks
    
    def _process_database_page(self, page_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a page record from a database query.
        
        Args:
            page_data: Raw page data from database query
            
        Returns:
            Processed page data or None if processing fails
        """
        try:
            page_id = page_data.get("id")
            if not page_id:
                logger.warning("Database page missing ID, skipping")
                return None
            
            # Extract basic information
            title = self._extract_title(page_data)
            url = page_data.get("url", "")
            created_time = self._parse_datetime(page_data.get("created_time"))
            last_edited_time = self._parse_datetime(page_data.get("last_edited_time"))
            
            # Parse properties
            properties = self.parser.parse_page_properties(page_data)
            
            return {
                "id": page_id,
                "title": title,
                "url": url,
                "created_time": created_time,
                "last_edited_time": last_edited_time,
                "properties": properties
            }
            
        except Exception as e:
            logger.warning(f"Failed to process database page: {e}")
            return None
