"""Pydantic models for the Notion Context Service."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class NotionPage(BaseModel):
    """Model representing a Notion page."""
    
    id: str = Field(..., description="Unique identifier of the Notion page")
    title: str = Field(..., description="Title of the page")
    content: str = Field(..., description="Text content of the page")
    url: str = Field(..., description="URL of the Notion page")
    created_time: datetime = Field(..., description="When the page was created")
    last_edited_time: datetime = Field(..., description="When the page was last edited")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional page properties")

class SearchQuery(BaseModel):
    """Model for search queries."""
    
    query: str = Field(..., description="Search query string", min_length=1)
    max_results: int = Field(default=10, description="Maximum number of results to return", ge=1, le=100)
    filter_properties: Optional[Dict[str, Any]] = Field(default=None, description="Properties to filter by")

class SearchResponse(BaseModel):
    """Model for search response."""
    
    results: List[NotionPage] = Field(..., description="List of matching Notion pages")
    total_count: int = Field(..., description="Total number of results found")
    query: str = Field(..., description="Original search query")

class ContextRequest(BaseModel):
    """Model for context requests."""
    
    page_ids: List[str] = Field(..., description="List of Notion page IDs to fetch context for")
    include_properties: bool = Field(default=True, description="Whether to include page properties")
    format: str = Field(default="text", description="Format of the returned context", pattern="^(text|json|markdown)$")

class ContextResponse(BaseModel):
    """Model for context response."""
    
    pages: List[NotionPage] = Field(..., description="List of requested Notion pages")
    context: str = Field(..., description="Formatted context for LLM analysis")
    total_pages: int = Field(..., description="Total number of pages returned")

class HealthResponse(BaseModel):
    """Model for health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")

class QueryResponse(BaseModel):
    """Model for query endpoint response."""
    
    query: str = Field(..., description="The original query string")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Query results")
    status: str = Field(default="success", description="Query execution status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Query execution timestamp")
