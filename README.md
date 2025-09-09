# Replicate Concurrent Generation API

A high-performance Docker service for concurrent image generation using Replicate models with intelligent concurrency management and dual authentication system.

## 🚀 Features

- ✅ **True Concurrent Processing**: Multi-threaded async architecture for simultaneous requests
- ✅ **Smart Rate Limiting**: Built-in concurrency control prevents API quota violations  
- ✅ **Dual Authentication**: Admin keys for internal services + user credentials for external clients
- ✅ **Production Ready**: Docker containerized with health monitoring and status endpoints
- ✅ **Multiple Models**: Support for Flux, Qwen, and other popular Replicate models
- ✅ **Flexible Output**: Configurable formats, aspect ratios, and generation parameters

## 📦 Supported Models

| Model | ID | Purpose | Parameters |
|-------|----|---------| -----------|
| **Flux Dev** | `flux-dev` | Fast text-to-image | aspect_ratio, guidance, steps |
| **Flux Context Max** | `flux-kontext-max` | Image editing with context | input_image, aspect_ratio |
| **Qwen Image** | `qwen-image` | Chinese-optimized generation | aspect_ratio, enhance_prompt |

*Model IDs map to full Replicate model names (e.g., `flux-dev` → `black-forest-labs/flux-dev`)*

## 🐳 Quick Start with Docker

```bash
# Pull and run the latest image
docker run -d \
  --name replicate-generation \
  -p 5003:5003 \
  -e REPLICATE_API_TOKEN="r8_your_replicate_token_here" \
  -e CONCURRENT_DOCKER_ADMIN_API_KEY="your_secure_admin_key" \
  -v $(pwd)/output:/app/output \
  betashow/replicate-concurrent-generation:latest
```

## ⚙️ Environment Configuration

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

## 🔌 API Reference

### Base URL
```
http://localhost:5003
```

### Authentication Headers

**Option 1: Admin Authentication**
```http
X-Admin-API-Key: your_admin_key
```
Uses server's configured Replicate token (recommended for internal services).

**Option 2: User Authentication** 
```http
X-Replicate-API-Key: user_replicate_token  
```
Uses client-provided Replicate token (for external integrations).

### Core Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "replicate-concurrent-generation", 
  "supported_models": ["flux-dev", "flux-kontext-max", "qwen-image"],
  "concurrency_status": {
    "concurrent_limit": 60,
    "requests_per_minute": 600
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
  "aspect_ratio": "16:9", 
  "output_format": "jpg"
}
```

**Response:**
```json
{
  "success": true,
  "model_name": "flux-dev",
  "files": ["output/flux_dev.jpg"],
  "count": 1
}
```

#### 3. Batch Image Generation (with Custom Filenames)

**Basic Batch Request:**
```http
POST /generate-batch
Content-Type: application/json
X-Admin-API-Key: your_admin_key

{
  "model_name": "flux-dev",
  "prompts": [
    "A red sports car",
    "A blue ocean wave", 
    "A green forest path"
  ],
  "aspect_ratio": "1:1"
}
```

**Advanced Batch with Custom Filenames (Recommended for Order Tracking):**
```http
POST /generate-batch
Content-Type: application/json
X-Admin-API-Key: your_admin_key

