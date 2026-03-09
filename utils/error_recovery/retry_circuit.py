#!/usr/bin/env python3
"""
Error Recovery Utilities - Gold Tier Phase 3
Provides retry logic, circuit breaker, and graceful degradation patterns.

Usage:
    from utils.error_recovery import with_retry, circuit_breaker, RetryConfig

    @with_retry(max_attempts=3, backoff_factor=2)
    def call_external_api():
        # Your code here
        pass

    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    def fragile_operation():
        # Your code here
        pass
"""

import time
import functools
import logging
from typing import Any, Callable, Dict, Optional, Type
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading

# Optional: import requests for examples (only used in __main__)
try:
    import requests
    _requests_available = True
except ImportError:
    _requests_available = False

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Consecutive failures to open circuit
    recovery_timeout: int = 60          # Seconds to wait before half-open
    success_threshold: int = 3          # Successes in half-open to close
    timeout: int = 30                   # Request timeout in seconds
    expected_exceptions: tuple = (ConnectionError, TimeoutError, Exception)


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0             # Initial delay in seconds
    max_delay: float = 60.0             # Maximum delay between retries
    backoff_factor: float = 2.0         # Exponential backoff multiplier
    jitter: bool = True                 # Add random jitter to prevent thundering herd
    retry_on: tuple = (ConnectionError, TimeoutError, Exception)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retry_on: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        jitter: Add random jitter to delay (default: True)
        retry_on: Tuple of exception types to retry on (default: all)

    Example:
        @with_retry(max_attempts=5, backoff_factor=3)
        def call_api():
            # Might fail transiently
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f"Retry exhausted after {max_attempts} attempts for {func.__name__}: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)

                    # Add jitter (±20%) to prevent thundering herd
                    if jitter:
                        import random
                        jitter_amount = delay * 0.2
                        delay += random.uniform(-jitter_amount, jitter_amount)

                    logger.warning(f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents calls to failing services and allows recovery time.
    Thread-safe implementation.

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service considered down, requests fail fast
    - HALF_OPEN: Testing if service recovered, allow limited requests

    Example:
        breaker = CircuitBreaker(
            name="facebook_api",
            failure_threshold=5,
            recovery_timeout=60
        )

        @breaker
        def call_facebook():
            return requests.post(...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
        expected_exceptions: tuple = (Exception,)
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def __call__(self, func: Callable) -> Callable:
        """Decorator usage."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if self._last_failure_time and \
                   datetime.now() - self._last_failure_time >= timedelta(seconds=self.recovery_timeout):
                    logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN for recovery test")
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    # Circuit is open, fail fast
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)

            # Success - update circuit state
            with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    self._success_count += 1
                    if self._success_count >= self.success_threshold:
                        logger.info(f"Circuit breaker '{self.name}' recovered, transitioning to CLOSED")
                        self._state = CircuitState.CLOSED
                        self._failure_count = 0
                        self._last_failure_time = None
                elif self._state == CircuitState.CLOSED:
                    # Reset failure count on success
                    self._failure_count = 0

            return result

        except self.expected_exceptions as e:
            with self._lock:
                self._failure_count += 1
                self._last_failure_time = datetime.now()

                if self._state == CircuitState.CLOSED and self._failure_count >= self.failure_threshold:
                    logger.warning(f"Circuit breaker '{self.name}' opened after {self.failure_count} failures")
                    self._state = CircuitState.OPEN
                elif self._state == CircuitState.HALF_OPEN:
                    logger.warning(f"Circuit breaker '{self.name}' failed during recovery test, reopening")
                    self._state = CircuitState.OPEN

            raise

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
        logger.info(f"Circuit breaker '{self.name}' manually reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout
            }


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    success_threshold: int = 3,
    expected_exceptions: tuple = (Exception,)
):
    """
    Decorator for circuit breaker pattern.

    Args:
        name: Unique name for this circuit breaker
        failure_threshold: Consecutive failures to open circuit
        recovery_timeout: Seconds to wait before testing recovery
        success_threshold: Successes needed to close circuit
        expected_exceptions: Exceptions that count as failures

    Example:
        @with_circuit_breaker("facebook_api", failure_threshold=5)
        def post_to_facebook(message):
            return requests.post(...)
    """
    # Store circuit breaker in function attribute to persist across calls
    if not hasattr(with_circuit_breaker, "_breakers"):
        with_circuit_breaker._breakers = {}

    if name not in with_circuit_breaker._breakers:
        with_circuit_breaker._breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            expected_exceptions=expected_exceptions
        )

    breaker = with_circuit_breaker._breakers[name]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def get_all_circuit_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    if not hasattr(with_circuit_breaker, "_breakers"):
        return {}
    return {name: breaker.get_stats() for name, breaker in with_circuit_breaker._breakers.items()}


# Example usage in MCP server:
if __name__ == "__main__":
    if not _requests_available:
        print("Note: Install 'requests' library to run examples")
        print("pip install requests")
    else:
        # Example 1: Retry
        @with_retry(max_attempts=3, backoff_factor=2)
        def fragile_api_call(url):
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()

        # Example 2: Circuit Breaker
        @with_circuit_breaker("my_service", failure_threshold=5, recovery_timeout=60)
        def call_external_service():
            # Might fail
            pass

        # Example 3: Manual circuit breaker
        breaker = CircuitBreaker("facebook", failure_threshold=5)
        try:
            result = breaker.call(requests.post, "https://api.facebook.com/...")
        except Exception as e:
            print(f"Service unavailable: {e}")

        # Get stats
        print(get_all_circuit_stats())
