"""Thread-safe session manager ensuring strict multi-call isolation.

Implements the full session lifecycle per the Layer 3 specification:
  create_session() / get_session() / get_or_create_session()
  update_session() / end_session()
"""

from __future__ import annotations
import threading
import time
from typing import Any, Dict, List, Optional
from .memory import CallMemory


class SessionManager:
    """Manages active call memories with concurrency safety and strict isolation."""

    def __init__(self, default_max_events: int = 8):
        self._sessions: Dict[str, CallMemory] = {}
        self._ended_sessions: Dict[str, float] = {}  # session_id -> end_time tombstone
        self._lock = threading.Lock()
        self._default_max_events = default_max_events

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    def create_session(self, session_id: str, max_events: Optional[int] = None) -> CallMemory:
        """
        Explicitly initializes a new call memory session.

        Raises ValueError if the session is already active.
        Raises ValueError if the session was already ended (tombstone guard).
        """
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session '{session_id}' is already active.")
            if session_id in self._ended_sessions:
                raise ValueError(
                    f"Session '{session_id}' was already ended at "
                    f"{self._ended_sessions[session_id]}. Use a new session ID."
                )
            memory = CallMemory(
                session_id=session_id,
                max_recent_events=max_events or self._default_max_events,
            )
            self._sessions[session_id] = memory
            return memory

    def get_or_create_session(self, session_id: str, max_events: Optional[int] = None) -> CallMemory:
        """Retrieves an existing session or initializes a new one on-demand."""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = CallMemory(
                    session_id=session_id,
                    max_recent_events=max_events or self._default_max_events,
                )
            return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[CallMemory]:
        """Fetches active session memory without side-effects."""
        with self._lock:
            return self._sessions.get(session_id)

    def update_session(
        self,
        session_id: str,
        current_state: Optional[str] = None,
        risk_score: Optional[float] = None,
        running_summary: Optional[str] = None,
        active_claim: Optional[str] = None,
        signals: Optional[Dict[str, Any]] = None,
    ) -> Optional[CallMemory]:
        """
        Imperatively updates memory fields for a session.
        Returns None if session does not exist (no implicit creation).
        """
        with self._lock:
            memory = self._sessions.get(session_id)
            if memory is None:
                return None
            if current_state is not None:
                memory.current_state = current_state
            if risk_score is not None:
                memory.risk_score = max(0.0, min(1.0, float(risk_score)))
            if running_summary and running_summary.strip():
                memory.running_summary = running_summary.strip()
            if active_claim is not None:
                memory.active_claim = active_claim
            if signals:
                memory.signals.update(signals)
            memory.updated_at = time.time()
            return memory

    def end_session(self, session_id: str) -> Optional[CallMemory]:
        """
        Terminates a session and purges active memory.
        Leaves a tombstone so the session ID cannot be accidentally reused.
        """
        with self._lock:
            memory = self._sessions.pop(session_id, None)
            if memory is not None:
                self._ended_sessions[session_id] = time.time()
            return memory

    # ──────────────────────────────────────────────────────────────────────────
    # Introspection
    # ──────────────────────────────────────────────────────────────────────────

    def list_active_session_ids(self) -> List[str]:
        """Returns all currently active session identifiers."""
        with self._lock:
            return list(self._sessions.keys())

    def active_session_count(self) -> int:
        """Returns count of active sessions."""
        with self._lock:
            return len(self._sessions)

    def session_stats(self) -> Dict[str, Any]:
        """Returns runtime statistics for monitoring / debugging."""
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "ended_sessions": len(self._ended_sessions),
                "active_session_ids": list(self._sessions.keys()),
                "total_events": sum(m.event_counter for m in self._sessions.values()),
            }


# Global singleton instance for Layer 3 memory
session_manager = SessionManager()