{
  "model_name": "flux-dev",
  "prompts": [
    "A red sports car",
    "A blue ocean wave", 
    "A green forest path"
  ],
  "custom_filenames": [
    "car_image_001",
    "ocean_wave_002",
    "forest_path_003"
  ],
  "aspect_ratio": "16:9"
}
```

**Response:**
```json
{
  "success": true,
  "model_name": "flux-dev",
  "total_prompts": 3,
  "successful_count": 3,
  "failed_count": 0,
  "successful_results": [
    {"prompt_index": 0, "files": ["output/batch_1/car_image_001.jpg"], "prompt": "A red sports car"},
    {"prompt_index": 1, "files": ["output/batch_2/ocean_wave_002.jpg"], "prompt": "A blue ocean wave"},
    {"prompt_index": 2, "files": ["output/batch_3/forest_path_003.jpg"], "prompt": "A green forest path"}
  ]
}
```

**🎯 Batch Processing Features:**
- **Order Preservation**: Results maintain exact correspondence with input prompts by index
- **Custom Filenames**: Use `custom_filenames` array to specify exact output names
- **Concurrent Processing**: All images generate simultaneously for maximum speed
- **Error Handling**: Failed generations don't affect successful ones
- **Flexible Parameters**: All model parameters work with batch processing

## 📋 Batch Order Management - 并行列表对应机制

### The Problem: Order Confusion in Concurrent Processing
When processing 20+ images concurrently, default filenames like `flux_dev_1.jpg`, `flux_dev_2.jpg` don't guarantee correspondence with your original prompt order.

### The Solution: Parallel Array Correspondence System
We use **two parallel arrays** to ensure perfect 1:1 correspondence between prompts and filenames:

```json
{
  "prompts": [
    "Red sports car",
    "Blue ocean wave", 
    "Green forest"
  ],
  "custom_filenames": [
    "car_image_001",
    "wave_image_002",
    "forest_image_003"
  ]
}
```

**How it works:**
- `prompts[0]` ↔ `custom_filenames[0]` → `car_image_001.jpg`
- `prompts[1]` ↔ `custom_filenames[1]` → `wave_image_002.jpg`  
- `prompts[2]` ↔ `custom_filenames[2]` → `forest_image_003.jpg`

**Why parallel arrays instead of dictionary:**
- ✅ Maintains exact processing order
- ✅ Simple validation (array length matching)
- ✅ Easy to understand and debug
- ✅ Works with any number of items

```json
{
  "model_name": "flux-dev",
  "prompts": [
    "Product photo of red sneakers",
    "Product photo of blue sneakers", 
    "Product photo of green sneakers"
  ],
  "custom_filenames": [
    "product_red_sneakers_001",
    "product_blue_sneakers_002", 
    "product_green_sneakers_003"
  ]
}
```

**Guaranteed Results:**
- `prompts[0]` → `product_red_sneakers_001.jpg`
- `prompts[1]` → `product_blue_sneakers_002.jpg` 
- `prompts[2]` → `product_green_sneakers_003.jpg`

### Batch Processing Best Practices:

1. **Always Use Sequential Numbering**: `image_001`, `image_002`, etc.
2. **Include Descriptive Names**: `red_car_001`, `blue_car_002`
3. **Match Array Lengths**: `custom_filenames.length === prompts.length`
4. **Use Consistent Naming**: Helps with post-processing and organization
5. **Plan File Extensions**: System auto-adds correct extensions (.jpg, .png, .webp)

#### 4. Service Status
```http
GET /status
```

#### 5. List Models
```http
GET /models
```

## 🎨 Complete Model Parameters Reference

### 1. Flux Dev (`flux-dev`) - Fast Text-to-Image Generation

**Purpose**: General-purpose text-to-image generation with fast processing times.

**All Available Parameters**:
```json
{
  "model_name": "flux-dev",
  "prompt": "Your text prompt (REQUIRED)",
  
  // Image Quality & Size
  "aspect_ratio": "16:9",           // Options: "1:1", "16:9", "9:16", "3:4", "4:3" (default: "1:1")
  "megapixels": "1",                // Options: "1", "0.25" (default: "1")
  "output_format": "webp",          // Options: "webp", "jpg", "png" (default: "webp") 
  "output_quality": 80,             // Range: 0-100 (default: 80)
  
  // Generation Control
  "seed": 42,                       // Integer for reproducible results (default: null/random)
  "guidance": 3.0,                  // Range: 0-10, higher = more prompt adherence (default: 3)
  "num_inference_steps": 28,        // Range: 1-50, more steps = better quality (default: 28)
  "prompt_strength": 0.8,           // Range: 0-1, prompt influence strength (default: 0.8)
  
  // Performance & Output
  "go_fast": true,                  // Boolean, enable fast mode (default: true)
  "num_outputs": 1,                 // Range: 1-4, number of images to generate (default: 1)
  "disable_safety_checker": false,  // Boolean, disable NSFW filter (default: false)
  
  // Custom Output
  "custom_filename": "my_image"     // Custom filename (optional, auto-adds extension)
}
```

### 2. Flux Context Max (`flux-kontext-max`) - Image Editing & Context

**Purpose**: Advanced image editing and context-aware generation using reference images.

**All Available Parameters**:
```json
{
  "model_name": "flux-kontext-max",
  "prompt": "Transform this image... (REQUIRED)",
  
  // Input Image (Required for this model)
  "input_image": "https://example.com/image.jpg",  // URL or file path (REQUIRED)
  
  // Image Dimensions
  "aspect_ratio": "match_input_image",              // Options: "match_input_image", "1:1", "16:9", "9:16", "4:3", "3:4", "21:9", "9:21" (default: "match_input_image")
  "output_format": "png",                           // Options: "jpg", "png" (default: "png")
  
  // Generation Control
  "seed": 42,                                       // Integer for reproducible results (default: null/random)
  "safety_tolerance": 2,                            // Range: 0-6, content safety level (default: 2)
  "prompt_upsampling": false,                       // Boolean, enhance prompt quality (default: false)
  
  // Custom Output
  "custom_filename": "edited_image"                 // Custom filename (optional, auto-adds .png extension)
}
```

### 3. Qwen Image (`qwen-image`) - Chinese-Optimized Generation

**Purpose**: High-quality image generation optimized for Chinese prompts and cultural content.

**All Available Parameters**:
```json
{
  "model_name": "qwen-image",
  "prompt": "Your text prompt (supports Chinese) (REQUIRED)",
  
  // Image Quality & Size  
  "aspect_ratio": "16:9",             // Options: "1:1", "16:9", "9:16", "3:4", "4:3" (default: "16:9")
  "output_format": "webp",            // Options: "webp", "jpg", "png" (default: "webp")
  "output_quality": 80,               // Range: 0-100, JPEG/WebP quality (default: 80)
  "image_size": "optimize_for_quality", // Options: "optimize_for_quality", "optimize_for_speed" (default: "optimize_for_quality")
  
  // Generation Control
  "guidance": 4.0,                    // Range: 0-10, prompt adherence strength (default: 4)
  "num_inference_steps": 50,          // Range: 1-100, more steps = better quality (default: 50)
  "lora_scale": 1.0,                  // Range: 0-2, LoRA model influence (default: 1)
  "enhance_prompt": false,            // Boolean, auto-enhance prompt quality (default: false)
  "negative_prompt": "",              // String, what to avoid in generation (default: empty)
  
  // Performance
  "go_fast": true,                    // Boolean, enable fast mode (default: true)
  
  // Custom Output
  "custom_filename": "qwen_artwork"   // Custom filename (optional, auto-adds .webp extension)
}
```

### Parameter Usage Tips:

1. **Required Parameters**: Only `model_name` and `prompt` are required for all models
2. **File Extensions**: Custom filenames automatically get appropriate extensions if not provided
3. **Performance vs Quality**: Use `go_fast: true` and lower `num_inference_steps` for speed
4. **Reproducibility**: Set `seed` to the same number for identical results
5. **Safety**: Adjust `safety_tolerance` (flux-kontext-max) for content filtering

## 🔧 Advanced Configuration

### Runtime Concurrency Adjustment (Admin Only)
```http
POST /configure
X-Admin-API-Key: your_admin_key

