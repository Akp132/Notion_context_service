"""Configuration settings for the Notion Context Service."""

import os
from dotenv import load_dotenv
from typing import Optional
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        """Initialize settings and validate required configurations."""
        # Notion API Configuration
        self.notion_api_key: str = self._get_notion_api_key()
        self.notion_database_id: Optional[str] = os.getenv("NOTION_DATABASE_ID")
        
        # Server Configuration
        self.host: str = os.getenv("HOST", "0.0.0.0")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.debug: bool = os.getenv("DEBUG", "True").lower() == "true"
        
        # API Configuration
        self.title: str = "Notion Context Service"
        self.description: str = "REST API service to deliver Notion context for LLM analysis"
        self.version: str = "1.0.0"
        
        # Validate configuration
        self._validate_config()
    
    def _get_notion_api_key(self) -> str:
        """Get and validate the Notion API key from environment variables.
        
        Returns:
            The Notion API key
            
        Raises:
            ValueError: If the API key is not found or invalid
        """
        api_key = os.getenv("NOTION_API_KEY")
        
        if not api_key:
            logger.warning("NOTION_API_KEY not found in environment variables")
            return ""
        
        # Basic validation - Notion API keys typically start with 'secret_'
        if not api_key.startswith("secret_"):
            logger.warning("NOTION_API_KEY does not appear to be a valid Notion integration token")
        
        return api_key
    
    def _validate_config(self) -> None:
        """Validate the configuration settings."""
        if not self.notion_api_key:
            logger.warning("Notion API key not configured - some endpoints may not work")
        
        if not self.notion_database_id:
            logger.info("Notion database ID not configured - using search across all accessible pages")
        
        logger.info(f"Configuration loaded - API key: {'✓' if self.notion_api_key else '✗'}, Database ID: {'✓' if self.notion_database_id else '✗'}")
    
    @property
    def is_notion_configured(self) -> bool:
        """Check if Notion is properly configured.
        
        Returns:
            True if Notion API key is available
        """
        return bool(self.notion_api_key)

# Global settings instance
settings = Settings()
