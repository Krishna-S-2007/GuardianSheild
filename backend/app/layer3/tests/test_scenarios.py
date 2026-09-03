"""End-to-end multi-scenario simulation tests for GuardianShield Layer 3."""

import pytest
from app.layer3.schemas import UserContext, TrustedContact, TelemetryEvent, SecurityState
from app.layer3.session import SessionManager
from app.layer3.service import Layer3Service
from app.services.session_service import SessionService


@pytest.fixture
def test_setup():
    mem_mgr = SessionManager(default_max_events=6)
    sess_svc = SessionService()
    service = Layer3Service(memory_manager=mem_mgr, backend_session_service=sess_svc)
    user_context = UserContext(
        user_id="EXEC-777",
        user_name="Vikram Malhotra",
        role="Treasury Director",
        transaction_limit=100000.0,
        trusted_contacts=[
            TrustedContact(name="Ananya", relationship="Deputy Director", phone_number="+919876500001"),
            TrustedContact(name="Rohit", relationship="Security Operations", phone_number="+919876500002"),
        ]
    )
    return service, mem_mgr, user_context


@pytest.mark.asyncio
async def test_scenario_1_deepfake_cfo_impersonation(test_setup):
    """
    Scenario 1: High-confidence synthetic voice + Urgent confidential wire transfer request.
    Progression: NORMAL -> AUTHORITY_IMPERSONATION -> FINANCIAL_PRESSURE / BLOCKED -> TERMINATE
    """
    service, mem_mgr, user_ctx = test_setup
    session_id = "SCENARIO-1-CFO-FRAUD"

    # Step 1: Greeting & CFO Claim (Low deepfake score initially)
    t1 = TelemetryEvent(
        transcript_delta="Vikram, this is the CFO calling. We have an emergency.",
        deepfake_score=0.40,
        speaker_id="caller",
    )
    r1 = await service.process_telemetry(session_id, t1, user_ctx)
    assert r1.current_state in ["NORMAL", "AUTHORITY_IMPERSONATION"]

    # Step 2: Secrecy and Urgency applied
    t2 = TelemetryEvent(
        transcript_delta="Keep this strictly confidential. Do not disconnect the call.",
        deepfake_score=0.65,
        speaker_id="caller",
    )
    r2 = await service.process_telemetry(session_id, t2, user_ctx)
    assert r2.risk_score >= 0.50
    assert r2.signals.get("urgency", 0.0) > 0.5

    # Step 3: Urgent wire transfer + high synthetic voice score
    t3 = TelemetryEvent(
        transcript_delta="Authorize the urgent transfer of 45 Lakhs to the vendor account immediately.",
        deepfake_score=0.92,
        is_critical=True,
        speaker_id="caller",
    )
    r3 = await service.process_telemetry(session_id, t3, user_ctx)
    assert r3.current_state in ["ISOLATION", "BLOCKED", "FINANCIAL_PRESSURE"]
    assert r3.risk_score >= 0.85
    assert r3.action_required in ["OUT_OF_BAND_VERIFY", "TERMINATE"]

    # Verify context durability
    mem = mem_mgr.get_session(session_id)
    assert "CFO" in mem.active_claim or "authority" in mem.running_summary.lower()
    assert mem.event_counter == 3


