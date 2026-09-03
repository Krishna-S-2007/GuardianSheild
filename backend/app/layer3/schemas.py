"""Data schemas and type definitions for GuardianShield Layer 3.

Harmonized schema supporting both Person A (Reasoning Engine) and Person B (Context Memory):
  - SecuritySignals (7-dimension attack vector scoring with dict & attribute access)
  - SecurityState (bi-directional mapping of attack_state/current_state, risk/risk_score, etc.)
  - UserContext, TrustedContact, TelemetryEvent, ReasoningContext
"""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from app.models.session import AttackState


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


class SecuritySignals(BaseModel):
    """Social-engineering signal strengths across 7 attack dimensions."""
    authority: float = Field(default=0.0, ge=0.0, le=1.0)
    fear: float = Field(default=0.0, ge=0.0, le=1.0)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    isolation: float = Field(default=0.0, ge=0.0, le=1.0)
    financial_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    credential_request: float = Field(default=0.0, ge=0.0, le=1.0)
    threat: float = Field(default=0.0, ge=0.0, le=1.0)

    def get(self, key: str, default: Any = 0.0) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def items(self):
        return self.model_dump().items()

    def keys(self):
        return self.model_dump().keys()

    def values(self):
        return self.model_dump().values()


class SecurityState(BaseModel):
    """
    Structured output produced by the Layer 3 security brain.
    Bi-directionally harmonizes Person A and Person B field naming:
      - attack_state <-> current_state
      - risk <-> risk_score
      - signals (SecuritySignals or dict)
      - recommended_action <-> action_required
      - reasoning <-> explanation / running_summary
    """
    attack_state: AttackState = Field(
        default=AttackState.NORMAL,
        description="Current social-engineering attack state."
    )
    current_state: str = Field(
        default="NORMAL",
        description="String representation of attack state."
    )
    risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall scam risk from 0.0 to 1.0."
    )
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall scam risk score (alias for risk)."
    )
    signals: Union[SecuritySignals, Dict[str, Any]] = Field(
        default_factory=SecuritySignals,
        description="Current social-engineering signal strengths."
    )
    active_claim: Optional[str] = Field(
        default=None,
        description="Most important claim made by the caller."
    )
    recommended_action: str = Field(
        default="MONITOR",
        description="Recommended security action for the system."
    )
    action_required: Optional[str] = Field(
        default=None,
        description="Action required identifier (alias for recommended_action)."
    )
    reasoning: str = Field(
        default="",
        description="Short explanation for the classification."
    )
    running_summary: str = Field(
        default="Call initiated.",
        description="Running summary preserved across session."
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Explanation alias for reasoning."
    )

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, data: Any) -> Any:
        """Bi-directional synchronization and clamping of Person A and Person B field names."""
        if not isinstance(data, dict):
            return data

        d = dict(data)

        # 1. State synchronization
        if "attack_state" in d and d["attack_state"] is not None:
            raw_state = d["attack_state"]
            state_str = raw_state.value if hasattr(raw_state, "value") else str(raw_state)
            if "current_state" not in d or d["current_state"] == "NORMAL":
                d["current_state"] = state_str
        elif "current_state" in d and d["current_state"] is not None:
            raw_str = str(d["current_state"]).upper()
            try:
                d["attack_state"] = AttackState(raw_str)
            except Exception:
                d["attack_state"] = AttackState.NORMAL

        # 2. Risk synchronization & clamping
        if "risk_score" in d and d["risk_score"] is not None:
            clamped = max(0.0, min(1.0, float(d["risk_score"])))
            d["risk_score"] = clamped
            if "risk" not in d:
                d["risk"] = clamped
            else:
                d["risk"] = max(0.0, min(1.0, float(d["risk"])))
        elif "risk" in d and d["risk"] is not None:
            clamped = max(0.0, min(1.0, float(d["risk"])))
            d["risk"] = clamped
            if "risk_score" not in d:
                d["risk_score"] = clamped

        # 3. Reasoning / Summary synchronization
        # Preserve explicit running_summary (including empty string)
        if "running_summary" in d and d["running_summary"] is not None:
            if "reasoning" not in d:
                d["reasoning"] = d["running_summary"]
            if "explanation" not in d:
                d["explanation"] = d["running_summary"]
        elif "reasoning" in d and d["reasoning"] is not None:
            if "running_summary" not in d:
                d["running_summary"] = d["reasoning"]
            if "explanation" not in d:
                d["explanation"] = d["reasoning"]
        elif "explanation" in d and d["explanation"] is not None:
            if "reasoning" not in d:
                d["reasoning"] = d["explanation"]
            if "running_summary" not in d:
                d["running_summary"] = d["explanation"]

        # 4. Action synchronization
        if "recommended_action" in d and d["recommended_action"]:
            if "action_required" not in d or d["action_required"] is None:
                d["action_required"] = d["recommended_action"]
        elif "action_required" in d and d["action_required"]:
            if "recommended_action" not in d or d["recommended_action"] == "MONITOR":
                d["recommended_action"] = d["action_required"]

        # 5. Signals normalization
        if "signals" in d:
            sig = d["signals"]
            if isinstance(sig, dict) and not isinstance(sig, SecuritySignals):
                filtered = {
                    k: max(0.0, min(1.0, float(v)))
                    for k, v in sig.items()
                    if k in SecuritySignals.model_fields
                }
                d["signals"] = SecuritySignals(**filtered)

        return d


class ReasoningContext(BaseModel):
    """Compact structured payload passed to Person A's LLM reasoning engine."""
    user_context: Dict[str, Any]
    call_memory: Dict[str, Any]
    new_telemetry: Dict[str, Any]
