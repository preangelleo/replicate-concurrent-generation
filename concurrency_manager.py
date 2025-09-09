"""
Simple global concurrency manager for Replicate API
Implements rate limiting based on requests per minute
"""

import asyncio
import time
from typing import Optional
from datetime import datetime, timedelta


class SimpleConcurrencyManager:
    """Simple singleton concurrency manager with rate limiting"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # Rate limiting settings
            self.max_requests_per_minute = 600  # Default Replicate limit
            self.semaphore = None
            self.concurrent_limit = 60  # Max concurrent requests
            
            # Request tracking for rate limiting
            self.request_times = []
            self.lock = asyncio.Lock()
            
            # Initialize semaphore
            self._initialize_semaphore()
            
            SimpleConcurrencyManager._initialized = True
    
    def _initialize_semaphore(self):
        """Initialize the global semaphore"""
        self.semaphore = asyncio.Semaphore(self.concurrent_limit)
        print(f"🚦 Global concurrency manager initialized: {self.concurrent_limit} concurrent, {self.max_requests_per_minute} requests/minute")
    
    def configure(self, concurrent_limit: Optional[int] = None, requests_per_minute: Optional[int] = None):
        """Configure the concurrency settings"""
        if concurrent_limit is not None:
            self.concurrent_limit = concurrent_limit
            self.semaphore = asyncio.Semaphore(concurrent_limit)
        
        if requests_per_minute is not None:
            self.max_requests_per_minute = requests_per_minute
        
        print(f"🔧 Concurrency settings updated: {self.concurrent_limit} concurrent, {self.max_requests_per_minute} requests/minute")
    
    async def _check_rate_limit(self):
        """Check if we're within rate limits and wait if necessary"""
        async with self.lock:
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            
            # Remove old request times
            self.request_times = [req_time for req_time in self.request_times if req_time > one_minute_ago]
            
            # Check if we're at the rate limit
            if len(self.request_times) >= self.max_requests_per_minute:
                # Calculate wait time until we can make another request
                oldest_request = min(self.request_times)
                wait_time = 60 - (now - oldest_request).total_seconds()
                
                if wait_time > 0:
                    print(f"⏳ Rate limit reached ({self.max_requests_per_minute}/min). Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    return await self._check_rate_limit()  # Recheck after waiting
            
            # Record this request
            self.request_times.append(now)
    
    async def acquire(self):
        """Acquire permission to make a request (handles both concurrency and rate limiting)"""
        # Wait for rate limit
        await self._check_rate_limit()
        
        # Acquire semaphore for concurrency control
        await self.semaphore.acquire()
        
        print(f"🟢 Request acquired (concurrent: {self.concurrent_limit - self.semaphore._value}/{self.concurrent_limit}, rate: {len(self.request_times)}/{self.max_requests_per_minute}/min)")
    
    def release(self):
        """Release the semaphore"""
        self.semaphore.release()
        print(f"🔴 Request released (concurrent: {self.concurrent_limit - self.semaphore._value}/{self.concurrent_limit})")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()


# Global instance
concurrency_manager = SimpleConcurrencyManager()


async def with_concurrency_control(coro):
    """Decorator to run async function with concurrency control"""
    async with concurrency_manager:
        return await coro


def get_concurrency_status():
    """Get current concurrency status"""
    manager = concurrency_manager
    return {
        'concurrent_limit': manager.concurrent_limit,
        'requests_per_minute_limit': manager.max_requests_per_minute,
        'current_concurrent': manager.concurrent_limit - (manager.semaphore._value if manager.semaphore else 0),
        'current_rate_per_minute': len(manager.request_times),
        'available_slots': manager.semaphore._value if manager.semaphore else 0
    }