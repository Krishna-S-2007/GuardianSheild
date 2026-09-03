"""Thread-safe session manager ensuring strict multi-call isolation."""

from __future__ import annotations
import threading
from typing import Dict, List, Optional
from .memory import CallMemory


class SessionManager:
    """Manages active call memories with concurrency safety and strict isolation."""

    def __init__(self, default_max_events: int = 8):
        self._sessions: Dict[str, CallMemory] = {}
        self._lock = threading.Lock()
        self._default_max_events = default_max_events

    def create_session(self, session_id: str, max_events: Optional[int] = None) -> CallMemory:
        """Explicitly initializes a new call memory session."""
        with self._lock:
            if session_id in self._sessions:
                raise ValueError(f"Session '{session_id}' is already active.")
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

    def end_session(self, session_id: str) -> Optional[CallMemory]:
        """Terminates session and purges active memory."""
        with self._lock:
            return self._sessions.pop(session_id, None)

    def list_active_session_ids(self) -> List[str]:
        """Returns all currently active session identifiers."""
        with self._lock:
            return list(self._sessions.keys())

    def active_session_count(self) -> int:
        """Returns count of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global singleton instance for Layer 3 memory
session_manager = SessionManager()
