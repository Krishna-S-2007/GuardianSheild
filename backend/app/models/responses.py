from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import time


class BaseResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully."
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    active_devices: int = 0
    active_sessions: int = 0
    timestamp: float = Field(default_factory=time.time)


class StateUpdatePush(BaseModel):
    type: str = "state_update"
    session_id: str
    state: str
    risk: float
    summary: str
    signals: Dict[str, float]
    active_claim: Optional[str] = None
    is_critical: bool = False
    timestamp: float = Field(default_factory=time.time)


class VerificationUpdatePush(BaseModel):
    type: str = "verification_update"
    session_id: str
    status: str  # e.g., "WAITING", "VERIFIED", "FAILED", "TIMEOUT"
    claim: Optional[str] = None
    result: Optional[str] = None
    contact_name: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
