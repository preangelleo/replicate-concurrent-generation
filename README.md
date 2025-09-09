# Replicate Concurrent Generation - Simple Version

A lightweight, high-performance concurrent image generation service using Replicate API.

## Features

- **Simple 3-Model Support**: flux-dev, flux-kontext-max, and qwen-image only
- **True Async Concurrency**: Handles multiple requests simultaneously without blocking
- **Global Rate Limiting**: Respects Replicate's 600 requests/minute limit
- **Dual Authentication**: Admin API key for internal use, or user-provided API keys
- **Docker Ready**: Easy deployment with health checks

## Supported Models

1. **black-forest-labs/flux-dev** (alias: `flux-dev`)
   - Fast text-to-image generation
   - No reference image support
   - Default output: `.jpg`

2. **black-forest-labs/flux-kontext-max** (alias: `flux-kontext-max`)
   - Text-to-image with optional reference image editing
   - Supports input_image parameter
   - Default output: `.png`

3. **qwen/qwen-image** (alias: `qwen-image`)
   - Advanced text rendering and image generation
   - No reference image support
   - Default output: `.webp`

## API Endpoints

### Authentication

Two authentication methods:

1. **Admin API Key** (for internal services):
   ```
   X-Admin-API-Key: your-admin-key
   ```
   Uses pre-configured Replicate token from environment.

2. **User API Key** (for external users):
   ```
   X-Replicate-API-Key: your-replicate-api-token
   ```
   User provides their own Replicate API token.

### Generate Single Image

```http
POST /generate
Content-Type: application/json
X-Admin-API-Key: your-admin-key  # OR X-Replicate-API-Key: user-token

{
  "model_name": "flux-dev",
  "prompt": "A beautiful sunset over mountains",
  "aspect_ratio": "16:9",
  "output_quality": 90
}
```

### Generate Batch Images

```http
POST /generate-batch
Content-Type: application/json
X-Admin-API-Key: your-admin-key

{
  "model_name": "qwen-image",
  "prompts": [
    "A cat sitting on a chair",
    "A dog running in a park",
    "A bird flying in the sky"
  ],
  "aspect_ratio": "1:1"
}
```

### Health Check

```http
GET /health
```

### List Models

```http
GET /models
```

### Get Status

```http
GET /status
```

### Configure Concurrency (Admin Only)

```http
POST /configure
Content-Type: application/json
X-Admin-API-Key: your-admin-key

{
  "concurrent_limit": 15,
  "requests_per_minute": 500
}
```

## Environment Variables

Create a `.env` file:

```bash
# Replicate API Configuration
REPLICATE_API_TOKEN=your-replicate-api-token

# Concurrency Settings
REPLICATE_CONCURRENT_LIMIT=10
REPLICATE_REQUESTS_PER_MINUTE=600

# Admin API Key (for internal use)
CONCURRENT_DOCKER_ADMIN_API_KEY=your-admin-api-key
```

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Run the service:
   ```bash
   python app.py
   ```

The service will start on `http://localhost:5000`.

## Docker Deployment

1. Build the image:
   ```bash
   docker build -t replicate-concurrent-generation .
   ```

2. Run the container:
   ```bash
   docker run -d \
     --name replicate-concurrent \
     -p 5000:5000 \
     --env-file .env \
     replicate-concurrent-generation
   ```

## Model Parameters

### flux-dev
- `seed`: Random seed (int)
- `go_fast`: Speed optimization (bool, default: true)
- `guidance`: Guidance scale (float, 0-10, default: 3)
- `aspect_ratio`: Image aspect ratio (1:1, 16:9, 9:16, 3:4, 4:3)
- `output_format`: File format (webp, jpg, png)
- `output_quality`: Quality (int, 0-100, default: 80)
- `num_inference_steps`: Steps (int, 1-50, default: 28)

### flux-kontext-max
- `input_image`: Reference image for editing (file path or URL)
- `aspect_ratio`: Image aspect ratio (match_input_image, 1:1, 16:9, 9:16, etc.)
- `output_format`: File format (jpg, png)
- `seed`: Random seed (int)
- `safety_tolerance`: Safety level (int, 0-6, default: 2)
- `prompt_upsampling`: Enhance prompt (bool, default: false)

### qwen-image
- `guidance`: Guidance scale (float, 0-10, default: 4)
- `aspect_ratio`: Image aspect ratio (1:1, 16:9, 9:16, 3:4, 4:3)
- `output_format`: File format (webp, jpg, png)
- `output_quality`: Quality (int, 0-100, default: 80)
- `enhance_prompt`: Enhance prompt (bool, default: false)
- `negative_prompt`: What to avoid (string)
- `num_inference_steps`: Steps (int, 1-100, default: 50)

## Concurrency Control

The service implements two levels of concurrency control:

1. **Concurrent Request Limit**: Maximum simultaneous API calls (default: 10)
2. **Rate Limiting**: Maximum requests per minute (default: 600)

Both limits are enforced globally across all users to prevent exceeding Replicate API limits.

## Error Handling

The service provides detailed error responses:

- `401`: Authentication error (invalid or missing API key)
- `400`: Validation error (missing parameters, unsupported model)
- `500`: Generation error (API failures, timeouts)

## Architecture

- **Async Functions**: All model calls use `asyncio.to_thread()` for non-blocking execution
- **Global Semaphore**: Shared concurrency control across all requests
- **Rate Limiting**: Time-based request tracking with automatic backoff
- **Thread Pool**: Flask integration with async operations
- **Context Managers**: Automatic resource management and cleanup

## Version History

- **2.0-simple**: Complete rewrite with 3 models only, simplified architecture
- **1.x**: Original complex version with multiple models and fallback chains