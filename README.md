# Notion Context Service

A FastAPI-based REST API service that provides Notion content for LLM analysis. This service allows you to search, fetch, and format Notion pages and databases to provide context for large language models.

## Features

- **Search Notion Pages**: Search across all accessible Notion pages or within specific databases
- **Fetch Page Content**: Retrieve full page content with formatting
- **Context Formatting**: Format content for LLM analysis in text, JSON, or Markdown formats
- **Recent Pages**: Get recently edited pages
- **Property Extraction**: Extract and parse Notion page properties
- **RESTful API**: Clean, documented API endpoints with OpenAPI/Swagger documentation

## Project Structure

```
notion_context_service/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration and settings
│   ├── notion/
│   │   ├── client.py          # Notion API client wrapper
│   │   ├── searcher.py        # Page search functionality
│   │   ├── fetcher.py         # Page content fetching
│   │   └── parser.py          # Content parsing and formatting
│   ├── api/
│   │   └── endpoints.py       # FastAPI route definitions
│   └── models/
│       └── schema.py          # Pydantic data models
├── requirements.txt           # Python dependencies
├── .env                      # Environment variables (not committed)
└── README.md                 # This file
```

## Installation

1. **Clone or create the project directory**:
   ```bash
   mkdir notion_context_service
   cd notion_context_service
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Notion API credentials
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Notion API Configuration
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_database_id_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### Getting Notion API Credentials

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration
3. Copy the "Internal Integration Token" (this is your `NOTION_API_KEY`)
4. Share your Notion pages/databases with the integration
5. Copy the database ID from the URL (for `NOTION_DATABASE_ID`)

## Usage

### Starting the Server

```bash
# Development mode with auto-reload
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

#### Health Check
```http
GET /api/v1/health
```

#### Search Pages
```http
POST /api/v1/search
Content-Type: application/json

{
  "query": "machine learning",
  "max_results": 10,
  "filter_properties": {}
}
```

#### Search Database Pages
```http
POST /api/v1/search/database/{database_id}
Content-Type: application/json

{
  "query": "project updates",
  "max_results": 5
}
```

#### Get Recent Pages
```http
GET /api/v1/search/recent?max_results=10
```

#### Get Single Page
```http
GET /api/v1/pages/{page_id}?include_properties=true
```

#### Get Context for Multiple Pages
```http
POST /api/v1/context
Content-Type: application/json

{
  "page_ids": ["page-id-1", "page-id-2"],
  "include_properties": true,
  "format": "text"
}
```

### Example Usage with Python

```python
import requests

# Search for pages
response = requests.post("http://localhost:8000/api/v1/search", json={
    "query": "project documentation",
    "max_results": 5
})
results = response.json()

# Get context for LLM analysis
context_response = requests.post("http://localhost:8000/api/v1/context", json={
    "page_ids": ["page-id-1", "page-id-2"],
    "format": "markdown"
})
context = context_response.json()["context"]
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Structure

- **`app/main.py`**: FastAPI application setup and configuration
- **`app/config.py`**: Environment-based configuration management
- **`app/notion/client.py`**: Low-level Notion API client wrapper
- **`app/notion/searcher.py`**: High-level search functionality
- **`app/notion/fetcher.py`**: Page content retrieval and processing
- **`app/notion/parser.py`**: Content parsing and text extraction
- **`app/api/endpoints.py`**: FastAPI route definitions
- **`app/models/schema.py`**: Pydantic data models for request/response

## Error Handling

The service includes comprehensive error handling:

- **Connection Errors**: Proper handling of Notion API connection issues
- **Authentication Errors**: Clear messages for invalid API keys
- **Rate Limiting**: Respects Notion API rate limits
- **Content Parsing**: Graceful handling of malformed content
- **Validation**: Input validation using Pydantic models

## Security Considerations

- Store API keys in environment variables (never commit to version control)
- Use HTTPS in production
- Implement proper authentication for production use
- Validate and sanitize all inputs
- Consider rate limiting for public APIs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Ensure your Notion integration has proper permissions
4. Verify your API key and database IDs are correct
