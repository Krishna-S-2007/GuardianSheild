"""Data schemas and type definitions for GuardianShield Layer 3."""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrustedContact(BaseModel):
    """Trusted contact profile for out-of-band identity verification."""
    name: str
    relationship: str
    device_id: Optional[str] = None
    phone_number: Optional[str] = None


class UserContext(BaseModel):
    """Static or profile-level user context injected into reasoning context."""
    user_id: str
    user_name: Optional[str] = "GuardianShield User"
    role: Optional[str] = "Executive"
    trusted_contacts: List[TrustedContact] = Field(default_factory=list)
    transaction_limit: float = 50000.0


class TelemetryEvent(BaseModel):
    """Ingested telemetry packet from Layer 1 (Audio) and Layer 2 (Transcription)."""
    event_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    transcript_delta: str
    deepfake_score: float = 0.0  # 0.0 = Authentic human, 1.0 = Synthetic deepfake
    speaker_id: Optional[str] = None
    acoustic_signals: Dict[str, Any] = Field(default_factory=dict)
    is_critical: bool = False  # True when fast-path triggers are detected


class SecurityState(BaseModel):
    """Output state produced by Layer 3 reasoning engine and stored in memory."""
    current_state: str = "NORMAL"  # NORMAL, SUSPICIOUS, ISOLATION, ESCALATED, BLOCKED, etc.
    risk_score: float = 0.0        # Bounded between 0.0 and 1.0
    running_summary: str = "Call initiated."
    active_claim: Optional[str] = None
    signals: Dict[str, Any] = Field(default_factory=dict)
    action_required: Optional[str] = None  # None, STEP_UP_AUTH, OUT_OF_BAND_VERIFY, TERMINATE
    explanation: Optional[str] = None


class ReasoningContext(BaseModel):
    """Compact structured payload passed to Person A's LLM reasoning engine."""
    user_context: Dict[str, Any]
    call_memory: Dict[str, Any]
    new_telemetry: Dict[str, Any]
