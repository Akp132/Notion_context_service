"""FastAPI endpoints for the Notion Context Service."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from ..models.schema import (
    SearchQuery, SearchResponse, ContextRequest, ContextResponse, 
    HealthResponse, NotionPage, QueryResponse
)
from ..notion.client import NotionClient, create_notion_client
from ..notion.searcher import NotionSearcher
from ..notion.fetcher import NotionFetcher
from ..notion.parser import NotionParser
from ..config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Global instances (in production, use dependency injection)
_notion_client = None
_searcher = None
_fetcher = None

def get_notion_client() -> NotionClient:
    """Get or create Notion client instance using the helper function."""
    global _notion_client
    if _notion_client is None:
        try:
            _notion_client = create_notion_client()
        except ValueError as e:
            raise HTTPException(
                status_code=500, 
                detail=str(e)
            )
    return _notion_client

def get_searcher() -> NotionSearcher:
    """Get or create searcher instance."""
    global _searcher
    if _searcher is None:
        client = get_notion_client()
        _searcher = NotionSearcher(client)
    return _searcher

def get_fetcher() -> NotionFetcher:
    """Get or create fetcher instance."""
    global _fetcher
    if _fetcher is None:
        client = get_notion_client()
        _fetcher = NotionFetcher(client)
    return _fetcher

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version=settings.version
    )

@router.post("/search", response_model=SearchResponse)
async def search_pages(
    search_query: SearchQuery,
    searcher: NotionSearcher = Depends(get_searcher)
):
    """Search for Notion pages.
    
    Args:
        search_query: Search parameters
        searcher: Notion searcher instance
        
    Returns:
        Search results with matching pages
    """
    try:
        return await searcher.search_pages(search_query)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/database/{database_id}", response_model=SearchResponse)
async def search_database_pages(
    database_id: str,
    search_query: SearchQuery,
    searcher: NotionSearcher = Depends(get_searcher)
):
    """Search for pages within a specific database.
    
    Args:
        database_id: ID of the database to search
        search_query: Search parameters
        searcher: Notion searcher instance
        
    Returns:
        Search results with matching pages from the database
    """
    try:
        return await searcher.search_by_database(database_id, search_query)
    except Exception as e:
        logger.error(f"Database search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/recent", response_model=SearchResponse)
async def get_recent_pages(
    max_results: int = 10,
    searcher: NotionSearcher = Depends(get_searcher)
):
    """Get recently edited pages.
    
    Args:
        max_results: Maximum number of pages to return
        searcher: Notion searcher instance
        
    Returns:
        List of recently edited pages
    """
    try:
        return await searcher.get_recent_pages(max_results)
    except Exception as e:
        logger.error(f"Failed to get recent pages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pages/{page_id}", response_model=NotionPage)
async def get_page(
    page_id: str,
    include_properties: bool = True,
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Get a specific page by ID.
    
    Args:
        page_id: ID of the page to retrieve
        include_properties: Whether to include page properties
        fetcher: Notion fetcher instance
        
    Returns:
        Page data with content
    """
    try:
        return await fetcher.fetch_page(page_id, include_properties)
    except Exception as e:
        logger.error(f"Failed to get page {page_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/context", response_model=ContextResponse)
