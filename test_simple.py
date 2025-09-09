"""
Simple test script for the new Replicate concurrent generation service
"""

import asyncio
import time
from model_functions import generate_image, MODEL_FUNCTIONS
from concurrency_manager import concurrency_manager, get_concurrency_status


async def test_single_generation():
    """Test single image generation"""
    print("🧪 Testing single image generation...")
    
    try:
        start_time = time.time()
        files = await generate_image(
            'flux-dev',
            'A beautiful sunset over mountains',
            output_dir='test_output',
            aspect_ratio='16:9',
            output_quality=80
        )
        end_time = time.time()
        
        print(f"✅ Single generation completed in {end_time - start_time:.2f}s")
        print(f"   Files generated: {files}")
        
    except Exception as e:
        print(f"❌ Single generation failed: {e}")


async def test_concurrent_generation():
    """Test concurrent image generation"""
    print("\n🧪 Testing concurrent image generation...")
    
    try:
        prompts = [
            "A cat sitting on a red chair",
            "A dog running in a green park", 
            "A bird flying in a blue sky"
        ]
        
        start_time = time.time()
        
        # Run all generations concurrently
        tasks = []
        for i, prompt in enumerate(prompts):
            task = generate_image(
                'qwen-image',
                prompt,
                output_dir=f'test_output/concurrent_{i+1}',
                aspect_ratio='1:1'
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        
        print(f"✅ Concurrent generation completed in {end_time - start_time:.2f}s")
        print(f"   Successful: {successful}/{len(prompts)}")
        print(f"   Failed: {failed}/{len(prompts)}")
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"   Task {i+1}: ❌ {result}")
            else:
                print(f"   Task {i+1}: ✅ {result}")
                
    except Exception as e:
        print(f"❌ Concurrent generation failed: {e}")


async def test_model_functions():
    """Test individual model functions"""
    print("\n🧪 Testing individual model functions...")
    
    models_to_test = [
        ('flux-dev', 'A simple geometric shape'),
        ('qwen-image', 'A colorful abstract pattern'),
        # Skip flux-kontext-max as it requires reference image
    ]
    
    for model_name, prompt in models_to_test:
        try:
            print(f"   Testing {model_name}...")
            start_time = time.time()
            
            files = await generate_image(
                model_name,
                prompt,
                output_dir=f'test_output/{model_name.replace("/", "_")}',
                aspect_ratio='1:1'
            )
            
            end_time = time.time()
            print(f"   ✅ {model_name}: {end_time - start_time:.2f}s, files: {files}")
            
        except Exception as e:
            print(f"   ❌ {model_name}: {e}")


async def test_concurrency_limits():
    """Test concurrency limiting"""
    print("\n🧪 Testing concurrency limits...")
    
    try:
        # Configure lower limits for testing
        concurrency_manager.configure(concurrent_limit=2, requests_per_minute=10)
        
        # Create 5 tasks (more than concurrent limit)
        prompts = [f"Test image {i+1}" for i in range(5)]
        
        start_time = time.time()
        
        tasks = []
        for i, prompt in enumerate(prompts):
            task = generate_image(
                'flux-dev',
                prompt,
                output_dir=f'test_output/limit_test_{i+1}',
                go_fast=True,
                num_inference_steps=10  # Faster for testing
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        print(f"✅ Concurrency limit test completed in {end_time - start_time:.2f}s")
        print(f"   Total tasks: {len(prompts)}")
        print(f"   Concurrent limit was: 2")
        print(f"   Expected behavior: Tasks queued and processed in batches of 2")
        
    except Exception as e:
        print(f"❌ Concurrency limit test failed: {e}")


async def main():
    """Run all tests"""
    print("🚀 Starting Replicate Concurrent Generation Tests")
    print(f"   Supported models: {list(MODEL_FUNCTIONS.keys())}")
    
    status = get_concurrency_status()
    print(f"   Initial concurrency status: {status}")
    
    # Run tests
    await test_single_generation()
    await test_model_functions()
    await test_concurrent_generation()
    await test_concurrency_limits()
    
    final_status = get_concurrency_status()
    print(f"\n📊 Final concurrency status: {final_status}")
    print("🏁 All tests completed!")


if __name__ == '__main__':
    # Make sure we have API key
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not os.getenv('REPLICATE_API_TOKEN'):
        print("❌ REPLICATE_API_TOKEN not found in environment")
        print("   Please set it in .env file or environment variables")
        exit(1)
    
    # Run tests
    asyncio.run(main())