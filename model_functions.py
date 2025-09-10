"""
Simple async model functions for Replicate API
Extracted from the original replicate_batch_process project
Only supports flux-dev, flux-kontext-max, and qwen models
"""

import os
import replicate
import requests
from typing import Dict, Any, List, Optional


# Model configurations extracted from the original config
MODELS_CONFIG = {
    'black-forest-labs/flux-dev': {
        'supported_params': {
            'seed': {'type': 'int', 'default': None},
            'go_fast': {'type': 'bool', 'default': True},
            'guidance': {'type': 'float', 'default': 3, 'range': [0, 10]},
            'megapixels': {'type': 'select', 'default': '1', 'options': ['1', '0.25']},
            'num_outputs': {'type': 'int', 'default': 1, 'range': [1, 4]},
            'aspect_ratio': {'type': 'select', 'default': '1:1', 'options': ['1:1', '16:9', '9:16', '3:4', '4:3']},
            'output_format': {'type': 'select', 'default': 'webp', 'options': ['webp', 'jpg', 'png']},
            'output_quality': {'type': 'int', 'default': 80, 'range': [0, 100]},
            'prompt_strength': {'type': 'float', 'default': 0.8, 'range': [0, 1]},
            'num_inference_steps': {'type': 'int', 'default': 28, 'range': [1, 50]},
            'disable_safety_checker': {'type': 'bool', 'default': False}
        }
    },
    'black-forest-labs/flux-kontext-max': {
        'supported_params': {
            'input_image': {'type': 'file', 'default': None},
            'aspect_ratio': {'type': 'select', 'default': 'match_input_image', 'options': ['match_input_image', '1:1', '16:9', '9:16', '4:3', '3:4', '21:9', '9:21']},
            'output_format': {'type': 'select', 'default': 'png', 'options': ['jpg', 'png']},
            'seed': {'type': 'int', 'default': None},
            'safety_tolerance': {'type': 'int', 'default': 2, 'range': [0, 6]},
            'prompt_upsampling': {'type': 'bool', 'default': False}
        }
    },
    'qwen/qwen-image': {
        'supported_params': {
            'go_fast': {'type': 'bool', 'default': True},
            'guidance': {'type': 'float', 'default': 4, 'range': [0, 10]},
            'image_size': {'type': 'select', 'default': 'optimize_for_quality', 'options': ['optimize_for_quality', 'optimize_for_speed']},
            'lora_scale': {'type': 'float', 'default': 1, 'range': [0, 2]},
            'aspect_ratio': {'type': 'select', 'default': '16:9', 'options': ['1:1', '16:9', '9:16', '3:4', '4:3']},
            'output_format': {'type': 'select', 'default': 'webp', 'options': ['webp', 'jpg', 'png']},
            'enhance_prompt': {'type': 'bool', 'default': False},
            'output_quality': {'type': 'int', 'default': 80, 'range': [0, 100]},
            'negative_prompt': {'type': 'str', 'default': ''},
            'num_inference_steps': {'type': 'int', 'default': 50, 'range': [1, 100]}
        }
    }
}


