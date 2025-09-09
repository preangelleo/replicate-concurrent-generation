"""
Simple Flask API for Replicate concurrent image generation
Supports only flux-dev, flux-kontext-max, and qwen-image models
"""

import os
import asyncio
from flask import Flask, request, jsonify
from concurrent.futures import ThreadPoolExecutor
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from model_functions import generate_image, MODEL_FUNCTIONS
from concurrency_manager import concurrency_manager, get_concurrency_status, with_concurrency_control

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread pool for running async functions
executor = ThreadPoolExecutor(max_workers=50)

# Admin API key for internal use
ADMIN_API_KEY = os.getenv('CONCURRENT_DOCKER_ADMIN_API_KEY')
DEFAULT_REPLICATE_API_KEY = os.getenv('REPLICATE_API_TOKEN')


def verify_api_key(headers):
    """Verify API key from headers and return appropriate Replicate API token"""
    admin_key = headers.get('X-Admin-API-Key')
    replicate_key = headers.get('X-Replicate-API-Key')
    
    if admin_key == ADMIN_API_KEY:
        # Admin user - use default token from environment
        if DEFAULT_REPLICATE_API_KEY:
            return DEFAULT_REPLICATE_API_KEY
        else:
            raise ValueError("Admin API key recognized but no default Replicate token configured")
    
    if replicate_key:
        # User provided their own Replicate API key
        return replicate_key
    
    # No valid authentication
    raise ValueError("No valid API key provided. Either provide X-Admin-API-Key or X-Replicate-API-Key header")


async def run_generation_with_concurrency(model_name: str, prompt: str, api_key: str, **kwargs):
    """Run image generation with concurrency control"""
    async def generate():
        return await generate_image(model_name, prompt, api_key, **kwargs)
    
    return await with_concurrency_control(generate())


def run_async_in_thread(coro):
    """Run async coroutine in a new event loop (for thread execution)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    status = get_concurrency_status()
    return jsonify({
        'status': 'healthy',
        'service': 'replicate-concurrent-generation',
        'version': '2.0-simple',
        'supported_models': list(MODEL_FUNCTIONS.keys()),
        'concurrency_status': status
    })


@app.route('/generate', methods=['POST'])
def generate():
    """Generate image with a single model"""
    try:
        # Verify API key
        try:
            api_key = verify_api_key(request.headers)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        model_name = data.get('model_name')
        prompt = data.get('prompt')
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        
        if model_name not in MODEL_FUNCTIONS:
            return jsonify({
                'error': f'Model {model_name} not supported',
                'supported_models': list(MODEL_FUNCTIONS.keys())
            }), 400
        
        # Extract other parameters
        kwargs = {k: v for k, v in data.items() if k not in ['model_name', 'prompt']}
        
        # Run generation in thread pool
        future = executor.submit(
            run_async_in_thread,
            run_generation_with_concurrency(model_name, prompt, api_key, **kwargs)
        )
        
        # Wait for result
        saved_files = future.result(timeout=300)  # 5 minute timeout
        
        return jsonify({
            'success': True,
            'model_name': model_name,
            'files': saved_files,
            'count': len(saved_files)
        })
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/generate-batch', methods=['POST'])
def generate_batch():
    """Generate images with batch processing"""
    try:
        # Verify API key
        try:
            api_key = verify_api_key(request.headers)
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        prompts = data.get('prompts', [])
        model_name = data.get('model_name')
        
        if not prompts:
            return jsonify({'error': 'prompts array is required'}), 400
        
        if not isinstance(prompts, list):
            return jsonify({'error': 'prompts must be an array'}), 400
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        if model_name not in MODEL_FUNCTIONS:
            return jsonify({
                'error': f'Model {model_name} not supported',
                'supported_models': list(MODEL_FUNCTIONS.keys())
            }), 400
        
        # Extract other parameters
        kwargs = {k: v for k, v in data.items() if k not in ['prompts', 'model_name']}
        
        # Process all prompts
        async def process_batch():
            tasks = []
            for i, prompt in enumerate(prompts):
                # Create unique output directory for each prompt
                prompt_kwargs = kwargs.copy()
                if 'output_dir' not in prompt_kwargs:
                    prompt_kwargs['output_dir'] = f'output/batch_{i+1}'
                
                task = run_generation_with_concurrency(model_name, prompt, api_key, **prompt_kwargs)
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Run batch processing in thread pool
        future = executor.submit(run_async_in_thread, process_batch())
        results = future.result(timeout=600)  # 10 minute timeout for batch
        
        # Process results
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_results.append({
                    'prompt_index': i,
                    'prompt': prompts[i],
                    'error': str(result)
                })
            else:
                successful_results.append({
                    'prompt_index': i,
                    'prompt': prompts[i],
                    'files': result,
                    'count': len(result)
                })
        
        return jsonify({
            'success': True,
            'model_name': model_name,
            'total_prompts': len(prompts),
            'successful_count': len(successful_results),
            'failed_count': len(failed_results),
            'successful_results': successful_results,
            'failed_results': failed_results
        })
        
    except Exception as e:
        logger.error(f"Batch generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/models', methods=['GET'])
def list_models():
    """List all supported models"""
    return jsonify({
        'supported_models': list(MODEL_FUNCTIONS.keys()),
        'model_count': len(MODEL_FUNCTIONS)
    })


@app.route('/status', methods=['GET'])
def status():
    """Get current status and concurrency information"""
    status = get_concurrency_status()
    return jsonify({
        'service': 'replicate-concurrent-generation',
        'version': '2.0-simple',
        'admin_api_configured': bool(ADMIN_API_KEY),
        'default_replicate_key_configured': bool(DEFAULT_REPLICATE_API_KEY),
        'concurrency': status
    })


@app.route('/configure', methods=['POST'])
def configure():
    """Configure concurrency settings (admin only)"""
    try:
        # Verify admin API key
        admin_key = request.headers.get('X-Admin-API-Key')
        if admin_key != ADMIN_API_KEY:
            return jsonify({'error': 'Admin API key required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        concurrent_limit = data.get('concurrent_limit')
        requests_per_minute = data.get('requests_per_minute')
        
        concurrency_manager.configure(concurrent_limit, requests_per_minute)
        
        return jsonify({
            'success': True,
            'message': 'Concurrency settings updated',
            'new_settings': get_concurrency_status()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Configure concurrency from environment
    concurrent_limit = int(os.getenv('REPLICATE_CONCURRENT_LIMIT', 60))
    requests_per_minute = int(os.getenv('REPLICATE_REQUESTS_PER_MINUTE', 600))
    
    # Get port and host from environment
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    concurrency_manager.configure(concurrent_limit, requests_per_minute)
    
    print(f"🚀 Starting Replicate Concurrent Generation Service")
    print(f"   Version: 2.0-simple")
    print(f"   Supported models: {list(MODEL_FUNCTIONS.keys())}")
    print(f"   Concurrency: {concurrent_limit} concurrent, {requests_per_minute} requests/minute")
    print(f"   Admin API: {'✅ Configured' if ADMIN_API_KEY else '❌ Not configured'}")
    print(f"   Default Replicate key: {'✅ Configured' if DEFAULT_REPLICATE_API_KEY else '❌ Not configured'}")
    print(f"   Running on: {host}:{port}")
    
    app.run(host=host, port=port, debug=False)