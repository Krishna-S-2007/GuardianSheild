"""GuardianShield Layer 3 - Context Memory, Session State, and Reasoning Integration.

Person B responsibility: memory machinery, session lifecycle, context construction,
and Layer 3 service wrapper for Member 4's backend integration.
"""

from .schemas import (
    UserContext,
    TrustedContact,
    TelemetryEvent,
    SecurityState,
    ReasoningContext,
)
from .memory import CallMemory
from .session import SessionManager, session_manager
from .context import build_reasoning_context
from .service import (
    Layer3Service,
    process_telemetry,
    end_session,
    layer3_session_stats,
    default_layer3_service,
)
from .mock_brain import mock_reasoning_engine
from .brain import GeminiBrain, evaluate_reasoning, gemini_brain

__all__ = [
    # Schemas
    "UserContext",
    "TrustedContact",
    "TelemetryEvent",
    "SecurityState",
    "ReasoningContext",
    # Memory
    "CallMemory",
    # Session
    "SessionManager",
    "session_manager",
    # Context
    "build_reasoning_context",
    # Service
    "Layer3Service",
    "process_telemetry",
    "end_session",
    "layer3_session_stats",
    "default_layer3_service",
    # Brain
    "GeminiBrain",
    "evaluate_reasoning",
    "gemini_brain",
    "mock_reasoning_engine",
]
