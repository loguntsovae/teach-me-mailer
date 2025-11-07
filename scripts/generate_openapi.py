#!/usr/bin/env python3
"""
Script to generate OpenAPI schema for the Teach Me Mailer API.
This script extracts the OpenAPI JSON schema from the FastAPI application
and saves it to docs/openapi.json for documentation purposes.
"""

import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def generate_openapi_schema():
    """Generate and save the OpenAPI schema."""
    try:
        from app.main import app
        
        # Get the OpenAPI schema
        openapi_schema = app.openapi()
        
        # Enhance the schema with additional information
        openapi_schema.update({
            "info": {
                "title": "Teach Me Mailer API",
                "description": """
A production-ready email service API built with FastAPI.

## Features

- 🔐 **Secure Authentication**: API key-based authentication with bcrypt hashing
- ⚡ **Rate Limiting**: Atomic rate limiting per API key with PostgreSQL
- 📧 **Reliable Email Delivery**: SMTP with STARTTLS encryption
- 📊 **Comprehensive Observability**: Prometheus metrics and structured logging
- 🧪 **Well Tested**: 100% test coverage with comprehensive test suite

## Authentication

All endpoints require authentication using the `X-API-Key` header:

```
X-API-Key: sk_test_your_api_key_here
```

API keys can be created using the provided management scripts or admin interface.

## Rate Limiting

Each API key has configurable daily email limits. When the limit is exceeded,
the API returns a 429 status code. Rate limits reset daily at midnight UTC.

## Error Handling

The API uses standard HTTP status codes and returns structured error responses:

- `200` - Success
- `202` - Accepted (for async operations)
- `401` - Unauthorized (invalid API key)
- `422` - Unprocessable Entity (validation error)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

## Support

For support and questions:
- GitHub Issues: https://github.com/loguntsovae/teach-me-mailer/issues
- Documentation: https://github.com/loguntsovae/teach-me-mailer/tree/main/docs
                """.strip(),
                "version": "1.0.0",
                "contact": {
                    "name": "Teach Me Mailer Support",
                    "url": "https://github.com/loguntsovae/teach-me-mailer",
                    "email": "support@example.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                },
                "termsOfService": "https://github.com/loguntsovae/teach-me-mailer/blob/main/LICENSE"
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                },
                {
                    "url": "https://api.example.com",
                    "description": "Production server"
                }
            ],
            "tags": [
                {
                    "name": "email",
                    "description": "Email sending operations"
                },
                {
                    "name": "health",
                    "description": "Health check and monitoring"
                },
                {
                    "name": "metrics", 
                    "description": "Prometheus metrics endpoint"
                }
            ]
        })
        
        # Ensure docs directory exists
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        # Write the schema to file
        schema_file = docs_dir / "openapi.json"
        with open(schema_file, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
        
        print(f"✅ OpenAPI schema generated successfully: {schema_file}")
        print(f"📊 Schema contains {len(openapi_schema.get('paths', {}))} endpoint(s)")
        
        # Also create a minimal schema summary
        create_api_summary(openapi_schema)
        
    except Exception as e:
        print(f"❌ Error generating OpenAPI schema: {e}")
        sys.exit(1)

def create_api_summary(schema):
    """Create a summary of API endpoints for quick reference."""
    summary = {
        "api_version": schema["info"]["version"],
        "title": schema["info"]["title"],
        "endpoints": []
    }
    
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        for method, details in methods.items():
            endpoint_info = {
                "path": path,
                "method": method.upper(),
                "summary": details.get("summary", ""),
                "description": details.get("description", ""),
                "tags": details.get("tags", [])
            }
            summary["endpoints"].append(endpoint_info)
    
    # Write summary to docs
    summary_file = Path("docs") / "api_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"📋 API summary created: {summary_file}")

if __name__ == "__main__":
    generate_openapi_schema()