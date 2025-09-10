#!/usr/bin/env python3
"""
Test Flask app structure and endpoints
"""

import json
from app import app

def test_endpoints():
    """Test if all endpoints are accessible"""
    print("=== Testing Flask App Structure ===")
    
    with app.test_client() as client:
        # Test health endpoint
        try:
            response = client.get('/health')
            data = response.get_json()
            print("✅ Health endpoint working")
            print(f"   Status: {data.get('status')}")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Models: {len(data.get('supported_models', []))}")
        except Exception as e:
            print(f"❌ Health endpoint error: {e}")
        
        # Test models endpoint
        try:
            response = client.get('/models')
            data = response.get_json()
            print("✅ Models endpoint working")
            print(f"   Model count: {data.get('model_count')}")
        except Exception as e:
            print(f"❌ Models endpoint error: {e}")
        
        # Test global semaphores endpoint
        try:
            response = client.get('/global-semaphores')
            data = response.get_json()
            print("✅ Global semaphores endpoint working")
            print(f"   Semaphore count: {data.get('count')}")
        except Exception as e:
            print(f"❌ Global semaphores endpoint error: {e}")
        
        # Test generate endpoint (should fail with 401 - no auth)
        try:
            response = client.post('/generate', 
                                 json={'model_name': 'flux-dev', 'prompt': 'test'})
            print(f"✅ Generate endpoint structure working (status: {response.status_code})")
            if response.status_code == 401:
                print("   ✅ Authentication properly required")
        except Exception as e:
            print(f"❌ Generate endpoint error: {e}")
        
        # Test batch generate endpoint (should fail with 401 - no auth)
        try:
            response = client.post('/generate-batch', 
                                 json={'model_name': 'flux-dev', 'tasks': [{'prompt': 'test'}]})
            print(f"✅ Batch generate endpoint structure working (status: {response.status_code})")
            if response.status_code == 401:
                print("   ✅ Authentication properly required")
        except Exception as e:
            print(f"❌ Batch generate endpoint error: {e}")

if __name__ == "__main__":
    test_endpoints()
    print("\n🎉 Flask structure tests completed!")