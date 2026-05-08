import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class SlidingWindowRateLimiter(BaseHTTPMiddleware):
    """Simple in-memory sliding-window limiter per client IP and path group."""

    def __init__(self, app, *, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.hits: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        limit = self.max_requests
        if path.startswith("/api/auth/login"):
            limit = 10
        elif path.startswith("/api/auth/signup"):
            limit = 8
        elif path.startswith("/api/processing/upload"):
            limit = 12

        key = f"{client_ip}:{path.split('/', 3)[:3]}"
        now = time.time()

        async with self._lock:
            bucket = self.hits[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please retry shortly.",
                )

            bucket.append(now)

        return await call_next(request)


class WSConnectionGuard:
    def __init__(self, *, max_per_ip: int = 5, max_total: int = 500):
        self.max_per_ip = max_per_ip
        self.max_total = max_total
        self.total = 0
        self.by_ip: DefaultDict[str, int] = defaultdict(int)

    def allow(self, ip: str) -> bool:
        if self.total >= self.max_total:
            return False
        if self.by_ip[ip] >= self.max_per_ip:
            return False
        self.total += 1
        self.by_ip[ip] += 1
        return True

    def release(self, ip: str):
        if self.by_ip[ip] > 0:
            self.by_ip[ip] -= 1
        if self.total > 0:
            self.total -= 1