{
  "concurrent_limit": 30,
  "requests_per_minute": 300
}
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  replicate-generation:
    image: betashow/replicate-concurrent-generation:latest
    ports:
      - "5003:5003"
    environment:
      - REPLICATE_API_TOKEN=r8_your_token_here
      - CONCURRENT_DOCKER_ADMIN_API_KEY=your_admin_key
      - FLASK_PORT=5003
    volumes:
      - ./output:/app/output
    restart: unless-stopped
```

## 🏗️ Building from Source

```bash
# Clone repository
git clone <your-repo-url>
cd replicate-concurrent-generation

# Build Docker image
docker build -t your-image-name:latest .

# Run locally for development
pip install -r requirements.txt
export REPLICATE_API_TOKEN="your_token"
export CONCURRENT_DOCKER_ADMIN_API_KEY="your_admin_key"
python app.py
```

## 📊 Error Handling

### Common Error Responses

**Authentication Error (401):**
```json
{
  "error": "No valid API key provided. Either provide X-Admin-API-Key or X-Replicate-API-Key header"
}
```

**Model Not Supported (400):**
```json
{
  "error": "Model 'invalid-model' not supported",
  "supported_models": ["flux-dev", "flux-kontext-max", "qwen-image"]
}
```

**Generation Error (500):**
```json
{
  "error": "Generation failed: <detailed error message>"
}
```

## 📁 File Organization

```
/app/
├── output/           # Generated images directory
├── model_functions.py # Model-specific generation logic
├── concurrency_manager.py # Rate limiting & concurrency control  
├── app.py           # Main Flask application
└── requirements.txt # Python dependencies
```

## 🔒 Security Notes

- Admin keys provide access to server's Replicate token
- User keys allow clients to use their own Replicate accounts
- All sensitive tokens should be passed via environment variables
- Generated files are stored in the container's `/app/output` directory

## 📈 Performance

- **Concurrent Limit**: Default 60 simultaneous requests
- **Rate Limit**: Default 600 requests per minute  
- **Thread Pool**: 50 worker threads for async processing
- **Timeouts**: 5 minutes for single images, 10 minutes for batches

## 🐛 Troubleshooting

### Service won't start
- Check `REPLICATE_API_TOKEN` is valid
- Ensure port 5003 is not in use
- Verify Docker image is latest version

### Generation errors
- Verify model name is exactly: `flux-dev`, `flux-kontext-max`, or `qwen-image`
- Check Replicate API token has sufficient quota
- Ensure input parameters match model requirements

### Permission errors
- Mount output volume with correct permissions
- Ensure admin API key matches configured value

## 🔄 Version History

- **v2.0**: Major rewrite with async architecture, bug fixes, and improved concurrency
- **v1.x**: Initial version with complex model support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Version:** 2.0  
**Docker Hub:** `betashow/replicate-concurrent-generation:latest`  
**Base Image:** `python:3.11-slim`