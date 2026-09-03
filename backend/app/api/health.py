import time
from fastapi import APIRouter
from app.models.responses import HealthResponse
from app.core.config import settings
from app.websocket.connection_manager import manager
from app.services.session_service import session_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Returns backend health status, active WebSocket connections, and active sessions."""
    active_sessions_count = await session_service.get_active_sessions_count()
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        active_devices=manager.get_online_count(),
        active_sessions=active_sessions_count,
        timestamp=time.time()
    )
