"""
Comprehensive tests for Layer 3 Session lifecycle, update_session(),
tombstone guard, session_stats(), memory.clear(), service.end_session(),
and all 8 test categories required by TEAM_MEMBER_3_LAYER3_PERSON_B_MEMORY.md
"""

import pytest
import time
from app.layer3.schemas import (
    TelemetryEvent, SecurityState, UserContext, TrustedContact
)
from app.layer3.memory import CallMemory
from app.layer3.session import SessionManager
from app.layer3.context import build_reasoning_context
from app.layer3.service import Layer3Service
from app.layer3 import (
    process_telemetry, end_session, layer3_session_stats,
    mock_reasoning_engine
)
from app.services.session_service import SessionService


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 1: State Persistence
# ─────────────────────────────────────────────────────────────────────────────

def test_state_persists_across_events():
    """State accumulated from event N must carry into event N+1."""
    mem = CallMemory("PERSIST-01")

    state_a = SecurityState(
        current_state="AUTHORITY_IMPERSONATION",
        risk_score=0.55,
        running_summary="Caller claims to be bank manager.",
        active_claim="Bank Manager Impersonation",
        signals={"authority": 0.8},
    )
    mem.update_from_security_state(state_a)
    assert mem.current_state == "AUTHORITY_IMPERSONATION"
    assert mem.active_claim == "Bank Manager Impersonation"

    # Second update must MERGE, not replace
    state_b = SecurityState(
        current_state="ISOLATION",
        risk_score=0.72,
        running_summary="Caller now demands secrecy.",
        signals={"isolation": 0.9},
    )
    mem.update_from_security_state(state_b)
    assert mem.current_state == "ISOLATION"
    assert mem.risk_score == 0.72
    # authority signal must be preserved from previous update
    assert mem.signals["authority"] == 0.8
    assert mem.signals["isolation"] == 0.9


def test_risk_score_never_decreases_below_clamping():
    """Risk score clamped to [0.0, 1.0] regardless of LLM output."""
    mem = CallMemory("CLAMP-01")
    mem.update_from_security_state(SecurityState(current_state="NORMAL", risk_score=2.99))
    assert mem.risk_score == 1.0
    mem.update_from_security_state(SecurityState(current_state="NORMAL", risk_score=-0.5))
    assert mem.risk_score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 2: Bounded Recent Events (already exists in test_memory.py)
# Adding complementary edge cases
# ─────────────────────────────────────────────────────────────────────────────

