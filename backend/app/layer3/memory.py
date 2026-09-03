"""Call memory and bounded event buffer management."""

from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
from collections import deque
from .schemas import TelemetryEvent, SecurityState


class CallMemory:
    """
    Maintains bounded temporal state and rolling event history for a call session.
    Prevents unbounded context growth for LLM reasoning calls.
    """

    def __init__(self, session_id: str, max_recent_events: int = 8):
        self.session_id: str = session_id
        self.current_state: str = "NORMAL"
        self.risk_score: float = 0.0
        self.running_summary: str = "Call initiated."
        self.signals: Dict[str, Any] = {
            "authority": 0.0,
            "fear": 0.0,
            "urgency": 0.0,
            "isolation": 0.0,
            "financial_pressure": 0.0,
            "credential_request": 0.0,
            "threat": 0.0,
        }
        self.active_claim: Optional[str] = None
        self._max_recent_events: int = max_recent_events
        self.recent_events: deque = deque(maxlen=max_recent_events)
        self.deepfake_score_history: deque = deque(maxlen=max_recent_events * 2)
        self.event_counter: int = 0
        self.created_at: float = time.time()
        self.updated_at: float = time.time()

    def add_telemetry_event(self, event: TelemetryEvent) -> None:
        """Appends a new event into the bounded sliding window."""
        self.event_counter += 1
        event_entry = {
            "event_seq": self.event_counter,
            "timestamp": event.timestamp,
            "transcript_delta": event.transcript_delta,
            "deepfake_score": round(event.deepfake_score, 3),
            "is_critical": event.is_critical,
            "speaker_id": event.speaker_id,
        }
        self.recent_events.append(event_entry)
        self.deepfake_score_history.append(event.deepfake_score)
        self.updated_at = time.time()

    def update_from_security_state(self, state: SecurityState) -> None:
        """Updates internal state and running summary from reasoning output."""
        if state.current_state:
            self.current_state = state.current_state
        self.risk_score = max(0.0, min(1.0, float(state.risk_score)))
        
        # Only overwrite running summary if a non-empty summary is returned
        if state.running_summary and state.running_summary.strip():
            self.running_summary = state.running_summary.strip()
        
        if state.active_claim is not None:
            self.active_claim = state.active_claim
            
        if state.signals:
            self.signals.update(state.signals)
            
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current memory state into a compact dictionary."""
        return {
            "session_id": self.session_id,
            "current_state": self.current_state,
            "risk_score": round(self.risk_score, 3),
            "running_summary": self.running_summary,
            "signals": self.signals,
            "active_claim": self.active_claim,
            "recent_events": list(self.recent_events),
            "deepfake_history": list(self.deepfake_score_history)[-5:],
            "total_events_processed": self.event_counter,
            "duration_seconds": round(time.time() - self.created_at, 1),
        }
