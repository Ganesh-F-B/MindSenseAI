"""
backend/rate_limiter.py

Server-side Rate Limiting & DoS / Abuse Protection for MindSenseAI (Security Hardening Phase 3).
Provides:
- In-memory sliding window log rate limiting with burst and sustained window tracking
- Dual-window enforcement: short burst window + 60s sustained window
- Identity-based partitioning:
    * Authenticated endpoints: strictly keyed by 'user:<user_id>'
    * Unauthenticated endpoints: strictly keyed by 'ip:<client_ip>' (with safe proxy handling)
- Session-independent enforcement: changing session_id cannot bypass rate limits
- Cross-user isolation: one user hitting limits never blocks another authenticated user
- Standard HTTP 429 response structure with Retry-After header
- Bounded concurrency control for heavy media processing (e.g. video analysis)
- Zero sensitive data stored in memory state (only keys and float timestamps)
- Periodic automatic cleanup of stale rate-limit history
"""

import asyncio
from collections import deque
from dataclasses import dataclass
import logging
import os
import threading
import time
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")


def set_rate_limiting_enabled(enabled: bool) -> None:
    """Enable or disable rate limiting globally (e.g. for fast unit testing)."""
    global RATE_LIMIT_ENABLED
    RATE_LIMIT_ENABLED = enabled


@dataclass(frozen=True)
class RateLimitConfig:
    sustained_requests: int  # Max requests allowed in sustained_window
    sustained_window: float   # Sustained window duration in seconds (typically 60.0)
    burst_requests: int      # Max requests allowed in burst_window
    burst_window: float      # Burst window duration in seconds (typically 5.0)


# ---------------------------------------------------------------------------
# Default Configurations (Environment-overridable)
# ---------------------------------------------------------------------------

AUTH_TOKEN_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_TOKEN_SUSTAINED", "25")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_TOKEN_BURST", "6")),
    burst_window=5.0,
)

AUTH_SIGNUP_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_SIGNUP_SUSTAINED", "20")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_SIGNUP_BURST", "5")),
    burst_window=5.0,
)

CHAT_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_CHAT_SUSTAINED", "40")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_CHAT_BURST", "4")),
    burst_window=5.0,
)

TTS_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_TTS_SUSTAINED", "30")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_TTS_BURST", "6")),
    burst_window=5.0,
)

TRANSCRIBE_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_TRANSCRIBE_SUSTAINED", "25")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_TRANSCRIBE_BURST", "6")),
    burst_window=5.0,
)

UPLOAD_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_UPLOAD_SUSTAINED", "30")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_UPLOAD_BURST", "6")),
    burst_window=5.0,
)

VIDEO_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_VIDEO_SUSTAINED", "10")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_VIDEO_BURST", "2")),
    burst_window=5.0,
)

EMERGENCY_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_EMERGENCY_SUSTAINED", "15")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_EMERGENCY_BURST", "3")),
    burst_window=5.0,
)

STATE_CHANGE_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_STATE_SUSTAINED", "20")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_STATE_BURST", "4")),
    burst_window=5.0,
)

GENERAL_READ_CONFIG = RateLimitConfig(
    sustained_requests=int(os.getenv("RATE_LIMIT_READ_SUSTAINED", "120")),
    sustained_window=60.0,
    burst_requests=int(os.getenv("RATE_LIMIT_READ_BURST", "25")),
    burst_window=5.0,
)


