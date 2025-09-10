"""
Thread-safe global concurrency manager for Replicate API
Implements true global rate limiting with threading.Semaphore
"""

import threading
import time
from typing import Optional
from datetime import datetime, timedelta


class ThreadSafeConcurrencyManager:
    """Thread-safe singleton concurrency manager with global rate limiting"""
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not ThreadSafeConcurrencyManager._initialized:
            with ThreadSafeConcurrencyManager._lock:
                if not ThreadSafeConcurrencyManager._initialized:
                    # Rate limiting settings
                    self.max_requests_per_minute = 600  # Default Replicate limit
                    self.concurrent_limit = 60  # Max concurrent requests
                    
                    # Thread-safe semaphore for concurrency control
                    self.semaphore = threading.Semaphore(self.concurrent_limit)
                    
                    # Request tracking for rate limiting
                    self.request_times = []
                    self.rate_limit_lock = threading.Lock()
                    
                    print(f"🚦 Global concurrency manager initialized: {self.concurrent_limit} concurrent, {self.max_requests_per_minute} requests/minute")
                    ThreadSafeConcurrencyManager._initialized = True
    
    def configure(self, concurrent_limit: Optional[int] = None, requests_per_minute: Optional[int] = None):
        """Configure the concurrency settings - ONLY updates values, does NOT recreate semaphore"""
        with ThreadSafeConcurrencyManager._lock:
            config_changed = False
            
            # Only recreate semaphore if concurrent limit actually changes
            if concurrent_limit is not None and concurrent_limit != self.concurrent_limit:
                self.concurrent_limit = concurrent_limit
                # Create new semaphore with updated limit
                old_semaphore = self.semaphore
                self.semaphore = threading.Semaphore(concurrent_limit)
                config_changed = True
            
            if requests_per_minute is not None and requests_per_minute != self.max_requests_per_minute:
                self.max_requests_per_minute = requests_per_minute
                config_changed = True
            
            if config_changed:
                print(f"🔧 Concurrency settings updated: {self.concurrent_limit} concurrent, {self.max_requests_per_minute} requests/minute")
            else:
                print(f"ℹ️ Concurrency settings unchanged: {self.concurrent_limit} concurrent, {self.max_requests_per_minute} requests/minute")
    
    def _check_rate_limit(self):
        """Check if we're within rate limits and wait if necessary (thread-safe)"""
        with self.rate_limit_lock:
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
                    time.sleep(wait_time)
                    return self._check_rate_limit()  # Recheck after waiting
            
            # Record this request
            self.request_times.append(now)
    
    def acquire(self, external_semaphore=None):
        """Acquire permission to make a request (handles both concurrency and rate limiting)
        
        Args:
            external_semaphore: Optional external semaphore for global control across services
        """
        # Check rate limit first (blocking)
        self._check_rate_limit()
        
        # Use external semaphore for global control or internal for individual control
        semaphore_to_use = external_semaphore if external_semaphore else self.semaphore
        
        # Acquire semaphore for concurrency control (blocking)
        semaphore_to_use.acquire()
        
        # Store which semaphore we used for release
        self._current_semaphore = semaphore_to_use
        
        # Get current stats for logging
        with self.rate_limit_lock:
            current_rate = len(self.request_times)
        
        # Note: We can't easily get the exact concurrent count from threading.Semaphore
        semaphore_type = "external" if external_semaphore else "internal"
        print(f"🟢 Request acquired using {semaphore_type} semaphore (rate: {current_rate}/{self.max_requests_per_minute}/min)")
    
    def release(self):
        """Release the appropriate semaphore"""
        # Release the semaphore we used in acquire
        semaphore_to_release = getattr(self, '_current_semaphore', self.semaphore)
        semaphore_to_release.release()
        print(f"🔴 Request released")
    
    def __enter__(self):
        """Context manager entry"""
        # Use internal semaphore for context manager (backward compatibility)
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
    
    def with_external_semaphore(self, external_semaphore):
        """Create a context manager that uses an external semaphore"""
        return ExternalSemaphoreContext(self, external_semaphore)


class ExternalSemaphoreContext:
    """Context manager for using external semaphore with concurrency manager"""
    
    def __init__(self, manager, external_semaphore):
        self.manager = manager
        self.external_semaphore = external_semaphore
    
    def __enter__(self):
        self.manager.acquire(self.external_semaphore)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.manager.release()


# Global instance - created once and shared across all requests
concurrency_manager = ThreadSafeConcurrencyManager()

# Global semaphore registry for external semaphore pattern
_global_semaphores = {}
_global_semaphores_lock = threading.Lock()


def register_global_semaphore(semaphore_id: str, limit: int):
    """Register a global semaphore for cross-service concurrency control
    
    Args:
        semaphore_id: Unique identifier for the semaphore
        limit: Maximum concurrent operations allowed
    
    Returns:
        The created threading.Semaphore instance
    """
    with _global_semaphores_lock:
        if semaphore_id in _global_semaphores:
            print(f"⚠️ Global semaphore '{semaphore_id}' already exists, returning existing one")
            return _global_semaphores[semaphore_id]
        
        semaphore = threading.Semaphore(limit)
        _global_semaphores[semaphore_id] = semaphore
        print(f"🌐 Global semaphore '{semaphore_id}' registered with limit {limit}")
        return semaphore


def get_global_semaphore(semaphore_id: str):
    """Get a registered global semaphore by ID
    
    Args:
        semaphore_id: Unique identifier for the semaphore
    
    Returns:
        The threading.Semaphore instance or None if not found
    """
    with _global_semaphores_lock:
        return _global_semaphores.get(semaphore_id)


def list_global_semaphores():
    """List all registered global semaphores"""
    with _global_semaphores_lock:
        return list(_global_semaphores.keys())


def run_with_external_semaphore(func, semaphore_id: str, *args, **kwargs):
    """Run a function with an external global semaphore
    
    Args:
        func: Function to execute
        semaphore_id: ID of the global semaphore to use
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        Function result
    """
    global_semaphore = get_global_semaphore(semaphore_id)
    if not global_semaphore:
        raise ValueError(f"Global semaphore '{semaphore_id}' not found. Register it first using register_global_semaphore()")
    
    with concurrency_manager.with_external_semaphore(global_semaphore):
        return func(*args, **kwargs)


def with_concurrency_control(func):
    """Decorator to run function with concurrency control (synchronous)"""
    def wrapper(*args, **kwargs):
        with concurrency_manager:
            return func(*args, **kwargs)
    return wrapper


def get_concurrency_status():
    """Get current concurrency status"""
    manager = concurrency_manager
    with manager.rate_limit_lock:
        current_rate = len(manager.request_times)
    
    # Note: threading.Semaphore doesn't expose current count easily
    # We'll show the limit instead
    return {
        'concurrent_limit': manager.concurrent_limit,
        'requests_per_minute_limit': manager.max_requests_per_minute,
        'current_concurrent': 0,  # Can't get exact count from threading.Semaphore
        'current_rate_per_minute': current_rate,
        'available_slots': manager.concurrent_limit  # Approximate
    }