def validate_and_filter_params(model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and filter parameters for a specific model"""
    if model_name not in MODELS_CONFIG:
        raise ValueError(f"Model {model_name} not supported")
    
    supported_params = MODELS_CONFIG[model_name]['supported_params']
    filtered_params = {'prompt': params.get('prompt')}  # Always include prompt
    
    for param_name, param_config in supported_params.items():
        if param_name in params and params[param_name] is not None:
            # Handle file parameters
            if param_config.get('type') == 'file':
                file_input = params[param_name]
                if isinstance(file_input, str):
                    if file_input.startswith(('http://', 'https://')):
                        filtered_params[param_name] = file_input
                    else:
                        # Local file - open for reading
                        try:
                            filtered_params[param_name] = open(file_input, 'rb')
                        except FileNotFoundError:
                            print(f"Warning: File not found: {file_input}, skipping parameter {param_name}")
                            continue
                else:
                    filtered_params[param_name] = file_input
            else:
                filtered_params[param_name] = params[param_name]
        elif param_config.get('default') is not None:
            filtered_params[param_name] = param_config['default']
    
    return filtered_params


def download_file_from_url(url: str, output_path: str) -> str:
    """Download a file from URL"""
    response = requests.get(url)
    response.raise_for_status()
    with open(output_path, 'wb') as f:
        f.write(response.content)
    return output_path


def flux_dev_generate(prompt: str, api_key: Optional[str] = None, **kwargs) -> List[str]:
    """
    Generate images using black-forest-labs/flux-dev model
    
    Args:
        prompt: Text prompt for image generation
        api_key: Replicate API token (optional, uses env if not provided)
        **kwargs: Additional parameters for the model
    
    Returns:
        List of image URLs (no longer downloads files)
    """
    # Set API key
    if api_key:
        os.environ["REPLICATE_API_TOKEN"] = api_key
    elif not os.getenv("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN must be provided either as parameter or environment variable")
    
    model_name = 'black-forest-labs/flux-dev'
    
    # Prepare parameters
    params = {'prompt': prompt, **kwargs}
    filtered_params = validate_and_filter_params(model_name, params)
    
    # Run the model
    output = replicate.run(model_name, input=filtered_params)
    
    # Return URLs directly instead of downloading files
    if isinstance(output, list):
        return [str(item) for item in output]
    else:
        return [str(output)]


def flux_kontext_max_generate(prompt: str, api_key: Optional[str] = None, **kwargs) -> List[str]:
    """
    Generate images using black-forest-labs/flux-kontext-max model
    
    Args:
        prompt: Text prompt for image generation
        api_key: Replicate API token (optional, uses env if not provided)
        **kwargs: Additional parameters for the model (supports input_image for editing)
    
    Returns:
        List of image URLs (no longer downloads files)
    """
    # Set API key
    if api_key:
        os.environ["REPLICATE_API_TOKEN"] = api_key
    elif not os.getenv("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN must be provided either as parameter or environment variable")
    
    model_name = 'black-forest-labs/flux-kontext-max'
    
    # Prepare parameters
    params = {'prompt': prompt, **kwargs}
    filtered_params = validate_and_filter_params(model_name, params)
    
    # Run the model
    output = replicate.run(model_name, input=filtered_params)
    
    # Return URLs directly instead of downloading files
    if isinstance(output, list):
        return [str(item) for item in output]
    else:
        return [str(output)]


def qwen_image_generate(prompt: str, api_key: Optional[str] = None, **kwargs) -> List[str]:
    """
    Generate images using qwen/qwen-image model
    
    Args:
        prompt: Text prompt for image generation
        api_key: Replicate API token (optional, uses env if not provided)
        **kwargs: Additional parameters for the model
    
    Returns:
        List of image URLs (no longer downloads files)
    """
    # Set API key
    if api_key:
        os.environ["REPLICATE_API_TOKEN"] = api_key
    elif not os.getenv("REPLICATE_API_TOKEN"):
        raise ValueError("REPLICATE_API_TOKEN must be provided either as parameter or environment variable")
    
    model_name = 'qwen/qwen-image'
    
    # Prepare parameters
    params = {'prompt': prompt, **kwargs}
    filtered_params = validate_and_filter_params(model_name, params)
    
    # Run the model
    output = replicate.run(model_name, input=filtered_params)
    
    # Return URLs directly instead of downloading files
    if isinstance(output, list):
        return [str(item) for item in output]
    else:
        return [str(output)]


# Model registry for easy access
MODEL_FUNCTIONS = {
    'flux-dev': flux_dev_generate,
    'flux-kontext-max': flux_kontext_max_generate,
    'qwen-image': qwen_image_generate,
    # Also allow full model names
    'black-forest-labs/flux-dev': flux_dev_generate,
    'black-forest-labs/flux-kontext-max': flux_kontext_max_generate,
    'qwen/qwen-image': qwen_image_generate,
}


def generate_image(model_name: str, prompt: str, api_key: Optional[str] = None, **kwargs) -> List[str]:
    """
    Generic function to generate images with any of the supported models
    
    Args:
        model_name: Name of the model ('flux-dev', 'flux-kontext-max', 'qwen-image')
        prompt: Text prompt for image generation
        api_key: Replicate API token (optional, uses env if not provided)
        **kwargs: Additional parameters for the model
    
    Returns:
        List of saved file paths
    """
    if model_name not in MODEL_FUNCTIONS:
        raise ValueError(f"Model '{model_name}' not supported. Available models: {list(MODEL_FUNCTIONS.keys())}")
    
    model_function = MODEL_FUNCTIONS[model_name]
    return model_function(prompt, api_key, **kwargs)