def test_event_counter_is_monotonic():
    """event_counter must always increase; recent_events is bounded."""
    mem = CallMemory("COUNTER-01", max_recent_events=3)
    for i in range(7):
        mem.add_telemetry_event(TelemetryEvent(transcript_delta=f"Packet {i}"))
    assert mem.event_counter == 7
    assert len(mem.recent_events) == 3
    assert mem.recent_events[-1]["event_seq"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 3: Running Summary Preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_running_summary_survives_empty_update():
    """Empty running_summary from LLM must NOT overwrite previous valid summary."""
    mem = CallMemory("SUMMARY-01")
    mem.update_from_security_state(SecurityState(
        current_state="URGENCY",
        risk_score=0.7,
        running_summary="Caller is urgently requesting funds.",
    ))
    mem.update_from_security_state(SecurityState(
        current_state="URGENCY",
        risk_score=0.75,
        running_summary="",  # LLM returned empty
    ))
    assert mem.running_summary == "Caller is urgently requesting funds."

def test_running_summary_survives_whitespace_only():
    """Whitespace-only summary also must not replace valid summary."""
    mem = CallMemory("SUMMARY-02")
    mem.update_from_security_state(SecurityState(
        current_state="ISOLATION",
        risk_score=0.6,
        running_summary="Important context saved.",
    ))
    mem.update_from_security_state(SecurityState(
        current_state="ISOLATION",
        risk_score=0.65,
        running_summary="   \t\n  ",
    ))
    assert mem.running_summary == "Important context saved."


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 4: Simultaneous Sessions (isolation)
# ─────────────────────────────────────────────────────────────────────────────

def test_simultaneous_sessions_never_share_state():
    """Sessions CALL-A and CALL-B must never see each other's state."""
    mgr = SessionManager()
    a = mgr.create_session("CALL-A")
    b = mgr.create_session("CALL-B")

    a.update_from_security_state(SecurityState(
        current_state="BLOCKED", risk_score=0.99,
        running_summary="Critical threat in A."
    ))
    b.update_from_security_state(SecurityState(
        current_state="NORMAL", risk_score=0.05,
        running_summary="Routine call in B."
    ))

    assert mgr.get_session("CALL-A").current_state == "BLOCKED"
    assert mgr.get_session("CALL-B").current_state == "NORMAL"
    assert mgr.get_session("CALL-A").risk_score == 0.99
    assert mgr.get_session("CALL-B").risk_score == 0.05


def test_session_count_accurate_during_lifecycle():
    """active_session_count must track creates and ends exactly."""
    mgr = SessionManager()
    assert mgr.active_session_count() == 0

    mgr.create_session("S1")
    mgr.create_session("S2")
    mgr.create_session("S3")
    assert mgr.active_session_count() == 3

    mgr.end_session("S2")
    assert mgr.active_session_count() == 2
    assert mgr.get_session("S2") is None
    assert mgr.get_session("S1") is not None


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 5: Ended-Session Rejection (NEW — tombstone guard)
# ─────────────────────────────────────────────────────────────────────────────

def test_ended_session_cannot_be_recreated():
    """After end_session(), the same session_id must be tombstoned."""
    mgr = SessionManager()
    mgr.create_session("TOMB-01")
    mgr.end_session("TOMB-01")

    with pytest.raises(ValueError, match="already ended"):
        mgr.create_session("TOMB-01")


def test_get_session_returns_none_after_end():
    """get_session must return None once a session is ended."""
    mgr = SessionManager()
    mgr.create_session("ENDED-01")
    mgr.end_session("ENDED-01")
    assert mgr.get_session("ENDED-01") is None


def test_end_session_returns_memory_for_audit():
    """end_session must return the CallMemory for post-call logging."""
    mgr = SessionManager()
    mem = mgr.create_session("AUDIT-01")
    mem.add_telemetry_event(TelemetryEvent(transcript_delta="Test event"))

    returned = mgr.end_session("AUDIT-01")
    assert returned is not None
    assert returned.session_id == "AUDIT-01"
    assert returned.event_counter == 1


def test_end_nonexistent_session_returns_none():
    """Ending a session that was never created returns None silently."""
    mgr = SessionManager()
    result = mgr.end_session("DOES-NOT-EXIST")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 5b: update_session() (new method)
# ─────────────────────────────────────────────────────────────────────────────

def test_update_session_modifies_fields():
    """update_session() must imperatively update specific fields only."""
    mgr = SessionManager()
    mgr.create_session("UPD-01")

    result = mgr.update_session(
        "UPD-01",
        current_state="CREDENTIAL_EXTRACTION",
        risk_score=0.91,
        running_summary="OTP requested by caller.",
        active_claim="Fake bank employee",
        signals={"credential_request": 0.99},
    )
    assert result is not None
    assert result.current_state == "CREDENTIAL_EXTRACTION"
    assert result.risk_score == 0.91
    assert result.running_summary == "OTP requested by caller."
    assert result.active_claim == "Fake bank employee"
    assert result.signals["credential_request"] == 0.99


def test_update_session_partial_update():
    """update_session() with only some fields must leave others unchanged."""
    mgr = SessionManager()
    s = mgr.create_session("UPD-02")
    s.active_claim = "Existing claim"
    s.current_state = "URGENCY"

    mgr.update_session("UPD-02", risk_score=0.80)

    updated = mgr.get_session("UPD-02")
    assert updated.risk_score == 0.80
    assert updated.current_state == "URGENCY"       # unchanged
    assert updated.active_claim == "Existing claim" # unchanged


def test_update_nonexistent_session_returns_none():
    """update_session on unknown session_id must return None silently."""
    mgr = SessionManager()
    result = mgr.update_session("NO-SUCH-SESSION", risk_score=0.5)
    assert result is None


def test_update_session_clamps_risk_score():
    """update_session must clamp risk_score to [0.0, 1.0]."""
    mgr = SessionManager()
    mgr.create_session("CLAMP-02")
    mgr.update_session("CLAMP-02", risk_score=5.0)
    assert mgr.get_session("CLAMP-02").risk_score == 1.0

    mgr.update_session("CLAMP-02", risk_score=-2.0)
    assert mgr.get_session("CLAMP-02").risk_score == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 5c: session_stats()
# ─────────────────────────────────────────────────────────────────────────────

def test_session_stats_structure():
    """session_stats() must return required monitoring fields."""
    mgr = SessionManager()
    mgr.create_session("STATS-01")
    mgr.create_session("STATS-02")
    mgr.end_session("STATS-01")

    stats = mgr.session_stats()
    assert stats["active_sessions"] == 1
    assert stats["ended_sessions"] == 1
    assert "STATS-02" in stats["active_session_ids"]
    assert "total_events" in stats


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 5d: memory.clear()
# ─────────────────────────────────────────────────────────────────────────────

def test_memory_clear_resets_runtime_fields():
    """clear() must reset state, signals, and event window but preserve audit fields."""
    mem = CallMemory("CLEAR-01", max_recent_events=5)

    # Populate with threat state
    for i in range(3):
        mem.add_telemetry_event(TelemetryEvent(transcript_delta=f"Event {i}", deepfake_score=0.8))
    mem.update_from_security_state(SecurityState(
        current_state="BLOCKED", risk_score=0.99,
        running_summary="Critical fraud call.",
        signals={"fear": 0.9, "urgency": 0.95},
    ))

    assert mem.current_state == "BLOCKED"
    counter_before = mem.event_counter  # must survive clear

    mem.clear()

    assert mem.current_state == "NORMAL"
    assert mem.risk_score == 0.0
    assert mem.running_summary == "Session cleared."
    assert mem.active_claim is None
    assert len(mem.recent_events) == 0
    assert len(mem.deepfake_score_history) == 0
    assert all(v == 0.0 for v in mem.signals.values())
    # audit field preserved
    assert mem.event_counter == counter_before
    assert mem.session_id == "CLEAR-01"


def test_memory_get_summary_dict():
    """get_summary_dict() must return a compact monitoring snapshot."""
    mem = CallMemory("SUMMARY-DICT-01")
    mem.add_telemetry_event(TelemetryEvent(transcript_delta="Hello", deepfake_score=0.3))
    mem.update_from_security_state(SecurityState(
        current_state="SUSPICIOUS", risk_score=0.4,
        running_summary="Mild anomaly.",
        active_claim="Unknown claim",
    ))

    summary = mem.get_summary_dict()
    assert summary["session_id"] == "SUMMARY-DICT-01"
    assert summary["current_state"] == "SUSPICIOUS"
    assert summary["risk_score"] == 0.4
    assert summary["active_claim"] == "Unknown claim"
    assert summary["total_events"] == 1
    assert summary["avg_deepfake_score"] == 0.3
    assert "duration_seconds" in summary


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 6: Reasoning Engine Failure (additional coverage)
# (core tests already exist in test_service.py; adding end_session variant)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_service_end_session_returns_true_for_known_session():
    """Service.end_session() must return True and clear layer3 memory."""
    mgr = SessionManager()
    svc = Layer3Service(memory_manager=mgr, backend_session_service=SessionService())
    user = UserContext(user_id="U-END")

    await svc.process_telemetry(
        "END-SVC-01",
        TelemetryEvent(transcript_delta="Hello there."),
        user
    )
    assert mgr.get_session("END-SVC-01") is not None

    result = await svc.end_session("END-SVC-01")
    assert result is True
    assert mgr.get_session("END-SVC-01") is None


@pytest.mark.asyncio
async def test_service_end_session_returns_false_for_unknown():
    """Service.end_session() on unknown session must return False."""
    svc = Layer3Service(
        memory_manager=SessionManager(),
        backend_session_service=SessionService()
    )
    result = await svc.end_session("GHOST-SESSION")
    assert result is False


@pytest.mark.asyncio
async def test_service_session_stats_reflects_active_sessions():
    """session_stats() must count running sessions accurately."""
    mgr = SessionManager()
    svc = Layer3Service(memory_manager=mgr, backend_session_service=SessionService())
    user = UserContext(user_id="U-STATS")

    await svc.process_telemetry("STAT-A", TelemetryEvent(transcript_delta="A"), user)
    await svc.process_telemetry("STAT-B", TelemetryEvent(transcript_delta="B"), user)

    stats = svc.session_stats()
    assert stats["active_sessions"] == 2
    assert "STAT-A" in stats["active_session_ids"]
    assert "STAT-B" in stats["active_session_ids"]

    await svc.end_session("STAT-A")
    stats2 = svc.session_stats()
    assert stats2["active_sessions"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 7: Context Construction (additional)
# ─────────────────────────────────────────────────────────────────────────────

def test_context_includes_all_required_keys():
    """build_reasoning_context must include user_context, call_memory, new_telemetry."""
    user = UserContext(
        user_id="CTX-USER-01",
        user_name="Arun Sharma",
        role="CFO",
        trusted_contacts=[
            TrustedContact(name="Krishna", relationship="son", device_id="DEV-K")
        ],
    )
    mem = CallMemory("CTX-MEM-01", max_recent_events=5)
    mem.current_state = "FINANCIAL_PRESSURE"
    mem.risk_score = 0.78
    mem.running_summary = "Caller demands funds."

    tel = TelemetryEvent(
        transcript_delta="Transfer 10 lakhs to this account.",
        deepfake_score=0.65,
        is_critical=True,
        speaker_id="unknown_caller",
    )

    ctx = build_reasoning_context(user, mem, tel)

    # user_context keys
    assert ctx["user_context"]["user_id"] == "CTX-USER-01"
    assert ctx["user_context"]["role"] == "CFO"
    assert ctx["user_context"]["transaction_limit"] == 50000.0
    assert len(ctx["user_context"]["trusted_contacts"]) == 1
    assert ctx["user_context"]["trusted_contacts"][0]["name"] == "Krishna"

    # call_memory keys
    assert ctx["call_memory"]["current_state"] == "FINANCIAL_PRESSURE"
    assert ctx["call_memory"]["risk_score"] == 0.78
    assert ctx["call_memory"]["running_summary"] == "Caller demands funds."

    # new_telemetry keys
    assert ctx["new_telemetry"]["transcript_delta"] == "Transfer 10 lakhs to this account."
    assert ctx["new_telemetry"]["deepfake_score"] == 0.65
    assert ctx["new_telemetry"]["is_critical"] is True
    assert ctx["new_telemetry"]["speaker_id"] == "unknown_caller"


def test_context_does_not_expose_unbounded_events():
    """Context must use bounded recent_events, not full transcript history."""
    mem = CallMemory("CTX-BOUND-01", max_recent_events=3)
    user = UserContext(user_id="U")
    for i in range(20):
        mem.add_telemetry_event(TelemetryEvent(transcript_delta=f"Event {i}"))

    tel = TelemetryEvent(transcript_delta="Final event")
    ctx = build_reasoning_context(user, mem, tel)

    # Only the bounded window (3) should be in context
    assert len(ctx["call_memory"]["recent_events"]) <= 3


# ─────────────────────────────────────────────────────────────────────────────
# MD Spec Test Category 8: Real/Mock Reasoning Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_mock_reasoning_engine_deterministic_for_otp():
    """Mock engine must flag OTP keywords with appropriate action."""
    ctx = {
        "new_telemetry": {
            "transcript_delta": "Please share your OTP now",
            "deepfake_score": 0.75,
            "is_critical": True,
        },
        "call_memory": {
            "current_state": "AUTHORITY_IMPERSONATION",
            "risk_score": 0.55,
            "running_summary": "Caller claims bank authority.",
            "signals": {"authority": 0.8},
            "active_claim": "Bank Manager",
        },
        "user_context": {},
    }
    result = mock_reasoning_engine(ctx)
    assert result.action_required in ["OUT_OF_BAND_VERIFY", "STEP_UP_AUTH", "TERMINATE"]
    assert result.risk_score >= 0.70
    assert result.signals.get("credential_request", 0) >= 0.9


def test_mock_reasoning_engine_normal_for_legit_call():
    """Mock engine must NOT flag a normal business conversation."""
    ctx = {
        "new_telemetry": {
            "transcript_delta": "Let's schedule the board meeting for next Tuesday.",
            "deepfake_score": 0.05,
            "is_critical": False,
        },
        "call_memory": {
            "current_state": "NORMAL",
            "risk_score": 0.0,
            "running_summary": "Call initiated.",
            "signals": {},
            "active_claim": None,
        },
        "user_context": {},
    }
    result = mock_reasoning_engine(ctx)
    assert result.current_state == "NORMAL"
    assert result.risk_score < 0.40
    assert result.action_required is None


def test_mock_reasoning_engine_terminate_on_high_deepfake():
    """High deepfake score (>=0.80) combined with existing risk must produce TERMINATE."""
    ctx = {
        "new_telemetry": {
            "transcript_delta": "Give me your account password immediately.",
            "deepfake_score": 0.91,
            "is_critical": True,
        },
        "call_memory": {
            "current_state": "ISOLATION",
            "risk_score": 0.75,
            "running_summary": "Caller demanding credentials with isolation tactics.",
            "signals": {"authority": 0.8, "isolation": 0.9},
            "active_claim": "Fake CBI",
        },
        "user_context": {},
    }
    result = mock_reasoning_engine(ctx)
    assert result.current_state == "BLOCKED"
    assert result.action_required == "TERMINATE"
    assert result.risk_score >= 0.96


@pytest.mark.asyncio
async def test_real_service_with_injected_mock_engine():
    """Full pipeline: Layer3Service with mock engine must produce valid SecurityState."""
    mgr = SessionManager()
    svc = Layer3Service(
        memory_manager=mgr,
        backend_session_service=SessionService(),
        reasoning_engine=mock_reasoning_engine,
    )

    user = UserContext(
        user_id="MOCK-INTEGRATION",
        user_name="Test Executive",
        trusted_contacts=[
            TrustedContact(name="Trusted One", relationship="spouse", device_id="DEV-T1")
        ],
    )

    # Simulate a 3-step attack progression
    steps = [
        ("I am calling from the bank regarding your account.", 0.25, False),
        ("This is urgent. Do not disconnect the call.", 0.60, False),
        ("Confirm the OTP I sent to prevent account freeze.", 0.82, True),
    ]

    last_result = None
    for transcript, df_score, critical in steps:
        last_result = await svc.process_telemetry(
            "INTEGRATION-01",
            TelemetryEvent(transcript_delta=transcript, deepfake_score=df_score, is_critical=critical),
            user,
        )

    mem = mgr.get_session("INTEGRATION-01")
    assert mem.event_counter == 3
    assert last_result.risk_score >= 0.80
    assert last_result.action_required in ["OUT_OF_BAND_VERIFY", "TERMINATE"]

    # End session cleanly
    result = await svc.end_session("INTEGRATION-01")
    assert result is True
    assert mgr.get_session("INTEGRATION-01") is None
