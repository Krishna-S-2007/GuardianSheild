"""GuardianShield Layer 3 - Context Memory, Session State, and Reasoning Integration.

Harmonized exports for Person A (Reasoning Engine) and Person B (Context Memory Machinery).
"""

from .schemas import (
    UserContext,
    TrustedContact,
    TelemetryEvent,
    SecuritySignals,
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
from .brain import (
    Layer3Brain,
    GeminiBrain,
    evaluate_reasoning,
    gemini_brain,
)
from .reasoning import Layer3Reasoner

__all__ = [
    # Schemas
    "UserContext",
    "TrustedContact",
    "TelemetryEvent",
    "SecuritySignals",
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
    # Brain & Reasoning (Person A + Person B)
    "Layer3Brain",
    "Layer3Reasoner",
    "GeminiBrain",
    "evaluate_reasoning",
    "gemini_brain",
    "mock_reasoning_engine",
]