class InMemoryRateLimiter:
    """Thread-safe in-memory sliding log rate limiter."""

    def __init__(self):
        self._history: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 60.0

    def check(self, key: str, config: RateLimitConfig) -> Tuple[bool, int]:
        """Check whether a request for `key` is allowed under `config`.
        
        Returns:
            (allowed: bool, retry_after: int)
        """
        if not RATE_LIMIT_ENABLED:
            return True, 0

        now = time.time()

        with self._lock:
            # Periodic sweep of empty entries
            if now - self._last_cleanup > self._cleanup_interval:
                self._sweep_stale(now)
                self._last_cleanup = now

            timestamps = self._history.setdefault(key, deque())

            # Evict timestamps older than sustained_window
            max_window = max(config.sustained_window, config.burst_window)
            cutoff = now - max_window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            # Check burst limit
            burst_cutoff = now - config.burst_window
            # Count entries in burst window
            burst_count = sum(1 for ts in timestamps if ts >= burst_cutoff)
            if burst_count >= config.burst_requests:
                # Oldest timestamp inside burst window
                burst_timestamps = [ts for ts in timestamps if ts >= burst_cutoff]
                retry_after = max(1, int(burst_timestamps[0] + config.burst_window - now) + 1)
                return False, retry_after

            # Check sustained limit
            sustained_cutoff = now - config.sustained_window
            sustained_count = sum(1 for ts in timestamps if ts >= sustained_cutoff)
            if sustained_count >= config.sustained_requests:
                sustained_timestamps = [ts for ts in timestamps if ts >= sustained_cutoff]
                retry_after = max(1, int(sustained_timestamps[0] + config.sustained_window - now) + 1)
                return False, retry_after

            # Request is permitted; record timestamp
            timestamps.append(now)
            return True, 0

    def _sweep_stale(self, now: float) -> None:
        """Remove empty or long-inactive keys to prevent unbounded memory growth."""
        keys_to_remove = []
        for key, timestamps in self._history.items():
            while timestamps and timestamps[0] < now - 300.0:  # 5 min max retention
                timestamps.popleft()
            if not timestamps:
                keys_to_remove.append(key)
        for k in keys_to_remove:
            self._history.pop(k, None)

    def reset(self) -> None:
        """Clear all rate limit state (used in testing)."""
        with self._lock:
            self._history.clear()

    def get_tracked_keys(self) -> list:
        """Return list of active keys for state inspection/testing."""
        with self._lock:
            return list(self._history.keys())


# Global singleton instance
limiter = InMemoryRateLimiter()


# ---------------------------------------------------------------------------
# Client IP Resolution
# ---------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    """Resolve client IP safely.
    
    Only respects X-Forwarded-For if the direct connecting host is explicitly
    listed in the TRUSTED_PROXIES environment variable. This prevents header
    spoofing in standard direct deployments.
    """
    client_host = request.client.host if request.client else "127.0.0.1"

    trusted_proxies_str = os.getenv("TRUSTED_PROXIES", "").strip()
    if trusted_proxies_str:
        trusted_proxies = {p.strip() for p in trusted_proxies_str.split(",") if p.strip()}
        if client_host in trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                # Leftmost IP in X-Forwarded-For is the original client IP
                return forwarded.split(",")[0].strip()

    return client_host


# ---------------------------------------------------------------------------
# Enforcement Helper
# ---------------------------------------------------------------------------

def enforce_rate_limit(key: str, config: RateLimitConfig, action_name: str = "request") -> None:
    """Enforce rate limit for `key`. Raises HTTP 429 if limit is exceeded."""
    allowed, retry_after = limiter.check(key, config)
    if not allowed:
        logger.warning(f"Rate limit exceeded for key='{key}', action='{action_name}', retry_after={retry_after}s")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {action_name}. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


# ---------------------------------------------------------------------------
# Concurrency Limiter for Heavy Compute (Video Processing)
# ---------------------------------------------------------------------------

class BoundedConcurrencyGuard:
    """In-memory concurrency guard limiting simultaneous expensive operations."""

    def __init__(self, max_concurrent: int, resource_name: str = "resource"):
        self.max_concurrent = max_concurrent
        self.resource_name = resource_name
        self._active = 0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            if self._active >= self.max_concurrent:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many concurrent {self.resource_name} operations in progress. Please retry shortly.",
                    headers={"Retry-After": "5"},
                )
            self._active += 1

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)

    @property
    def current_active(self) -> int:
        with self._lock:
            return self._active


# Allow at most 2 concurrent video processing pipelines server-wide
video_concurrency_guard = BoundedConcurrencyGuard(
    max_concurrent=int(os.getenv("MAX_CONCURRENT_VIDEO_UPLOADS", "2")),
    resource_name="video analysis",
)
