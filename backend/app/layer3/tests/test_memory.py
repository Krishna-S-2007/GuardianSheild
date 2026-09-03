"""Unit tests for Layer 3 CallMemory, Bounded Events, and Session Isolation."""

import pytest
from app.layer3.schemas import TelemetryEvent, SecurityState, UserContext, TrustedContact
from app.layer3.memory import CallMemory
from app.layer3.session import SessionManager
from app.layer3.context import build_reasoning_context


def test_call_memory_initialization():
    mem = CallMemory(session_id="CALL-001", max_recent_events=5)
    assert mem.session_id == "CALL-001"
    assert mem.current_state == "NORMAL"
    assert mem.risk_score == 0.0
    assert mem.running_summary == "Call initiated."
    assert len(mem.recent_events) == 0
    assert mem.event_counter == 0


def test_bounded_recent_events():
    mem = CallMemory(session_id="CALL-BOUNDED", max_recent_events=4)

    for i in range(1, 10):
        event = TelemetryEvent(
            transcript_delta=f"Spoken phrase {i}",
            deepfake_score=0.1 * i,
            speaker_id="caller",
        )
        mem.add_telemetry_event(event)

    # Max length is 4, so only the last 4 events remain in recent_events
    assert len(mem.recent_events) == 4
    assert mem.event_counter == 9

    # Verify event sequences retained
    retained_seqs = [e["event_seq"] for e in mem.recent_events]
    assert retained_seqs == [6, 7, 8, 9]

    retained_texts = [e["transcript_delta"] for e in mem.recent_events]
    assert retained_texts == [
        "Spoken phrase 6",
        "Spoken phrase 7",
        "Spoken phrase 8",
        "Spoken phrase 9",
    ]


def test_update_from_security_state():
    mem = CallMemory(session_id="CALL-STATE", max_recent_events=5)
    state = SecurityState(
        current_state="ISOLATION",
        risk_score=0.82,
        running_summary="Caller demanding OTP under threat of arrest.",
        active_claim="CBI Officer Impersonation",
        signals={"fear": 0.9, "urgency": 0.95},
        action_required="OUT_OF_BAND_VERIFY",
    )
    mem.update_from_security_state(state)

    assert mem.current_state == "ISOLATION"
    assert mem.risk_score == 0.82
    assert mem.running_summary == "Caller demanding OTP under threat of arrest."
    assert mem.active_claim == "CBI Officer Impersonation"
    assert mem.signals["fear"] == 0.9

    # Ensure empty running summary does NOT wipe previous valid summary
    empty_state = SecurityState(
        current_state="ISOLATION",
        risk_score=0.85,
        running_summary="",
    )
    mem.update_from_security_state(empty_state)
    assert mem.running_summary == "Caller demanding OTP under threat of arrest."


def test_multi_session_isolation():
    manager = SessionManager()
    s1 = manager.create_session("SESSION-ALPHA")
    s2 = manager.create_session("SESSION-BETA")

    s1.running_summary = "Alpha: Suspected bank impersonation"
    s2.running_summary = "Beta: Routine executive conversation"

    assert manager.get_session("SESSION-ALPHA").running_summary == "Alpha: Suspected bank impersonation"
    assert manager.get_session("SESSION-BETA").running_summary == "Beta: Routine executive conversation"

    # End session Alpha
    ended = manager.end_session("SESSION-ALPHA")
    assert ended.session_id == "SESSION-ALPHA"
    assert manager.get_session("SESSION-ALPHA") is None
    assert manager.get_session("SESSION-BETA") is not None


def test_duplicate_session_rejection():
    manager = SessionManager()
    manager.create_session("SESSION-DUP")
    with pytest.raises(ValueError, match="already active"):
        manager.create_session("SESSION-DUP")


def test_context_construction():
    user = UserContext(
        user_id="EXEC-01",
        user_name="Rajesh Sharma",
        role="CFO",
        trusted_contacts=[
            TrustedContact(name="Anil", relationship="Deputy CFO", phone_number="+919876543210")
        ],
    )
    mem = CallMemory(session_id="CALL-CTX", max_recent_events=5)
    mem.current_state = "SUSPICIOUS"
    mem.risk_score = 0.6
    mem.running_summary = "Caller claims to be customs official."

    tel = TelemetryEvent(
        transcript_delta="Confirm your UPI PIN immediately.",
        deepfake_score=0.85,
        is_critical=True,
    )

    ctx = build_reasoning_context(user, mem, tel)

    assert ctx["user_context"]["user_id"] == "EXEC-01"
    assert len(ctx["user_context"]["trusted_contacts"]) == 1
    assert ctx["call_memory"]["current_state"] == "SUSPICIOUS"
    assert ctx["call_memory"]["risk_score"] == 0.6
    assert ctx["new_telemetry"]["transcript_delta"] == "Confirm your UPI PIN immediately."
    assert ctx["new_telemetry"]["deepfake_score"] == 0.85
    assert ctx["new_telemetry"]["is_critical"] is True
