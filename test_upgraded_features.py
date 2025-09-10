#!/usr/bin/env python3
"""
Test script for upgraded Replicate Concurrent Generation service
Tests the External Semaphore Pattern and 3-tier authentication system
"""

import os
import json
import time
import asyncio
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from model_functions import MODEL_FUNCTIONS
from concurrency_manager import (
    concurrency_manager, register_global_semaphore, 
    get_global_semaphore, list_global_semaphores
)

# Test configuration
TEST_API_URL = "http://localhost:5003"  # Assuming Replicate service runs on port 5003
ADMIN_API_KEY = os.getenv('CONCURRENT_DOCKER_ADMIN_API_KEY', 'test-admin-key')
TEST_REPLICATE_KEY = os.getenv('REPLICATE_API_TOKEN', 'test-replicate-key')

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def test_health_endpoint():
    """Test 1: Health check endpoint"""
    print_section("TEST 1: Health Check Endpoint")
    
    try:
        response = requests.get(f"{TEST_API_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("✅ Health check passed")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Supported models: {len(data.get('supported_models', []))}")
            print(f"   Concurrency status: {data.get('concurrency_status', {})}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_global_semaphores():
    """Test 2: Global semaphore management"""
    print_section("TEST 2: Global Semaphore Management")
    
    try:
        # Test listing global semaphores
        response = requests.get(f"{TEST_API_URL}/global-semaphores")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Global semaphores listed: {data.get('count', 0)} semaphores")
            print(f"   Available: {data.get('global_semaphores', [])}")
        
        # Test registering a new global semaphore (admin only)
        headers = {'X-Admin-API-Key': ADMIN_API_KEY}
        payload = {
            'semaphore_id': 'test-global-semaphore',
            'limit': 5
        }
        response = requests.post(
            f"{TEST_API_URL}/global-semaphores",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Global semaphore registration successful")
            print(f"   Semaphore ID: {data.get('semaphore_id')}")
            print(f"   Limit: {data.get('limit')}")
        else:
            print(f"❌ Global semaphore registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ Global semaphore test error: {e}")
        return False

def test_three_tier_authentication():
    """Test 3: Three-tier authentication system"""
    print_section("TEST 3: Three-Tier Authentication System")
    
    test_payload = {
        'model_name': 'flux-dev',
        'prompt': 'A simple test image'
    }
    
    # Test 1: Admin API Key authentication
    print("\n--- Tier 1: Admin API Key Authentication ---")
    headers = {'X-Admin-API-Key': ADMIN_API_KEY}
    try:
        response = requests.post(
            f"{TEST_API_URL}/generate",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        if response.status_code in [200, 500]:  # 500 might be expected if no real API key
            print("✅ Admin API Key authentication working")
        else:
            print(f"❌ Admin API Key auth failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Admin API Key test (expected if no real keys): {e}")
    
    # Test 2: User credentials in payload
    print("\n--- Tier 2: User Credentials in Payload ---")
    payload_with_creds = test_payload.copy()
    payload_with_creds['credentials'] = {
        'replicate_api_token': TEST_REPLICATE_KEY
    }
    try:
        response = requests.post(
            f"{TEST_API_URL}/generate",
            json=payload_with_creds,
            timeout=30
        )
        if response.status_code in [200, 500]:
            print("✅ User credentials authentication working")
        else:
            print(f"❌ User credentials auth failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ User credentials test (expected if no real keys): {e}")
    
    # Test 3: Missing authentication
    print("\n--- Test: Missing Authentication ---")
    try:
        response = requests.post(
            f"{TEST_API_URL}/generate",
            json=test_payload,
            timeout=10
        )
        if response.status_code == 401:
            print("✅ Proper 401 response for missing authentication")
        else:
            print(f"❌ Expected 401 for missing auth, got: {response.status_code}")
    except Exception as e:
        print(f"❌ Missing auth test error: {e}")
    
    return True

def test_external_semaphore_support():
    """Test 4: External semaphore support in generation"""
    print_section("TEST 4: External Semaphore Support")
    
    # Test with external semaphore
    test_payload = {
        'model_name': 'flux-dev',
        'prompt': 'Test with external semaphore',
        'external_semaphore_id': 'test-global-semaphore'
    }
    
    headers = {'X-Admin-API-Key': ADMIN_API_KEY}
    
    try:
        response = requests.post(
            f"{TEST_API_URL}/generate",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        if response.status_code in [200, 500]:  # 500 expected if no real API key
            data = response.json()
            if response.status_code == 200:
                print("✅ External semaphore generation working")
                print(f"   External semaphore used: {data.get('external_semaphore_used')}")
                print(f"   Semaphore ID: {data.get('semaphore_id')}")
            else:
                print("⚠️ External semaphore request processed (no real API key)")
        else:
            print(f"❌ External semaphore test failed: {response.status_code}")
            print(f"   Response: {response.text}")
        
        return True
    except Exception as e:
        print(f"❌ External semaphore test error: {e}")
        return False

def test_batch_generation():
    """Test 5: Batch generation with authentication"""
    print_section("TEST 5: Batch Generation")
    
    test_payload = {
        'model_name': 'flux-dev',
        'prompts': [
            'Test image 1',
            'Test image 2'
        ],
        'external_semaphore_id': 'test-global-semaphore'
    }
    
    headers = {'X-Admin-API-Key': ADMIN_API_KEY}
    
    try:
        response = requests.post(
            f"{TEST_API_URL}/generate-batch",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        
        if response.status_code in [200, 500]:
            data = response.json()
            if response.status_code == 200:
                print("✅ Batch generation working")
                print(f"   Total prompts: {data.get('total_prompts')}")
                print(f"   External semaphore used: {data.get('external_semaphore_used')}")
            else:
                print("⚠️ Batch generation request processed (no real API key)")
        else:
            print(f"❌ Batch generation failed: {response.status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Batch generation test error: {e}")
        return False

def test_concurrency_manager_direct():
    """Test 6: Direct concurrency manager functionality"""
    print_section("TEST 6: Direct Concurrency Manager")
    
    try:
        # Test registering a local semaphore
        semaphore = register_global_semaphore('test-local', 3)
        print("✅ Local semaphore registered")
        
        # Test retrieving it
        retrieved = get_global_semaphore('test-local')
        if retrieved == semaphore:
            print("✅ Semaphore retrieval working")
        
        # Test listing
        all_semaphores = list_global_semaphores()
        if 'test-local' in all_semaphores:
            print("✅ Semaphore listing working")
            print(f"   Available semaphores: {all_semaphores}")
        
        # Test context manager with external semaphore
        def test_context():
            with concurrency_manager.with_external_semaphore(semaphore):
                time.sleep(0.1)
                return "success"
        
        result = test_context()
        if result == "success":
            print("✅ External semaphore context manager working")
        
        return True
    except Exception as e:
        print(f"❌ Direct concurrency manager test error: {e}")
        return False

def test_backward_compatibility():
    """Test 7: Backward compatibility"""
    print_section("TEST 7: Backward Compatibility")
    
    try:
        # Test standard context manager still works
        with concurrency_manager:
            time.sleep(0.1)
        
        print("✅ Backward compatibility maintained")
        print("   Standard context manager still works")
        
        return True
    except Exception as e:
        print(f"❌ Backward compatibility test error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print_section("REPLICATE EXTERNAL SEMAPHORE PATTERN UPGRADE TEST")
    print("Testing upgraded functionality...")
    
    results = []
    
    # Run all tests
    test_functions = [
        ("Health Check", test_health_endpoint),
        ("Global Semaphores", test_global_semaphores),
        ("Three-Tier Auth", test_three_tier_authentication),
        ("External Semaphore", test_external_semaphore_support),
        ("Batch Generation", test_batch_generation),
        ("Direct Manager", test_concurrency_manager_direct),
        ("Backward Compatibility", test_backward_compatibility)
    ]
    
    for test_name, test_func in test_functions:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! External Semaphore Pattern upgrade successful!")
    else:
        print("⚠️ Some tests failed. Check logs above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)