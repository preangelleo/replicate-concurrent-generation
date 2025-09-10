#!/usr/bin/env python3
"""
Test actual generation with new URL return format
"""

import json
from app import app

def test_actual_generation():
    """Test actual generation and inspect the new response format"""
    print("=== Testing Actual Generation with URL Return ===")
    
    with app.test_client() as client:
        # Test single generation
        print("\n--- Single Generation Test ---")
        response = client.post('/generate', json={
            'model_name': 'flux-dev',
            'prompt': 'A beautiful sunset over mountains',
            'output_filename': 'sunset_mountains'
        })
        
        if response.status_code == 200:
            data = response.get_json()
            print("✅ Single generation successful!")
            print("Response structure:")
            print(f"   Success: {data.get('success')}")
            print(f"   Model: {data.get('model_name')}")
            print(f"   Prompt: {data.get('prompt')}")
            print(f"   Output filename: {data.get('output_filename')}")
            print(f"   Generated files count: {data.get('count')}")
            print("   Generated files:")
            for i, file_info in enumerate(data.get('generated_files', [])):
                print(f"     {i+1}. URL: {file_info.get('url')}")
                print(f"        Filename: {file_info.get('filename')}")
        else:
            print(f"❌ Single generation failed: {response.status_code}")
            print(f"   Error: {response.get_json()}")
        
        # Test batch generation
        print("\n--- Batch Generation Test ---")
        response = client.post('/generate-batch', json={
            'model_name': 'flux-dev',
            'tasks': [
                {'prompt': 'A red car', 'output_filename': 'red_car.jpg'},
                {'prompt': 'A blue house', 'output_filename': 'blue_house'}
            ]
        })
        
        if response.status_code == 200:
            data = response.get_json()
            print("✅ Batch generation successful!")
            print("Response structure:")
            print(f"   Success: {data.get('success')}")
            print(f"   Total tasks: {data.get('total_tasks')}")
            print(f"   Successful: {data.get('successful_count')}")
            print(f"   Failed: {data.get('failed_count')}")
            print("   Successful results:")
            for result in data.get('successful_results', []):
                print(f"     Task {result.get('task_index')}: {result.get('prompt')}")
                print(f"       Output filename: {result.get('output_filename')}")
                print(f"       Generated files:")
                for file_info in result.get('generated_files', []):
                    print(f"         - URL: {file_info.get('url')}")
                    print(f"           Filename: {file_info.get('filename')}")
        else:
            print(f"❌ Batch generation failed: {response.status_code}")
            print(f"   Error: {response.get_json()}")

if __name__ == "__main__":
    test_actual_generation()
    print("\n🎉 Actual generation tests completed!")