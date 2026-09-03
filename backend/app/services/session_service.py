import asyncio
import time
import logging
import uuid
from typing import Dict, List, Optional
from app.models.session import CallSession, CallStatus, DeviceProfile, AttackState

logger = logging.getLogger("guardianshield.session")


class SessionService:
    """Manages active call sessions and device registry in-memory."""

    def __init__(self):
        # Maps session_id -> CallSession
        self._sessions: Dict[str, CallSession] = {}
        # Maps device_id -> DeviceProfile
        self._devices: Dict[str, DeviceProfile] = {}
        # Maps device_id -> active session_id
        self._device_active_sessions: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    # --- Device Profile Operations ---

    async def register_device(self, profile: DeviceProfile) -> DeviceProfile:
        async with self._lock:
            profile.online = True
            profile.last_seen = time.time()
            self._devices[profile.device_id] = profile
            logger.info(f"Registered device profile: {profile.device_id} ({profile.user_name})")
            return profile

    async def get_device(self, device_id: str) -> Optional[DeviceProfile]:
        async with self._lock:
            return self._devices.get(device_id)

    async def get_all_devices(self) -> List[DeviceProfile]:
        async with self._lock:
            return list(self._devices.values())

    async def update_device_presence(self, device_id: str, online: bool) -> None:
        async with self._lock:
            if device_id in self._devices:
                self._devices[device_id].online = online
                self._devices[device_id].last_seen = time.time()

    # --- Session Operations ---

    async def create_session(
        self,
        caller_device_id: str,
        callee_device_id: str,
        custom_session_id: Optional[str] = None
    ) -> CallSession:
        async with self._lock:
            session_id = custom_session_id or f"CALL-{uuid.uuid4().hex[:8].upper()}"
            session = CallSession(
                session_id=session_id,
                caller_device_id=caller_device_id,
                callee_device_id=callee_device_id,
                status=CallStatus.RINGING,
                start_time=time.time(),
                current_state=AttackState.NORMAL,
                risk_score=0.0,
                running_summary="Call session initiated."
            )
            self._sessions[session_id] = session
            self._device_active_sessions[caller_device_id] = session_id
            self._device_active_sessions[callee_device_id] = session_id
            logger.info(f"Created session {session_id} between {caller_device_id} and {callee_device_id}")
            return session

    async def get_session(self, session_id: str) -> Optional[CallSession]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def get_active_session_for_device(self, device_id: str) -> Optional[CallSession]:
        async with self._lock:
            session_id = self._device_active_sessions.get(device_id)
            if session_id and session_id in self._sessions:
                return self._sessions[session_id]
            return None

    async def update_session_status(self, session_id: str, status: CallStatus) -> Optional[CallSession]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = status
                session.updated_at = time.time()
                if status in (CallStatus.ENDED, CallStatus.REJECTED):
                    session.end_time = time.time()
                    # Clear active session mapping
                    if self._device_active_sessions.get(session.caller_device_id) == session_id:
                        del self._device_active_sessions[session.caller_device_id]
                    if self._device_active_sessions.get(session.callee_device_id) == session_id:
                        del self._device_active_sessions[session.callee_device_id]
                return session
            return None

    async def update_session_state(
        self,
        session_id: str,
        current_state: AttackState,
        risk_score: float,
        summary: str,
        signals: Dict[str, float],
        active_claim: Optional[str] = None,
        new_event: Optional[str] = None,
        deepfake_score: Optional[float] = None
    ) -> Optional[CallSession]:
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            session.current_state = current_state
            session.risk_score = max(0.0, min(1.0, risk_score))
            session.running_summary = summary
            session.signals = signals
            if active_claim:
                session.active_claim = active_claim

            if new_event:
                session.recent_events.append(new_event)
                # Keep only rolling window of last 5 recent events (PRD Section 24.2)
                if len(session.recent_events) > 5:
                    session.recent_events = session.recent_events[-5:]

            if deepfake_score is not None:
                session.deepfake_score_history.append(deepfake_score)

            session.telemetry_count += 1
            session.updated_at = time.time()
            return session

    async def get_active_sessions_count(self) -> int:
        async with self._lock:
            return sum(1 for s in self._sessions.values() if s.status == CallStatus.CONNECTED or s.status == CallStatus.RINGING)

    async def get_all_active_sessions(self) -> List[CallSession]:
        async with self._lock:
            return [s for s in self._sessions.values() if s.status in (CallStatus.RINGING, CallStatus.CONNECTED)]


session_service = SessionService()
