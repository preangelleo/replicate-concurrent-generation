"""
Simple Flask API for Replicate concurrent image generation
Supports only flux-dev, flux-kontext-max, and qwen-image models
"""

import os
import shutil
import threading
import time
from flask import Flask, request, jsonify
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from model_functions import generate_image, MODEL_FUNCTIONS
from concurrency_manager import (
    concurrency_manager, get_concurrency_status, with_concurrency_control,
    register_global_semaphore, get_global_semaphore, list_global_semaphores,
    run_with_external_semaphore
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Admin API key for internal use
ADMIN_API_KEY = os.getenv('CONCURRENT_DOCKER_ADMIN_API_KEY')
DEFAULT_REPLICATE_API_KEY = os.getenv('REPLICATE_API_TOKEN')


def get_credentials_from_request(headers, request_data=None):
    """Enhanced 3-tier authentication system (similar to Volcengine TTS)
    
    Priority:
    1. Admin API Key (header) -> Use server's credentials
    2. User credentials (request payload) -> Use user's credentials  
    3. Environment variables -> Use server's credentials (fallback)
    
    Returns:
        tuple: (api_key, external_semaphore_id, concurrency_limit)
    """
    # Extract credentials from request payload if provided
    credentials = None
    external_semaphore_id = None
    custom_concurrency = None
    
    if request_data:
        credentials = request_data.get('credentials', {})
        external_semaphore_id = request_data.get('external_semaphore_id')
        custom_concurrency = request_data.get('concurrency_limit')
    
    # Tier 1: Admin API Key in Header -> Uses Server's Credentials
    admin_key = headers.get('X-Admin-API-Key')
    if admin_key == ADMIN_API_KEY:
        if DEFAULT_REPLICATE_API_KEY:
            return DEFAULT_REPLICATE_API_KEY, external_semaphore_id, custom_concurrency
        else:
            raise ValueError("Admin API key recognized but no default Replicate token configured")
    
    # Tier 2: User-provided credentials in request payload
    if credentials and credentials.get('replicate_api_token'):
        user_api_key = credentials['replicate_api_token']
        # User can also specify their own concurrency limit
        user_concurrency = credentials.get('concurrency_limit', custom_concurrency)
        return user_api_key, external_semaphore_id, user_concurrency
    
    # Tier 2 Alternative: User-provided key in header
    replicate_key = headers.get('X-Replicate-API-Key')
    if replicate_key:
        return replicate_key, external_semaphore_id, custom_concurrency
    
    # Tier 3: Environment Variables (fallback)
    if DEFAULT_REPLICATE_API_KEY:
        return DEFAULT_REPLICATE_API_KEY, external_semaphore_id, custom_concurrency
    
    # No valid authentication found
    raise ValueError(
        "No valid API key provided. Use one of:\n"
        "1. X-Admin-API-Key header (for trusted services)\n"
        "2. X-Replicate-API-Key header (user's key)\n"
        "3. credentials.replicate_api_token in request payload\n"
        "4. Configure REPLICATE_API_TOKEN environment variable"
    )


def cleanup_files_delayed(file_paths, delay_minutes=30):
    """Schedule files for delayed cleanup to give users time to download
    
    Args:
        file_paths: List of file paths to delete
        delay_minutes: Minutes to wait before cleanup (default: 30 minutes)
    """
    if not file_paths:
        return
    
    def delayed_cleanup():
        time.sleep(delay_minutes * 60)  # Convert to seconds
        
        directories_to_cleanup = set()
        cleaned_count = 0
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_count += 1
                    # Add parent directory for cleanup if it becomes empty
                    parent_dir = os.path.dirname(file_path)
                    if parent_dir and parent_dir != '.':
                        directories_to_cleanup.add(parent_dir)
            except Exception as e:
                logger.warning(f"Failed to delete file {file_path}: {e}")
        
        # Clean up empty directories
        for directory in directories_to_cleanup:
            try:
                if os.path.exists(directory) and not os.listdir(directory):
                    os.rmdir(directory)
            except Exception as e:
                logger.warning(f"Failed to remove directory {directory}: {e}")
        
        logger.info(f"🧹 Delayed cleanup completed: {cleaned_count} files removed after {delay_minutes} minutes")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info(f"📅 Scheduled cleanup for {len(file_paths)} files in {delay_minutes} minutes")


def cleanup_files_immediate():
    """Immediate cleanup for emergency situations (not recommended for normal use)"""
    logger.warning("⚠️ Immediate cleanup disabled for user safety - use delayed cleanup instead")


def run_generation_with_concurrency(model_name: str, prompt: str, api_key: str, 
                                   external_semaphore_id=None, **kwargs):
    """Run image generation with concurrency control (supports external semaphore)
    
    Args:
        model_name: Name of the model to use
        prompt: Text prompt for generation
        api_key: Replicate API key
        external_semaphore_id: Optional global semaphore ID for cross-service control
        **kwargs: Additional model parameters
    """
    if external_semaphore_id:
        # Use external semaphore for global concurrency control
        global_semaphore = get_global_semaphore(external_semaphore_id)
        if not global_semaphore:
            raise ValueError(f"Global semaphore '{external_semaphore_id}' not found. Available: {list_global_semaphores()}")
        
        with concurrency_manager.with_external_semaphore(global_semaphore):
            return generate_image(model_name, prompt, api_key, **kwargs)
    else:
        # Use internal concurrency control
        with concurrency_manager:
            return generate_image(model_name, prompt, api_key, **kwargs)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    status = get_concurrency_status()
    return jsonify({
        'status': 'healthy',
        'service': 'replicate-concurrent-generation',
        'version': '3.0-volcengine-enhanced (External Semaphore Pattern + URL-Direct-Return)',
        'supported_models': list(MODEL_FUNCTIONS.keys()),
        'concurrency_status': status
    })


@app.route('/generate', methods=['POST'])
def generate():
    """Generate image with a single model (Enhanced with 3-tier auth and external semaphore support)"""
    try:
        # Parse request data first
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Enhanced 3-tier authentication
        try:
            api_key, external_semaphore_id, custom_concurrency = get_credentials_from_request(
                request.headers, data
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
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
        
        # Extract other parameters (excluding auth and control fields)
        exclude_fields = ['model_name', 'prompt', 'credentials', 'external_semaphore_id', 'concurrency_limit']
        kwargs = {k: v for k, v in data.items() if k not in exclude_fields}
        
        # Run generation with enhanced concurrency control
        result_urls = run_generation_with_concurrency(
            model_name, prompt, api_key, 
            external_semaphore_id=external_semaphore_id,
            **kwargs
        )
        
        # Process results to include filename mapping
        output_filename = data.get('output_filename', 'generated_image')
        files_with_names = []
        
        if isinstance(result_urls, list):
            for j, url in enumerate(result_urls):
                # Generate filename with index if multiple outputs
                if len(result_urls) > 1:
                    base_filename = output_filename.rsplit('.', 1)[0] if '.' in output_filename else output_filename
                    ext = output_filename.rsplit('.', 1)[1] if '.' in output_filename else 'jpg'
                    filename = f"{base_filename}_{j+1}.{ext}"
                else:
                    filename = output_filename if '.' in output_filename else f"{output_filename}.jpg"
                
                files_with_names.append({
                    'url': str(url),
                    'filename': filename
                })
        else:
            # Single URL result
            filename = output_filename if '.' in output_filename else f"{output_filename}.jpg"
            files_with_names.append({
                'url': str(result_urls),
                'filename': filename
            })
        
        # Prepare response
        response_data = {
            'success': True,
            'model_name': model_name,
            'prompt': prompt,
            'output_filename': output_filename,
            'generated_files': files_with_names,
            'count': len(files_with_names),
            'external_semaphore_used': external_semaphore_id is not None,
            'semaphore_id': external_semaphore_id
        }
        
        # Note: Since we're returning URLs directly, no local files to cleanup
        logger.info(f"✅ Successfully generated {len(files_with_names)} images and returned URLs")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/generate-batch', methods=['POST'])
def generate_batch():
    """Generate images with batch processing (Enhanced with 3-tier auth and external semaphore support)"""
    try:
        # Parse request data first
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Enhanced 3-tier authentication
        try:
            api_key, external_semaphore_id, custom_concurrency = get_credentials_from_request(
                request.headers, data
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        
        # Validate required fields
        tasks = data.get('tasks', [])
        prompts = data.get('prompts', [])  # Backward compatibility
        model_name = data.get('model_name')
        
        # Support both new format (tasks) and legacy format (prompts + custom_filenames)
        if tasks:
            # New format: list of dictionaries
            if not isinstance(tasks, list):
                return jsonify({'error': 'tasks must be an array'}), 400
            
            # Validate each task
            for i, task in enumerate(tasks):
                if not isinstance(task, dict):
                    return jsonify({'error': f'Task {i} must be a dictionary'}), 400
                if 'prompt' not in task:
                    return jsonify({'error': f'Task {i} missing required field: prompt'}), 400
            
            task_list = tasks
        elif prompts:
            # Legacy format: separate arrays
            if not isinstance(prompts, list):
                return jsonify({'error': 'prompts must be an array'}), 400
            
            custom_filenames = data.get('custom_filenames', [])
            if custom_filenames:
                if not isinstance(custom_filenames, list):
                    return jsonify({'error': 'custom_filenames must be an array'}), 400
                if len(custom_filenames) != len(prompts):
                    return jsonify({'error': 'custom_filenames length must match prompts length'}), 400
            
            # Convert to new format
            task_list = []
            for i, prompt in enumerate(prompts):
                task = {'prompt': prompt}
                if custom_filenames and i < len(custom_filenames):
                    task['output_filename'] = custom_filenames[i]
                task_list.append(task)
        else:
            return jsonify({'error': 'Either tasks array or prompts array is required'}), 400
        
        if not model_name:
            return jsonify({'error': 'model_name is required'}), 400
        
        if model_name not in MODEL_FUNCTIONS:
            return jsonify({
                'error': f'Model {model_name} not supported',
                'supported_models': list(MODEL_FUNCTIONS.keys())
            }), 400
        
        # Extract other parameters (excluding auth and control fields)
        exclude_fields = ['tasks', 'prompts', 'model_name', 'custom_filenames', 'credentials', 'external_semaphore_id', 'concurrency_limit']
        global_kwargs = {k: v for k, v in data.items() if k not in exclude_fields}
        
        # Process all tasks sequentially with enhanced concurrency control
        results = []
        
        for i, task in enumerate(task_list):
            try:
                # Extract task-specific parameters
                prompt = task['prompt']
                task_kwargs = global_kwargs.copy()
                
                # Merge task-specific parameters (they override global ones)
                for key, value in task.items():
                    if key not in ['prompt', 'output_filename']:
                        task_kwargs[key] = value
                
                # Set output directory
                if 'output_dir' not in task_kwargs:
                    task_kwargs['output_dir'] = f'output/batch_{i+1}'
                
                # Set custom filename if provided
                if 'output_filename' in task:
                    task_kwargs['custom_filename'] = task['output_filename']
                
                # Generate images
                result = run_generation_with_concurrency(
                    model_name, prompt, api_key,
                    external_semaphore_id=external_semaphore_id,
                    **task_kwargs
                )
                
                results.append(result)
            except Exception as e:
                results.append(e)
        
        # Process results - Return list of dictionaries to match input format
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            task = task_list[i]
            task_prompt = task['prompt']
            task_filename = task.get('output_filename', f'generated_image_{i+1}')
            
            if isinstance(result, Exception):
                failed_results.append({
                    'task_index': i,
                    'prompt': task_prompt,
                    'output_filename': task_filename,
                    'error': str(result)
                })
            else:
                # result is now a list of URLs from model_functions
                # Create list of dictionaries with URL and filename correspondence
                if isinstance(result, list):
                    files_with_names = []
                    for j, url in enumerate(result):
                        # Generate filename with index if multiple outputs
                        if len(result) > 1:
                            base_filename = task_filename.rsplit('.', 1)[0] if '.' in task_filename else task_filename
                            ext = task_filename.rsplit('.', 1)[1] if '.' in task_filename else 'jpg'
                            filename = f"{base_filename}_{j+1}.{ext}"
                        else:
                            filename = task_filename if '.' in task_filename else f"{task_filename}.jpg"
                        
                        files_with_names.append({
                            'url': str(url),
                            'filename': filename
                        })
                    
                    successful_results.append({
                        'task_index': i,
                        'prompt': task_prompt,
                        'output_filename': task_filename,
                        'generated_files': files_with_names,
                        'count': len(files_with_names)
                    })
                else:
                    # Single URL result
                    filename = task_filename if '.' in task_filename else f"{task_filename}.jpg"
                    successful_results.append({
                        'task_index': i,
                        'prompt': task_prompt,
                        'output_filename': task_filename,
                        'generated_files': [{
                            'url': str(result),
                            'filename': filename
                        }],
                        'count': 1
                    })
        
        # Prepare response
        response_data = {
            'success': True,
            'model_name': model_name,
            'total_tasks': len(task_list),
            'successful_count': len(successful_results),
            'failed_count': len(failed_results),
            'successful_results': successful_results,
            'failed_results': failed_results,
            'external_semaphore_used': external_semaphore_id is not None,
            'semaphore_id': external_semaphore_id
        }
        
        # Note: Since we're returning URLs directly, no local files to cleanup  
        logger.info(f"✅ Successfully processed {len(task_list)} batch tasks and returned URLs")
        
        return jsonify(response_data)
        
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


@app.route('/global-semaphores', methods=['GET'])
def list_global_semaphores_endpoint():
    """List all registered global semaphores"""
    return jsonify({
        'global_semaphores': list_global_semaphores(),
        'count': len(list_global_semaphores())
    })


@app.route('/global-semaphores', methods=['POST'])
def register_global_semaphore_endpoint():
    """Register a new global semaphore (admin only)"""
    try:
        # Verify admin API key
        admin_key = request.headers.get('X-Admin-API-Key')
        if admin_key != ADMIN_API_KEY:
            return jsonify({'error': 'Admin API key required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        semaphore_id = data.get('semaphore_id')
        limit = data.get('limit')
        
        if not semaphore_id:
            return jsonify({'error': 'semaphore_id is required'}), 400
        
        if not limit or not isinstance(limit, int) or limit <= 0:
            return jsonify({'error': 'limit must be a positive integer'}), 400
        
        semaphore = register_global_semaphore(semaphore_id, limit)
        
        return jsonify({
            'success': True,
            'message': f'Global semaphore "{semaphore_id}" registered',
            'semaphore_id': semaphore_id,
            'limit': limit,
            'all_semaphores': list_global_semaphores()
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
    
    # Register default global semaphores for cross-service usage
    default_global_semaphore_id = os.getenv('DEFAULT_GLOBAL_SEMAPHORE_ID', 'replicate-global')
    default_global_limit = int(os.getenv('DEFAULT_GLOBAL_SEMAPHORE_LIMIT', concurrent_limit))
    
    if default_global_semaphore_id:
        register_global_semaphore(default_global_semaphore_id, default_global_limit)
        print(f"🌐 Default global semaphore registered: '{default_global_semaphore_id}' (limit: {default_global_limit})")
    
    print(f"🚀 Starting Enhanced Replicate Concurrent Generation Service")
    print(f"   Version: 3.0-volcengine-enhanced (External Semaphore Pattern)")
    print(f"   Supported models: {list(MODEL_FUNCTIONS.keys())}")
    print(f"   Internal concurrency: {concurrent_limit} concurrent, {requests_per_minute} requests/minute")
    print(f"   Global semaphores: {list_global_semaphores()}")
    print(f"   Admin API: {'✅ Configured' if ADMIN_API_KEY else '❌ Not configured'}")
    print(f"   Default Replicate key: {'✅ Configured' if DEFAULT_REPLICATE_API_KEY else '❌ Not configured'}")
    print(f"   3-Tier Authentication: ✅ Enhanced (Admin Key → User Credentials → Environment)")
    print(f"   External Semaphore Support: ✅ Enabled")
    print(f"   Running on: {host}:{port}")
    
    app.run(host=host, port=port, debug=False)