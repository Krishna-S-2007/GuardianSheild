from typing import Dict, Optional
from pydantic import BaseModel, Field
import time


class TelemetryPayload(BaseModel):
    session_id: str
    device_id: str
    timestamp: float = Field(default_factory=time.time)
    transcript_delta: str = ""
    deepfake_score: Optional[float] = None
    language: Optional[str] = "en"
    is_critical: bool = False
    metadata: Optional[Dict[str, str]] = None


class TelemetryIngestResponse(BaseModel):
    status: str = "success"
    session_id: str
    current_state: str
    risk_score: float
    is_critical: bool
    summary: str
    timestamp: float = Field(default_factory=time.time)
