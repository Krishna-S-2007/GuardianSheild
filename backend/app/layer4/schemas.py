"""Data schemas for GuardianShield Layer 4 Verification & Actions."""

from __future__ import annotations
import time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    IDLE = "IDLE"
    WAITING_CONTACT = "WAITING_CONTACT"
    CONFIRMED_LEGITIMATE = "CONFIRMED_LEGITIMATE"
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    TIMEOUT = "TIMEOUT"
    STEP_UP_PROMPTED = "STEP_UP_PROMPTED"
    CALL_TERMINATED = "CALL_TERMINATED"


class VerificationRequest(BaseModel):
    session_id: str
    victim_device_id: str
    victim_name: Optional[str] = "Executive"
    contact_device_id: str
    contact_name: str
    active_claim: str
    risk_score: float
    timestamp: float = Field(default_factory=time.time)


class VerificationResponse(BaseModel):
    session_id: str
    contact_device_id: str
    is_legitimate: bool
    notes: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class VerificationRecord(BaseModel):
    session_id: str
    victim_device_id: str
    status: VerificationStatus = VerificationStatus.WAITING_CONTACT
    active_claim: Optional[str] = None
    target_contact_name: Optional[str] = None
    target_contact_device_id: Optional[str] = None
    outcome: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
