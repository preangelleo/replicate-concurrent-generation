# Replicate Concurrent Generation API

A high-performance Docker service for concurrent image generation using Replicate models with External Semaphore Pattern, 3-tier authentication, and URL-direct-return architecture.

## Purpose & Overview

This service provides efficient concurrent access to Replicate's image generation models while maintaining proper rate limiting and API quota management. It's designed for applications that need to generate multiple images simultaneously without exceeding account limits or encountering rate limiting errors.

### Key Features

- **External Semaphore Pattern**: Cross-service concurrency control for multi-service deployments
- **3-tier authentication system**: Flexible authentication for different deployment scenarios  
- **URL Direct Return**: Direct Replicate URL responses eliminating file management overhead
- **Perfect Input/Output Correspondence**: List of Dict structure with exact task mapping
- **Global Rate Limiting**: Prevents API account limit violations regardless of concurrent load

## Supported Models

| Model | ID | Purpose | Key Features |
|-------|----|---------| -------------|
| **Flux Dev** | `flux-dev` | Fast text-to-image | High-speed generation, flexible parameters |
| **Flux Context Max** | `flux-kontext-max` | Image editing/context | Input image support, context-aware |
| **Qwen Image** | `qwen-image` | Chinese-optimized | Supports Chinese prompts, cultural content |

## Quick Start with Docker

```bash
# Pull and run the latest image
docker run -d \
  --name replicate-generation \
  -p 5003:5003 \
  -e REPLICATE_API_TOKEN="r8_your_replicate_token_here" \
  -e CONCURRENT_DOCKER_ADMIN_API_KEY="your_secure_admin_key" \
  betashow/replicate-concurrent-generation:v3.0
```

## Environment Configuration

Create a `.env` file:

```env
# Required Configuration
REPLICATE_API_TOKEN=r8_your_replicate_api_token_here
CONCURRENT_DOCKER_ADMIN_API_KEY=your_secure_admin_api_key

# Optional Configuration  
FLASK_PORT=5003
FLASK_HOST=0.0.0.0
REPLICATE_CONCURRENT_LIMIT=60
REPLICATE_REQUESTS_PER_MINUTE=600
```

## API Reference

### Base URL
```
http://localhost:5003
```

### Authentication Options

#### Option 1: Admin API Key (Header) - Recommended for Internal Services
```http
X-Admin-API-Key: your_admin_key
```
Uses server's configured Replicate token with highest priority.

#### Option 2: User Credentials (Request Payload) - For External Clients
```json
{
  "credentials": {
    "replicate_api_token": "user_replicate_token"
  }
}
```

#### Option 3: Environment Fallback (Backward Compatibility)
No authentication headers - uses server environment variables.

### External Semaphore Management

#### List Global Semaphores
```http
GET /global-semaphores
```

**Response:**
```json
{
  "count": 2,
  "global_semaphores": ["image-generation-global", "cross-service-limit"]
}
```

#### Register Global Semaphore (Admin Only)
```http
POST /global-semaphores
X-Admin-API-Key: your_admin_key

{
  "semaphore_id": "my-global-semaphore",
  "limit": 20
}
```

### Image Generation Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "replicate-concurrent-generation",
  "version": "3.0 (External Semaphore Pattern + URL-Direct-Return)",
  "supported_models": ["flux-dev", "flux-kontext-max", "qwen-image"],
  "concurrency_status": {
    "concurrent_limit": 60,
    "requests_per_minute_limit": 600
  }
}
```

#### 2. Single Image Generation
```http
POST /generate
Content-Type: application/json
X-Admin-API-Key: your_admin_key

{
  "model_name": "flux-dev",
  "prompt": "A serene mountain landscape at sunset",
  "output_filename": "mountain_sunset",
  "aspect_ratio": "16:9",
  "external_semaphore_id": "my-global-semaphore"
}
```

**Response:**
```json
{
  "success": true,
  "model_name": "flux-dev",
  "prompt": "A serene mountain landscape at sunset",
  "output_filename": "mountain_sunset",
  "generated_files": [
    {
      "url": "https://replicate.delivery/xezq/JnAq6ke6EGzvTiO6eXs7OtbZINX7vCPDdd7c4xtWWr8ocoTVA/out-0.webp",
      "filename": "mountain_sunset.jpg"
    }
  ],
  "count": 1,
  "external_semaphore_used": true,
  "semaphore_id": "my-global-semaphore"
}
```

#### 3. Batch Generation

**Tasks Format (List of Dictionary):**
```http
POST /generate-batch
Content-Type: application/json
X-Admin-API-Key: your_admin_key