@pytest.mark.asyncio
async def test_scenario_2_digital_arrest_vishing(test_setup):
    """
    Scenario 2: Digital Arrest scam involving fake law enforcement (CBI/Customs/Police)
    Progression: AUTHORITY_IMPERSONATION -> FEAR/ISOLATION -> OUT_OF_BAND_VERIFY
    """
    service, mem_mgr, user_ctx = test_setup
    session_id = "SCENARIO-2-DIGITAL-ARREST"

    # Step 1: Fake Police / Customs Official
    t1 = TelemetryEvent(
        transcript_delta="This is Officer Sharma from Mumbai Customs. Your parcel has contraband.",
        deepfake_score=0.35,
    )
    r1 = await service.process_telemetry(session_id, t1, user_ctx)
    assert "Customs" in r1.active_claim or r1.signals.get("authority", 0.0) > 0.5

    # Step 2: Threat of arrest and isolation
    t2 = TelemetryEvent(
        transcript_delta="You are placed under digital arrest. Do not tell anyone or you will be jailed.",
        deepfake_score=0.55,
    )
    r2 = await service.process_telemetry(session_id, t2, user_ctx)
    assert r2.risk_score > 0.5

    # Step 3: Demanding OTP / Verification PIN
    t3 = TelemetryEvent(
        transcript_delta="Share your banking OTP immediately for verification and clearance.",
        deepfake_score=0.75,
        is_critical=True,
    )
    r3 = await service.process_telemetry(session_id, t3, user_ctx)
    assert r3.risk_score >= 0.70
    assert r3.action_required in ["OUT_OF_BAND_VERIFY", "STEP_UP_AUTH", "TERMINATE"]


@pytest.mark.asyncio
async def test_scenario_3_legitimate_executive_conversation(test_setup):
    """
    Scenario 3: Routine business conversation with low deepfake score.
    Must maintain NORMAL state without false positives.
    """
    service, mem_mgr, user_ctx = test_setup
    session_id = "SCENARIO-3-LEGIT"

    statements = [
        ("Hi Vikram, do you have the Q3 financial presentation ready?", 0.05),
        ("Yes, I sent the slide deck to your email this morning.", 0.08),
        ("Great, let's review slide 4 during tomorrow's board meeting.", 0.04),
        ("Sounds good. Have a great evening.", 0.02),
    ]

    for stmt, df_score in statements:
        tel = TelemetryEvent(transcript_delta=stmt, deepfake_score=df_score)
        res = await service.process_telemetry(session_id, tel, user_ctx)
        assert res.risk_score < 0.40
        assert res.action_required is None

    mem = mem_mgr.get_session(session_id)
    assert mem.current_state == "NORMAL"
    assert mem.event_counter == 4


@pytest.mark.asyncio
async def test_scenario_4_mid_call_resilience_under_llm_crash(test_setup):
    """
    Scenario 4: Valid threat detection, followed by mid-call Gemini crash.
    Verifies that state and accumulated threat signals survive intact.
    """
    mem_mgr = SessionManager()
    
    call_tracker = {"calls": 0}
    def flaky_llm(ctx):
        call_tracker["calls"] += 1
        if call_tracker["calls"] <= 2:
            return SecurityState(
                current_state="ISOLATION",
                risk_score=0.84,
                running_summary="Active digital arrest threat in progress.",
                active_claim="Fake CBI Inspector",
                signals={"fear": 0.95, "isolation": 0.90},
                action_required="OUT_OF_BAND_VERIFY",
            )
        # 3rd call crashes
        raise ConnectionResetError("Remote Gemini connection dropped")

    service = Layer3Service(memory_manager=mem_mgr, reasoning_engine=flaky_llm)
    user_ctx = UserContext(user_id="EXEC-CRASH-TEST")
    session_id = "SCENARIO-4-CRASH"

    # Calls 1 & 2 succeed
    await service.process_telemetry(session_id, TelemetryEvent(transcript_delta="Claiming CBI"), user_ctx)
    r2 = await service.process_telemetry(session_id, TelemetryEvent(transcript_delta="Demanding isolation"), user_ctx)
    assert r2.current_state == "ISOLATION"
    assert r2.risk_score == 0.84

    # Call 3 encounters crash
    r3 = await service.process_telemetry(session_id, TelemetryEvent(transcript_delta="Share OTP"), user_ctx)
    
    # State remains intact
    assert r3.current_state == "ISOLATION"
    assert r3.risk_score == 0.84
    assert r3.running_summary == "Active digital arrest threat in progress."
    assert "Fail-Safe Mode" in r3.explanation

    mem = mem_mgr.get_session(session_id)
    assert mem.current_state == "ISOLATION"
    assert mem.running_summary == "Active digital arrest threat in progress."
