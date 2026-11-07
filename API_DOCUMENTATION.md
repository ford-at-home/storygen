# Richmond Storyline Generator API Documentation

## Overview

The Richmond Storyline Generator API provides endpoints for generating AI-powered stories that incorporate Richmond, Virginia's local context and culture.

Base URL: `http://localhost:5000` (development)

## Authentication

Currently, the API does not require authentication. This will be added in future versions.

## Endpoints

### 1. Welcome & Documentation
**GET /**

Returns API documentation and available endpoints.

#### Response
```json
{
  "service": "Richmond Storyline Generator API",
  "version": "1.0.0",
  "endpoints": {
    "/": "This documentation",
    "/health": "Health check endpoint",
    "/stats": "API usage statistics",
    "/styles": "Get available story styles",
    "/generate-story": {
      "method": "POST",
      "description": "Generate a Richmond story",
      "body": {
        "core_idea": "Your story idea (required, min 10 chars)",
        "style": "short_post|long_post|blog_post (optional, default: short_post)"
      }
    }
  }
}
```

### 2. Health Check
**GET /health**

Check if the API is running and healthy.

#### Response
```json
{
  "status": "healthy",
  "service": "richmond-storyline-generator",
  "version": "1.0.0",
  "timestamp": 1699123456.789
}
```

### 3. API Statistics
**GET /stats**

Get usage statistics for the API.

#### Response
```json
{
  "total_requests": 150,
  "successful_requests": 145,
  "failed_requests": 5,
  "average_response_time": 2.34
}
```

### 4. Story Styles
**GET /styles**

Get available story generation styles with descriptions.

#### Response
```json
{
  "styles": [
    {
      "id": "short_post",
      "name": "Short Post",
      "description": "A concise story perfect for social media (300-500 words)",
      "max_tokens": 1024
    },
    {
      "id": "long_post",
      "name": "Long Post",
      "description": "A detailed narrative with rich context (600-1000 words)",
      "max_tokens": 2048
    },
    {
      "id": "blog_post",
      "name": "Blog Post",
      "description": "A comprehensive article with full development (1000-2000 words)",
      "max_tokens": 4096
    }
  ]
}
```

### 5. Generate Story
**POST /generate-story**

Generate a Richmond-themed story based on the provided idea.

#### Request Body
```json
{
  "core_idea": "Richmond tech professionals returning from coastal cities",
  "style": "short_post"
}
```

#### Parameters
- `core_idea` (string, required): The main idea or theme for your story. Minimum 10 characters.
- `style` (string, optional): The format/length of the story. Options: `short_post`, `long_post`, `blog_post`. Default: `short_post`

#### Success Response (200 OK)
```json
{
  "story": "In the shadow of Richmond's historic skyline, a quiet revolution is unfolding...",
  "metadata": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "style": "short_post",
    "response_time": "3.45s",
    "context_retrieved": true
  }
}
```

#### Error Responses

**400 Bad Request - Validation Error**
```json
{
  "error": "Validation error",
  "details": {
    "core_idea": ["Core idea must be at least 10 characters"]
  }
}
```

**400 Bad Request - Missing Field**
```json
{
  "error": "Missing required field",
  "field": "core_idea"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred. Please try again later."
}
```

## Error Codes

| Status Code | Description |
|------------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid input or missing required fields |
| 404 | Not Found - Endpoint doesn't exist |
| 405 | Method Not Allowed |
| 500 | Internal Server Error |

## Rate Limiting

Currently, there are no rate limits. This will be implemented in future versions.

## CORS

CORS is enabled for the following origins in development:
- http://localhost:3000
- http://localhost:8080

## Examples

### Generate a Short Story
```bash
curl -X POST http://localhost:5000/generate-story \
  -H "Content-Type: application/json" \
  -d '{
    "core_idea": "A developer moves back to Richmond from Silicon Valley to start a craft brewery that hosts coding meetups"
  }'
```

### Generate a Blog Post
```bash
curl -X POST http://localhost:5000/generate-story \
  -H "Content-Type: application/json" \
  -d '{
    "core_idea": "The transformation of Scott's Addition from industrial district to innovation hub",
    "style": "blog_post"
  }'
```

### Check API Health
```bash
curl http://localhost:5000/health
```

### Get Available Styles
```bash
curl http://localhost:5000/styles
```

## Response Headers

All responses include the following security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

## Best Practices

1. **Core Idea**: Provide specific, detailed ideas for better story generation
2. **Style Selection**: Choose the appropriate style based on your intended use
3. **Error Handling**: Always check for error responses and handle them appropriately
4. **Response Time**: Story generation can take 2-5 seconds depending on style

## Future Enhancements

- Authentication and API keys
- Rate limiting per user
- Webhook support for async generation
- Batch story generation
- Story revision endpoints
- User session management