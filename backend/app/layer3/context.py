"""Reasoning context builder for GuardianShield Layer 3."""

from __future__ import annotations
from typing import Any, Dict
from .schemas import UserContext, TelemetryEvent
from .memory import CallMemory


def build_reasoning_context(
    user_context: UserContext,
    call_memory: CallMemory,
    new_telemetry: TelemetryEvent,
) -> Dict[str, Any]:
    """
    Constructs a compact context dictionary for Person A's LLM reasoning engine.
    Ensures bounded token payload consisting of:
      1. User profile context
      2. Call memory (running summary + sliding event window)
      3. New telemetry packet
    """
    return {
        "user_context": {
            "user_id": user_context.user_id,
            "user_name": user_context.user_name,
            "role": user_context.role,
            "transaction_limit": user_context.transaction_limit,
            "trusted_contacts": [c.model_dump() for c in user_context.trusted_contacts],
        },
        "call_memory": call_memory.to_dict(),
        "new_telemetry": {
            "transcript_delta": new_telemetry.transcript_delta,
            "deepfake_score": round(new_telemetry.deepfake_score, 3),
            "speaker_id": new_telemetry.speaker_id,
            "is_critical": new_telemetry.is_critical,
            "acoustic_signals": new_telemetry.acoustic_signals,
            "timestamp": new_telemetry.timestamp,
        },
    }
