#!/usr/bin/env python3
"""
Simple FastAPI app to test Sentry integration
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi import FastAPI

# Initialize Sentry SDK
sentry_sdk.init(
    dsn="https://fccb9ee60a71cb42db499c0546e83160@o4510323039535104.ingest.de.sentry.io/4510323045892176",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
    environment="dev",
)

app = FastAPI(title="Sentry Test Server")

@app.get("/")
async def root():
    return {"message": "Sentry Test Server Running"}

@app.get("/debug-sentry")
async def debug_sentry():
    """
    Debug endpoint to test Sentry error capture.
    
    This endpoint intentionally raises an exception to verify that Sentry
    is properly configured and can capture errors from the FastAPI application.
    """
    print("Testing Sentry error capture")
    
    # Intentionally raise an exception to test Sentry integration
    raise Exception("Test exception for Sentry error tracking - this is intentional!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)