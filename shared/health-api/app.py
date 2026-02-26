"""
Health/Echo API — Lightweight backend for APIM multi-region failover demo.

Each Container App instance sets the REGION environment variable so the API
self-identifies which Azure region it is running in.
"""

import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Health API",
    description="Lightweight echo/health service for APIM multi-region demo",
    version="1.0.0",
)

REGION = os.getenv("REGION", "unknown")


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "health-api",
        "region": REGION,
        "version": "1.0.0",
        "endpoints": ["/health", "/echo"],
    }


@app.get("/health")
async def health():
    """Health check — returns region identity and timestamp."""
    return {
        "status": "healthy",
        "region": REGION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/echo")
async def echo(request: Request):
    """Echo — returns request metadata and region info."""
    return {
        "region": REGION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "query_params": dict(request.query_params),
        "client_host": request.client.host if request.client else None,
    }


@app.get("/status")
async def status():
    """Simple status for APIM health probes."""
    return JSONResponse(content={"status": "ok"}, status_code=200)
