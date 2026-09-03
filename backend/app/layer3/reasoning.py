"""Layer 3 Reasoning Orchestrator (Person A / Anoop).

Coordinates analysis between the session context and Layer3Brain,
and persists the resulting security state through SessionService.
"""

from __future__ import annotations
from typing import Optional, Union

from app.layer3.brain import Layer3Brain
from app.layer3.schemas import SecurityState
from app.models.session import CallSession, AttackState
from app.services.session_service import SessionService, session_service as default_session_service


class Layer3Reasoner:
    """
    GuardianShield Layer 3 reasoning orchestration.

    Combines the existing CallSession context with the latest
    transcript, delegates analysis to the Layer 3 Brain, and
    persists the resulting security state through SessionService.
    """

    def __init__(
        self,
        brain: Optional[Layer3Brain] = None,
        session_service: Optional[SessionService] = None,
    ):
        self.brain = brain or Layer3Brain()
        self.session_service = session_service or default_session_service

    def analyze_session(
        self,
        session: CallSession,
        transcript: str,
    ) -> SecurityState:
        """
        Analyze a new transcript using the current session context.

        This method only performs reasoning. It does not modify
        the CallSession.
        """
        result = self.brain.analyze(
            transcript=transcript,
            running_summary=session.running_summary,
            recent_events=session.recent_events,
        )

        return self._validate_result(result)

    async def analyze_and_update_session(
        self,
        session: CallSession,
        transcript: str,
        new_event: Optional[str] = None,
        deepfake_score: Optional[float] = None,
    ) -> SecurityState:
        """
        Analyze the latest transcript and persist the resulting
        security state into the existing CallSession.
        """
        result = self.analyze_session(
            session=session,
            transcript=transcript,
        )

        if self.session_service is None:
            raise ValueError("SessionService is required to update the session.")

        # Handle signals whether Pydantic model or dict
        signals_dict = (
            result.signals.model_dump()
            if hasattr(result.signals, "model_dump")
            else dict(result.signals)
        )

        # Convert to AttackState enum if needed
        attack_state_enum = result.attack_state
        if isinstance(attack_state_enum, str):
            try:
                attack_state_enum = AttackState(attack_state_enum)
            except Exception:
                attack_state_enum = AttackState.NORMAL

        await self.session_service.update_session_state(
            session_id=session.session_id,
            current_state=attack_state_enum,
            risk_score=result.risk,
            summary=result.reasoning,
            signals=signals_dict,
            active_claim=result.active_claim,
            new_event=new_event or transcript,
            deepfake_score=deepfake_score,
        )

        return result

    @staticmethod
    def _validate_result(result: SecurityState) -> SecurityState:
        """
        Validate and clamp security values before they are persisted into the session.
        """
        # Clamp overall risk
        result.risk = max(0.0, min(1.0, float(result.risk)))
        result.risk_score = result.risk

        # Clamp every individual security signal
        signal_fields = (
            "authority",
            "fear",
            "urgency",
            "isolation",
            "financial_pressure",
            "credential_request",
            "threat",
        )

        for field_name in signal_fields:
            if hasattr(result.signals, field_name):
                val = getattr(result.signals, field_name)
                setattr(result.signals, field_name, max(0.0, min(1.0, float(val))))
            elif isinstance(result.signals, dict) and field_name in result.signals:
                result.signals[field_name] = max(0.0, min(1.0, float(result.signals[field_name])))

        return result