async def get_context(
    context_request: ContextRequest,
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Get context for multiple pages.
    
    Args:
        context_request: Request with page IDs and formatting options
        fetcher: Notion fetcher instance
        
    Returns:
        Formatted context for LLM analysis
    """
    try:
        # Fetch pages
        pages = await fetcher.fetch_pages(
            context_request.page_ids, 
            context_request.include_properties
        )
        
        # Format context based on requested format
        context = _format_context(pages, context_request.format)
        
        return ContextResponse(
            pages=pages,
            context=context,
            total_pages=len(pages)
        )
        
    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _format_context(pages: List[NotionPage], format_type: str) -> str:
    """Format pages into context string.
    
    Args:
        pages: List of Notion pages
        format_type: Format type (text, json, markdown)
        
    Returns:
        Formatted context string
    """
    if format_type == "json":
        import json
        return json.dumps([page.dict() for page in pages], indent=2, default=str)
    
    elif format_type == "markdown":
        context_parts = []
        for page in pages:
            context_parts.append(f"# {page.title}")
            context_parts.append(f"**URL:** {page.url}")
            context_parts.append(f"**Created:** {page.created_time}")
            context_parts.append(f"**Last Edited:** {page.last_edited_time}")
            context_parts.append("")
            context_parts.append(page.content)
            context_parts.append("---")
        return "\n".join(context_parts)
    
    else:  # text format
        context_parts = []
        for page in pages:
            context_parts.append(f"Page: {page.title}")
            context_parts.append(f"URL: {page.url}")
            context_parts.append(f"Created: {page.created_time}")
            context_parts.append(f"Last Edited: {page.last_edited_time}")
            context_parts.append("")
            context_parts.append(page.content)
            context_parts.append("\n" + "="*50 + "\n")
        return "\n".join(context_parts)

@router.get("/query", response_model=QueryResponse)
async def query_notion(
    q: str,
    max_results: int = 10,
    per_database_page_limit: int = 10,
    include_blocks: bool = True,
    expand_databases: bool = True,
    db_start_cursor: Optional[str] = None,
    format: str = "both",
    searcher: NotionSearcher = Depends(get_searcher),
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Query endpoint for search and analytics queries.
    
    Steps:
    1) Use searcher to find relevant pages/databases (searcher.search_pages_and_databases)
    2) For each database: fetch its pages (fetcher.query_database)
    3) For each page (from search or db): recursively fetch blocks (fetcher.fetch_page_with_blocks)
    4) Use parser to format content for LLM (parser.flatten_blocks_to_text, parser.blocks_to_elements)
    5) Return clean structured JSON with the query and results
    """
    try:
        logger.info(f"Processing query: '{q}' with max_results: {max_results}")
        
        # Validate bounds
        max_results = 50 if max_results > 50 else max_results
        max_results = 1 if max_results < 1 else max_results
        per_database_page_limit = 50 if per_database_page_limit > 50 else per_database_page_limit
        per_database_page_limit = 1 if per_database_page_limit < 1 else per_database_page_limit

        parser = NotionParser()

        # Normalize format
        fmt = (format or "both").lower()
        if fmt not in ("text", "elements", "both"):
            fmt = "both"

        # 1) Search for pages and databases
        top_matches = searcher.search_pages_and_databases(q, max_results=max_results)

        final_results = []

        for match in top_matches:
            obj_type = match.get("object_type")
            try:
                if obj_type == "database":
                    # 2) Expand database → pages
                    db_id = match.get("id")
                    db_title = match.get("title")
                    if not expand_databases:
                        final_results.append({
                            "object_type": "database",
                            "id": db_id,
                            "title": db_title,
                            "url": match.get("url"),
                            "last_edited": match.get("last_edited"),
                        })
                        continue

                    query_args = {"page_size": per_database_page_limit}
                    if db_start_cursor:
                        query_args["start_cursor"] = db_start_cursor
                    pages = fetcher.query_database(db_id, query_args)

                    expanded_pages = []
                    for page in pages[:per_database_page_limit]:
                        try:
                            # 3) Recursively fetch page blocks
                            content_text = ""
                            elements = []
                            total_blocks = 0
                            if include_blocks:
                                page_full = fetcher.fetch_page_with_blocks(page["id"]) 
                                blocks = page_full.get("blocks", [])
                                total_blocks = page_full.get("total_blocks", 0)
                                # 4) Format for LLM per requested format
                                if fmt in ("text", "both"):
                                    content_text = parser.flatten_blocks_to_text(blocks)
                                if fmt in ("elements", "both"):
                                    elements = parser.blocks_to_elements(blocks)
                            expanded_pages.append({
                                "id": page["id"],
                                "title": page.get("title"),
                                "url": page.get("url"),
                                **({"content_text": content_text} if fmt in ("text", "both") else {}),
                                **({"elements": elements} if fmt in ("elements", "both") else {}),
                                "total_blocks": total_blocks
                            })
                        except Exception as e:
                            # Per-page error: continue other pages
                            logger.warning(f"Failed to fetch/parse page {page.get('id')}: {e}")
                            expanded_pages.append({
                                "id": page.get("id"),
                                "title": page.get("title"),
                                "url": page.get("url"),
                                "error": str(e)
                            })

                    final_results.append({
                        "object_type": "database",
                        "id": db_id,
                        "title": db_title,
                        "url": match.get("url"),
                        "last_edited": match.get("last_edited"),
                        "pages": expanded_pages
                    })
                else:
                    # Treat as single page
                    page_id = match.get("id")
                    content_text = ""
                    elements = []
                    total_blocks = 0
                    if include_blocks:
                        page_full = fetcher.fetch_page_with_blocks(page_id)
                        blocks = page_full.get("blocks", [])
                        total_blocks = page_full.get("total_blocks", 0)
                        if fmt in ("text", "both"):
                            content_text = parser.flatten_blocks_to_text(blocks)
                        if fmt in ("elements", "both"):
                            elements = parser.blocks_to_elements(blocks)
                    final_results.append({
                        "object_type": "page",
                        "id": page_id,
                        "title": match.get("title"),
                        "url": match.get("url"),
                        "last_edited": match.get("last_edited"),
                        "total_blocks": total_blocks,
                        **({"content_text": content_text} if fmt in ("text", "both") else {}),
                        **({"elements": elements} if fmt in ("elements", "both") else {})
                    })
            except Exception as e:
                # Per-object error: include error but keep other objects
                logger.warning(f"Failed to process search match {match.get('id')}: {e}")
                final_results.append({
                    "object_type": obj_type,
                    "id": match.get("id"),
                    "title": match.get("title"),
                    "url": match.get("url"),
                    "error": str(e)
                })

        logger.info(f"Query '{q}' integration returned {len(final_results)} result entries")
        return QueryResponse(query=q, results=final_results, status="success")

    except ValueError as e:
        logger.warning(f"Invalid query parameter: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Notion API connection error for query '{q}': {e}")
        raise HTTPException(status_code=503, detail="Notion API connection failed")
    except Exception as e:
        logger.error(f"Query processing failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@router.get("/databases/{database_id}/export")
async def export_database(
    database_id: str,
    include_blocks: bool = True,
    format: str = "both",
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Export pages from a specific Notion database with optional blocks.

    Steps:
    1) Query database pages with pagination (fetcher.query_database)
    2) For each page, optionally fetch blocks (fetcher.fetch_page_with_blocks)
    3) Format using parser (parser.flatten_blocks_to_text / blocks_to_elements)
    4) Return results and a cursor for continuing export
    """
    try:
        # Bounds and format normalization
        fmt = (format or "both").lower()
        if fmt not in ("text", "elements", "both"):
            fmt = "both"

        parser = NotionParser()

        # Query entire database (no page limit) leveraging built-in pagination
        # Note: query_database returns already-processed page metadata
        processed_pages = fetcher.query_database(database_id)

        results = []
        for meta in processed_pages:
            try:
                # Minimal page metadata
                page_id = meta.get("id")

                content_text = ""
                elements = []
                total_blocks = 0
                if include_blocks and page_id:
                    page_full = fetcher.fetch_page_with_blocks(page_id)
                    blocks = page_full.get("blocks", [])
                    total_blocks = page_full.get("total_blocks", 0)
                    if fmt in ("text", "both"):
                        content_text = parser.flatten_blocks_to_text(blocks)
                    if fmt in ("elements", "both"):
                        elements = parser.blocks_to_elements(blocks)

                results.append({
                    **({
                        "id": meta.get("id"),
                        "title": meta.get("title"),
                        "url": meta.get("url"),
                        "created_time": meta.get("created_time"),
                        "last_edited_time": meta.get("last_edited_time"),
                    }),
                    "total_blocks": total_blocks,
                    **({"content_text": content_text} if fmt in ("text", "both") else {}),
                    **({"elements": elements} if fmt in ("elements", "both") else {}),
                })
            except Exception as e:
                logger.warning(f"Failed to export page {meta.get('id')}: {e}")
                results.append({"id": meta.get("id"), "error": str(e)})

        return {
            "database_id": database_id,
            "count": len(results),
            "has_more": False,
            "next_cursor": None,
            "results": results,
        }

    except ValueError as e:
        logger.warning(f"Invalid export parameter: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Notion API connection error for export of '{database_id}': {e}")
        raise HTTPException(status_code=503, detail="Notion API connection failed")
    except Exception as e:
        logger.error(f"Database export failed for '{database_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Database export failed: {str(e)}")

@router.get("/search/databases")
async def search_databases(
    q: str,
    max_results: int = 10,
    per_database_page_limit: int = 10,
    include_blocks: bool = False,
    format: str = "both",
    minimal: bool = False,
    minimal_mode: str = "string",  # "string" | "lines"
    searcher: NotionSearcher = Depends(get_searcher),
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Search for databases by query and list their items (pages).

    Steps:
    - Use searcher to find databases
    - For each database, list pages (optionally fetch/parse blocks per page)
    - Return structured JSON with database metadata and page items
    """
    try:
        max_results = 50 if max_results > 50 else max_results
        max_results = 1 if max_results < 1 else max_results
        per_database_page_limit = 50 if per_database_page_limit > 50 else per_database_page_limit
        per_database_page_limit = 1 if per_database_page_limit < 1 else per_database_page_limit

        fmt = (format or "both").lower()
        if fmt not in ("text", "elements", "both"):
            fmt = "both"
        if minimal_mode not in ("string", "lines"):
            minimal_mode = "string"

        parser = NotionParser()

        matches = searcher.search_pages_and_databases(q, max_results=max_results)
        db_matches = [m for m in matches if m.get("object_type") == "database"]

        results = []
        for db in db_matches:
            try:
                db_id = db.get("id")
                pages = fetcher.query_database(db_id, {"page_size": per_database_page_limit})
                items = []
                for p in pages[:per_database_page_limit]:
                    try:
                        content_text = ""
                        elements = []
                        total_blocks = 0
                        if include_blocks:
                            full = fetcher.fetch_page_with_blocks(p["id"]) 
                            blocks = full.get("blocks", [])
                            total_blocks = full.get("total_blocks", 0)
                            if fmt in ("text", "both"):
                                content_text = parser.flatten_blocks_to_text(blocks)
                            if fmt in ("elements", "both"):
                                elements = parser.blocks_to_elements(blocks)
                        if minimal:
                            items.append({
                                "title": parser.sanitize_text(p.get("title") or ""),
                                **(
                                    {"content": parser.sanitize_text(content_text)}
                                    if fmt in ("text", "both") and minimal_mode == "string" else {}
                                ),
                                **(
                                    {"content_lines": parser.sanitize_text(content_text).split("\n")}
                                    if fmt in ("text", "both") and minimal_mode == "lines" else {}
                                )
                            })
                        else:
                            items.append({
                                "id": p.get("id"),
                                "title": parser.sanitize_text(p.get("title") or ""),
                                "url": p.get("url"),
                                "created_time": p.get("created_time"),
                                "last_edited_time": p.get("last_edited_time"),
                                "total_blocks": total_blocks,
                                **({"content_text": parser.sanitize_text(content_text)} if fmt in ("text", "both") else {}),
                                **({"elements": elements} if fmt in ("elements", "both") else {}),
                            })
                    except Exception as e:
                        logger.warning(f"Failed to process page {p.get('id')}: {e}")
                        items.append({"id": p.get("id"), "title": p.get("title"), "error": str(e)})

                if minimal:
                    results.append({
                        "database": db.get("title"),
                        "items": items
                    })
                else:
                    results.append({
                        "id": db_id,
                        "title": db.get("title"),
                        "url": db.get("url"),
                        "last_edited": db.get("last_edited"),
                        "items": items
                    })
            except Exception as e:
                logger.warning(f"Failed to expand database {db.get('id')}: {e}")
                results.append({"id": db.get("id"), "title": db.get("title"), "error": str(e)})

        return {"query": q, "results": results}

    except ValueError as e:
        logger.warning(f"Invalid query parameter: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Notion API connection error for db search '{q}': {e}")
        raise HTTPException(status_code=503, detail="Notion API connection failed")
    except Exception as e:
        logger.error(f"Database search failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Database search failed: {str(e)}")

