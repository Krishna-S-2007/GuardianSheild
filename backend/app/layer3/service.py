"""Core Layer 3 Service coordinating memory, context generation, and reasoning."""

from __future__ import annotations
import logging
import time
from typing import Any, Callable, Dict, Optional

from .schemas import UserContext, TelemetryEvent, SecurityState
from .session import SessionManager, session_manager
from .context import build_reasoning_context
from .mock_brain import mock_reasoning_engine
from app.services.session_service import session_service, SessionService
from app.models.session import AttackState

logger = logging.getLogger("guardianshield.layer3")


class Layer3Service:
    """
    Coordinates context building, memory management, and reasoning engine invocation.
    Provides robust failover protection and integration with backend session infrastructure.
    """

    def __init__(
        self,
        memory_manager: Optional[SessionManager] = None,
        backend_session_service: Optional[SessionService] = None,
        reasoning_engine: Optional[Callable[[Dict[str, Any]], SecurityState]] = None,
    ):
        self.memory_manager = memory_manager or session_manager
        self.backend_session_service = backend_session_service or session_service
        self.reasoning_engine = reasoning_engine or mock_reasoning_engine

    def set_reasoning_engine(self, engine_fn: Callable[[Dict[str, Any]], SecurityState]) -> None:
        """Allows injecting Person A's real Gemini reasoning engine."""
        self.reasoning_engine = engine_fn

    async def process_telemetry(
        self,
        session_id: str,
        telemetry: TelemetryEvent,
        user_context: Optional[UserContext] = None,
    ) -> SecurityState:
        """
        Main pipeline method processing an incoming telemetry packet.
        
        Workflow:
          1. Fallback / fetch user context
          2. Retrieve or create session memory in Layer 3
          3. Append telemetry to bounded event window
          4. Build compact reasoning context
          5. Call Person A reasoning engine (with failover protection)
          6. Persist resulting state into Layer 3 memory & backend session service
          7. Return updated SecurityState
        """
        # 1. Fallback user context
        if user_context is None:
            user_context = UserContext(
                user_id="DEFAULT_USER",
                user_name="GuardianShield User",
                role="Executive",
            )

        # 2. Retrieve Layer 3 call memory
        memory = self.memory_manager.get_or_create_session(session_id)

        # 3. Add to sliding event window
        memory.add_telemetry_event(telemetry)

        # 4. Construct compact context payload
        context_payload = build_reasoning_context(user_context, memory, telemetry)

        # 5. Invoke reasoning engine with exception handling
        try:
            # Supports both async and sync reasoning callables
            import inspect
            if inspect.iscoroutinefunction(self.reasoning_engine):
                new_state = await self.reasoning_engine(context_payload)
            else:
                new_state = self.reasoning_engine(context_payload)

            if isinstance(new_state, dict):
                new_state = SecurityState(**new_state)
            elif not isinstance(new_state, SecurityState):
                raise TypeError(f"Reasoning engine must return SecurityState or dict, got {type(new_state)}")

            # 6. Update Layer 3 memory
            memory.update_from_security_state(new_state)

        except Exception as exc:
            logger.error(
                f"[Layer 3] Reasoning engine execution failed for session {session_id}: {exc}",
                exc_info=True,
            )
            # Fail-safe preservation: keep current state, never overwrite with null/empty state
            new_state = SecurityState(
                current_state=memory.current_state,
                risk_score=memory.risk_score,
                running_summary=memory.running_summary,
                active_claim=memory.active_claim,
                signals=memory.signals,
                action_required=None,
                explanation=f"Fail-Safe Mode: Reasoning engine encountered an error ({str(exc)}). Preserved previous state.",
            )

        # 7. Sync state with backend session service if session exists
        try:
            backend_state_enum = AttackState.NORMAL
            try:
                backend_state_enum = AttackState(new_state.current_state)
            except Exception:
                pass

            signals_float = {k: float(v) for k, v in new_state.signals.items() if isinstance(v, (int, float))}

            await self.backend_session_service.update_session_state(
                session_id=session_id,
                current_state=backend_state_enum,
                risk_score=new_state.risk_score,
                summary=new_state.running_summary,
                signals=signals_float,
                active_claim=new_state.active_claim,
                new_event=telemetry.transcript_delta,
                deepfake_score=telemetry.deepfake_score,
            )
        except Exception as exc:
            logger.debug(f"[Layer 3] Backend session update notice for {session_id}: {exc}")

        return new_state


# Global singleton instance
default_layer3_service = Layer3Service()


async def process_telemetry(
    session_id: str,
    telemetry: TelemetryEvent,
    user_context: Optional[UserContext] = None,
) -> SecurityState:
    """Convenience functional wrapper for backend integration."""
    return await default_layer3_service.process_telemetry(session_id, telemetry, user_context)