{
  "model_name": "flux-dev",
  "tasks": [
    {
      "prompt": "A red sports car",
      "output_filename": "red_car.jpg",
      "aspect_ratio": "16:9"
    },
    {
      "prompt": "A blue ocean wave",
      "output_filename": "blue_wave",
      "num_outputs": 2
    },
    {
      "prompt": "A green forest path",
      "output_filename": "forest_path.png",
      "guidance": 5.0
    }
  ],
  "external_semaphore_id": "my-global-semaphore"
}
```

**Response (Perfect Input/Output Correspondence):**
```json
{
  "success": true,
  "model_name": "flux-dev",
  "total_tasks": 3,
  "successful_count": 3,
  "failed_count": 0,
  "successful_results": [
    {
      "task_index": 0,
      "prompt": "A red sports car",
      "output_filename": "red_car.jpg",
      "generated_files": [
        {
          "url": "https://replicate.delivery/xezq/1wLmlsFuQXZyKtwaniNcRu7wrHhTDfXNHFGp6Y8AY1NVO0pKA/out-0.webp",
          "filename": "red_car.jpg"
        }
      ],
      "count": 1
    },
    {
      "task_index": 1,
      "prompt": "A blue ocean wave",
      "output_filename": "blue_wave",
      "generated_files": [
        {
          "url": "https://replicate.delivery/xezq/uByv2SwpTQqdHp3tpui1qbbt5pycnexJxncXvaFyXCYWO0pKA/out-0.webp",
          "filename": "blue_wave_1.jpg"
        },
        {
          "url": "https://replicate.delivery/xezq/aBcv3SwpTQqdHp3tpui1qbbt5pycnexJxncXvaFyXCYWO0pKA/out-1.webp",
          "filename": "blue_wave_2.jpg"
        }
      ],
      "count": 2
    },
    {
      "task_index": 2,
      "prompt": "A green forest path",
      "output_filename": "forest_path.png",
      "generated_files": [
        {
          "url": "https://replicate.delivery/xezq/dEfg4SwpTQqdHp3tpui1qbbt5pycnexJxncXvaFyXCYWO0pKA/out-0.webp",
          "filename": "forest_path.png"
        }
      ],
      "count": 1
    }
  ],
  "failed_results": [],
  "external_semaphore_used": true,
  "semaphore_id": "my-global-semaphore"
}
```

**Legacy Format Support (Backward Compatibility):**
```json
{
  "model_name": "flux-dev",
  "prompts": ["A red car", "A blue house"],
  "custom_filenames": ["red_car", "blue_house"]
}
```

### Key Benefits: Input/Output Perfect Correspondence

#### Input Structure:
- **Tasks Array**: List of task objects
- **Each Task**: `{prompt, output_filename, ...parameters}`
- **Flexible**: Each task can have individual parameters

#### Output Structure:
- **Results Array**: Exactly matches input tasks by index
- **Each Result**: `{task_index, prompt, output_filename, generated_files, count}`
- **Generated Files**: Array of `{url, filename}` objects
- **Perfect Mapping**: `tasks[i]` → `successful_results[i]`

## Advanced Features

### External Semaphore Integration
```json
{
  "model_name": "flux-dev",
  "prompt": "Test with global concurrency",
  "external_semaphore_id": "cross-service-limit"
}
```

### User Credentials Authentication
```json
{
  "model_name": "flux-dev", 
  "prompt": "User's own API generation",
  "credentials": {
    "replicate_api_token": "user_r8_token_here"
  }
}
```

### Multiple Output Images
```json
{
  "model_name": "flux-dev",
  "prompt": "Generate variations",
  "output_filename": "variations",
  "num_outputs": 4
}
```
**Result**: `variations_1.jpg`, `variations_2.jpg`, `variations_3.jpg`, `variations_4.jpg`

## Complete Model Parameters

### 1. Flux Dev (`flux-dev`)
```json
{
  "model_name": "flux-dev",
  "prompt": "Required text prompt",
  "output_filename": "my_image",
  
  // Image Settings
  "aspect_ratio": "16:9",           // "1:1", "16:9", "9:16", "3:4", "4:3"
  "megapixels": "1",                // "1", "0.25"
  "output_format": "webp",          // "webp", "jpg", "png"
  "output_quality": 80,             // 0-100
  
  // Generation Control
  "seed": 42,                       // Integer for reproducible results
  "guidance": 3.0,                  // 0-10, prompt adherence strength
  "num_inference_steps": 28,        // 1-50, quality vs speed
  "prompt_strength": 0.8,           // 0-1, prompt influence
  "num_outputs": 1,                 // 1-4, number of images
  
  // Performance
  "go_fast": true,                  // Enable fast mode
  "disable_safety_checker": false   // Disable NSFW filter
}
```

### 2. Flux Context Max (`flux-kontext-max`)
```json
{
  "model_name": "flux-kontext-max",
  "prompt": "Transform this image...",
  "output_filename": "edited_image",
  
  // Required Input
  "input_image": "https://example.com/image.jpg",  // URL or file path
  
  // Image Settings
  "aspect_ratio": "match_input_image",             // "match_input_image", "1:1", "16:9", etc.
  "output_format": "png",                          // "jpg", "png"
  
  // Generation Control
  "seed": 42,                                      // Reproducible results
  "safety_tolerance": 2,                           // 0-6, content filtering
  "prompt_upsampling": false                       // Enhance prompt quality
}
```

### 3. Qwen Image (`qwen-image`)
```json
{
  "model_name": "qwen-image",
  "prompt": "A beautiful landscape",
  "output_filename": "qwen_artwork",
  
  // Image Settings  
  "aspect_ratio": "16:9",             // "1:1", "16:9", "9:16", "3:4", "4:3"
  "output_format": "webp",            // "webp", "jpg", "png"
  "output_quality": 80,               // 0-100
  "image_size": "optimize_for_quality", // "optimize_for_quality", "optimize_for_speed"
  
  // Generation Control
  "guidance": 4.0,                    // 0-10, prompt adherence
  "num_inference_steps": 50,          // 1-100, quality vs speed
  "lora_scale": 1.0,                  // 0-2, LoRA influence
  "enhance_prompt": false,            // Auto-enhance prompts
  "negative_prompt": "",              // What to avoid
  
  // Performance
  "go_fast": true                     // Fast mode
}
```

## Docker Deployment

### Production Deployment
```bash
# Build latest image
docker build -t betashow/replicate-concurrent-generation:v3.0 .

