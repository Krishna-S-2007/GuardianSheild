from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import time


class CallStatus(str, Enum):
    IDLE = "IDLE"
    RINGING = "RINGING"
    CONNECTED = "CONNECTED"
    ENDED = "ENDED"
    REJECTED = "REJECTED"


class AttackState(str, Enum):
    NORMAL = "NORMAL"
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    FEAR_INDUCTION = "FEAR_INDUCTION"
    ISOLATION = "ISOLATION"
    URGENCY = "URGENCY"
    FINANCIAL_PRESSURE = "FINANCIAL_PRESSURE"
    CREDENTIAL_EXTRACTION = "CREDENTIAL_EXTRACTION"
    FAMILY_EMERGENCY = "FAMILY_EMERGENCY"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"


class SignalingType(str, Enum):
    REGISTER = "register"
    REGISTERED = "registered"
    CALL_INITIATE = "call_initiate"
    INCOMING_CALL = "incoming_call"
    CALL_ACCEPT = "call_accept"
    CALL_REJECT = "call_reject"
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice_candidate"
    CALL_END = "call_end"
    STATE_UPDATE = "state_update"
    VERIFICATION_UPDATE = "verification_update"
    TELEMETRY = "telemetry"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"


class TrustedContact(BaseModel):
    name: str
    relationship: str
    device_id: str
    phone_number: Optional[str] = None


class DeviceProfile(BaseModel):
    device_id: str
    user_id: Optional[str] = None
    user_name: str = "GuardianShield User"
    online: bool = True
    trusted_contacts: List[TrustedContact] = Field(default_factory=list)
    last_seen: float = Field(default_factory=time.time)


class SignalingMessage(BaseModel):
    type: SignalingType
    sender_device_id: str
    target_device_id: Optional[str] = None
    session_id: Optional[str] = None
    sdp: Optional[str] = None
    sdp_type: Optional[str] = None
    candidate: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class CallSession(BaseModel):
    session_id: str
    caller_device_id: str
    callee_device_id: str
    status: CallStatus = CallStatus.RINGING
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None

    # Memory & State
    current_state: AttackState = AttackState.NORMAL
    risk_score: float = 0.0
    running_summary: str = "Call session initialized."
    signals: Dict[str, float] = Field(default_factory=lambda: {
        "authority": 0.0,
        "fear": 0.0,
        "urgency": 0.0,
        "isolation": 0.0,
        "financial_pressure": 0.0,
        "credential_request": 0.0,
        "threat": 0.0
    })
    active_claim: Optional[str] = None
    recent_events: List[str] = Field(default_factory=list)
    deepfake_score_history: List[float] = Field(default_factory=list)
    telemetry_count: int = 0
    updated_at: float = Field(default_factory=time.time)