@router.get("/search/pages")
async def search_pages_endpoint(
    q: str,
    max_results: int = 10,
    include_blocks: bool = True,
    format: str = "both",
    minimal: bool = False,
    minimal_mode: str = "string",
    searcher: NotionSearcher = Depends(get_searcher),
    fetcher: NotionFetcher = Depends(get_fetcher)
):
    """Search for pages by query and list their parsed content.

    Steps:
    - Use searcher to find pages
    - For each page, optionally fetch/parse blocks
    - Return structured JSON with page metadata and content blobs
    """
    try:
        max_results = 50 if max_results > 50 else max_results
        max_results = 1 if max_results < 1 else max_results

        fmt = (format or "both").lower()
        if fmt not in ("text", "elements", "both"):
            fmt = "both"
        if minimal_mode not in ("string", "lines"):
            minimal_mode = "string"

        parser = NotionParser()
        matches = searcher.search_pages_and_databases(q, max_results=max_results)
        page_matches = [m for m in matches if m.get("object_type") == "page"]

        results = []
        for m in page_matches:
            try:
                content_text = ""
                elements = []
                total_blocks = 0
                if include_blocks:
                    full = fetcher.fetch_page_with_blocks(m.get("id"))
                    blocks = full.get("blocks", [])
                    total_blocks = full.get("total_blocks", 0)
                    if fmt in ("text", "both"):
                        content_text = parser.flatten_blocks_to_text(blocks)
                    if fmt in ("elements", "both"):
                        elements = parser.blocks_to_elements(blocks)
                if minimal:
                    results.append({
                        "title": parser.sanitize_text(m.get("title") or ""),
                        **(
                            {"content": parser.sanitize_text(content_text)}
                            if fmt in ("text", "both") and minimal_mode == "string" else {}
                        ),
                        **(
                            {"content_lines": parser.sanitize_text(content_text).split("\n")}
                            if fmt in ("text", "both") and minimal_mode == "lines" else {}
                        )
                    })
                else:
                    results.append({
                        "id": m.get("id"),
                        "title": parser.sanitize_text(m.get("title") or ""),
                        "url": m.get("url"),
                        "last_edited": m.get("last_edited"),
                        "total_blocks": total_blocks,
                        **({"content_text": parser.sanitize_text(content_text)} if fmt in ("text", "both") else {}),
                        **({"elements": elements} if fmt in ("elements", "both") else {}),
                    })
            except Exception as e:
                logger.warning(f"Failed to parse page {m.get('id')}: {e}")
                results.append({"id": m.get("id"), "title": m.get("title"), "error": str(e)})

        return {"query": q, "results": results}

    except ValueError as e:
        logger.warning(f"Invalid query parameter: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Notion API connection error for page search '{q}': {e}")
        raise HTTPException(status_code=503, detail="Notion API connection failed")
    except Exception as e:
        logger.error(f"Page search failed for '{q}': {e}")
        raise HTTPException(status_code=500, detail=f"Page search failed: {str(e)}")