# Run with external semaphore support
docker run -d \
  --name replicate-v3 \
  -p 5003:5003 \
  -e REPLICATE_API_TOKEN="r8_your_token" \
  -e CONCURRENT_DOCKER_ADMIN_API_KEY="your_admin_key" \
  --restart unless-stopped \
  betashow/replicate-concurrent-generation:v3.0
```

### Docker Compose
```yaml
version: '3.8'
services:
  replicate-generation:
    image: betashow/replicate-concurrent-generation:v3.0
    ports:
      - "5003:5003"
    environment:
      - REPLICATE_API_TOKEN=r8_your_token_here
      - CONCURRENT_DOCKER_ADMIN_API_KEY=your_admin_key
      - FLASK_PORT=5003
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Error Handling

### Authentication Errors
```json
// Missing authentication
{
  "error": "Authentication failed. Provide 'X-Admin-API-Key' in headers or complete credentials in payload."
}

// Invalid admin key
{
  "error": "Invalid admin API key"
}

// Invalid user credentials
{
  "error": "Invalid Replicate API token in credentials"
}
```

### Generation Errors
```json
// Model not supported
{
  "error": "Model 'invalid-model' not supported",
  "supported_models": ["flux-dev", "flux-kontext-max", "qwen-image"]
}

// External semaphore not found
{
  "error": "External semaphore 'nonexistent-semaphore' not found"
}

// Batch format error
{
  "error": "Task 0 missing required field: prompt"
}
```

## Security Features

### Multi-tier Authentication
- **Admin keys**: Full access to server resources
- **User credentials**: Isolated user accounts  
- **Environment fallback**: Backward compatibility

### Safe URL Return
- **No local files**: Zero file security risks
- **Direct access**: Users get immediate Replicate URLs
- **No cleanup needed**: Eliminates timing-based vulnerabilities

### External Semaphore Security
- **Admin-only creation**: Only admin keys can register global semaphores
- **Isolated access**: Each semaphore operates independently
- **Thread-safe**: Robust concurrent access control

## Performance Features

### Speed Enhancements
- **URL Return**: Eliminate file download/upload overhead
- **Global Semaphores**: Optimal concurrent resource utilization
- **Structured Processing**: Efficient batch processing pipeline

### Resource Efficiency  
- **No File Storage**: Docker images never grow in size
- **Memory Optimization**: No file buffering required
- **Network Efficiency**: Direct URL return reduces bandwidth

### Scalability Features
- **Cross-service Coordination**: Share limits across multiple instances  
- **Dynamic Semaphore Management**: Create semaphores on demand
- **Flexible Authentication**: Support various deployment scenarios

## Testing

### Health Check Test
```bash
curl http://localhost:5003/health
```

### Admin Authentication Test
```bash
curl -X POST http://localhost:5003/generate \
  -H "X-Admin-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "flux-dev",
    "prompt": "Test admin auth",
    "output_filename": "admin_test"
  }'
```

### User Credentials Test
```bash
curl -X POST http://localhost:5003/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "flux-dev", 
    "prompt": "Test user auth",
    "output_filename": "user_test",
    "credentials": {
      "replicate_api_token": "user_r8_token_here"
    }
  }'
```

### Batch Generation Test
```bash
curl -X POST http://localhost:5003/generate-batch \
  -H "X-Admin-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "flux-dev",
    "tasks": [
      {"prompt": "Red car", "output_filename": "red_car.jpg"},
      {"prompt": "Blue house", "output_filename": "blue_house"}
    ]
  }'
```

### External Semaphore Test
```bash
# Register global semaphore
curl -X POST http://localhost:5003/global-semaphores \
  -H "X-Admin-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "semaphore_id": "test-global",
    "limit": 5
  }'

# Use global semaphore
curl -X POST http://localhost:5003/generate \
  -H "X-Admin-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "flux-dev",
    "prompt": "Test with global semaphore",
    "external_semaphore_id": "test-global"
  }'
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/enhancement`)
3. Commit your changes (`git commit -m 'Add enhancement'`)  
4. Push to branch (`git push origin feature/enhancement`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.