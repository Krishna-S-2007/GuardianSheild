"""Integration tests for Layer 3 Service and Telemetry processing."""

import pytest
from app.layer3.schemas import UserContext, TelemetryEvent, SecurityState
from app.layer3.session import SessionManager
from app.layer3.service import Layer3Service
from app.services.session_service import SessionService


@pytest.mark.asyncio
async def test_process_telemetry_flow_with_mock_reasoning():
    mem_mgr = SessionManager()
    session_svc = SessionService()
    service = Layer3Service(memory_manager=mem_mgr, backend_session_service=session_svc)

    user = UserContext(user_id="USER-99")

    # Step 1: Normal statement
    t1 = TelemetryEvent(transcript_delta="Good morning, this is Rajesh from Finance.", deepfake_score=0.1)
    res1 = await service.process_telemetry("CALL-TEST-1", t1, user)
    assert res1.current_state in ["NORMAL", "AUTHORITY_IMPERSONATION"]

    # Step 2: Impersonation and urgency
    t2 = TelemetryEvent(transcript_delta="I am calling from the bank. This is urgent and confidential.", deepfake_score=0.4)
    res2 = await service.process_telemetry("CALL-TEST-1", t2, user)
    assert res2.risk_score > 0.3
    assert "urgent" in res2.running_summary.lower() or "authority" in res2.running_summary.lower()

    # Step 3: Critical credential request with high deepfake score
    t3 = TelemetryEvent(transcript_delta="Give me the OTP now to prevent account suspension.", deepfake_score=0.88, is_critical=True)
    res3 = await service.process_telemetry("CALL-TEST-1", t3, user)
    assert res3.risk_score >= 0.8
    assert res3.action_required in ["OUT_OF_BAND_VERIFY", "TERMINATE", "STEP_UP_AUTH"]

    # Verify that memory preserved the accumulated state
    mem = mem_mgr.get_session("CALL-TEST-1")
    assert mem.event_counter == 3
    assert len(mem.recent_events) == 3


@pytest.mark.asyncio
async def test_reasoning_failure_preserves_last_valid_state():
    mem_mgr = SessionManager()
    
    # Engine that succeeds on call 1, then crashes on call 2
    attempts = {"count": 0}
    def flaky_engine(ctx):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return SecurityState(
                current_state="ISOLATION",
                risk_score=0.78,
                running_summary="Valid threat summary established.",
                active_claim="Fake Police Officer",
            )
        raise TimeoutError("Gemini API connection timed out")

    service = Layer3Service(memory_manager=mem_mgr, reasoning_engine=flaky_engine)
    user = UserContext(user_id="USER-ERR")

    # 1. First event succeeds
    r1 = await service.process_telemetry("CALL-FAILOVER", TelemetryEvent(transcript_delta="Event 1"), user)
    assert r1.current_state == "ISOLATION"
    assert r1.risk_score == 0.78

    # 2. Second event triggers timeout
    r2 = await service.process_telemetry("CALL-FAILOVER", TelemetryEvent(transcript_delta="Event 2"), user)
    
    # Crucial guarantee: state was NOT wiped or set to empty defaults
    assert r2.current_state == "ISOLATION"
    assert r2.risk_score == 0.78
    assert r2.running_summary == "Valid threat summary established."
    assert "Fail-Safe Mode" in r2.explanation

    mem = mem_mgr.get_session("CALL-FAILOVER")
    assert mem.current_state == "ISOLATION"
    assert mem.running_summary == "Valid threat summary established."
