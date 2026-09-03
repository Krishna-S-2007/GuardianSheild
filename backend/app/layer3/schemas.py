from typing import Optional

from pydantic import BaseModel, Field

from app.models.session import AttackState


class SecuritySignals(BaseModel):
    """Social-engineering signal strengths."""

    authority: float = Field(ge=0.0, le=1.0)
    fear: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    isolation: float = Field(ge=0.0, le=1.0)
    financial_pressure: float = Field(ge=0.0, le=1.0)
    credential_request: float = Field(ge=0.0, le=1.0)
    threat: float = Field(ge=0.0, le=1.0)


class SecurityState(BaseModel):
    """
    Structured output produced by the Layer 3 security brain.
    """

    attack_state: AttackState = Field(
        description="Current social-engineering attack state."
    )

    risk: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall scam risk from 0.0 to 1.0."
    )

    signals: SecuritySignals = Field(
        description="Current social-engineering signal strengths."
    )

    active_claim: Optional[str] = Field(
        default=None,
        description="Most important claim made by the caller."
    )

    recommended_action: str = Field(
        description="Recommended security action for the system."
    )

    reasoning: str = Field(
        description="Short explanation for the classification."
    )