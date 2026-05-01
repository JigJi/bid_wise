from fastapi import APIRouter

from app.api.v1 import projects, tor

router = APIRouter(prefix="/api/v1")
router.include_router(projects.router)
router.include_router(tor.router)

__all__ = ["router"]
