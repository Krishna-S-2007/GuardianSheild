from app.layer3.brain import Layer3Brain
from app.layer3.schemas import SecurityState
from app.models.session import CallSession
from app.services.session_service import SessionService


class Layer3Reasoner:
    """
    GuardianShield Layer 3 reasoning orchestration.

    Combines the existing CallSession context with the latest
    transcript, delegates analysis to the Layer 3 Brain, and
    persists the resulting security state through the existing
    SessionService.
    """

    def __init__(
        self,
        brain: Layer3Brain | None = None,
        session_service: SessionService | None = None,
    ):
        self.brain = brain or Layer3Brain()
        self.session_service = session_service

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
        new_event: str | None = None,
        deepfake_score: float | None = None,
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
            raise ValueError(
                "SessionService is required to update the session."
            )

        await self.session_service.update_session_state(
            session_id=session.session_id,
            current_state=result.attack_state,
            risk_score=result.risk,
            summary=result.reasoning,
            signals=result.signals.model_dump(),
            active_claim=result.active_claim,
            new_event=new_event,
            deepfake_score=deepfake_score,
        )

        return result

    @staticmethod
    def _validate_result(
        result: SecurityState,
    ) -> SecurityState:
        """
        Validate and clamp security values before they are
        persisted into the session.
        """

        # Clamp overall risk.
        result.risk = max(
            0.0,
            min(1.0, result.risk),
        )

        # Clamp every individual security signal.
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
            value = getattr(
                result.signals,
                field_name,
            )

            setattr(
                result.signals,
                field_name,
                max(0.0, min(1.0, value)),
            )

        return result