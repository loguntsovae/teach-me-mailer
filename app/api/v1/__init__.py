from fastapi import APIRouter

# Aggregate sub-routers for v1
from .health import router as health_router
from .mail import router as mail_router
from .usage import router as usage_router

router = APIRouter()

# Include feature-specific routers. The main app will mount this aggregate
# router under /api/v1 (and also include it at root for the health check).
router.include_router(mail_router)
router.include_router(usage_router)
router.include_router(health_router)
