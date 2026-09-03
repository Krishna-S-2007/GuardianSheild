"""Integration tests verifying Person A (Layer3Brain, Layer3Reasoner, SecuritySignals)
and Person B (CallMemory, Layer3Service, SessionManager) working harmoniously.
"""

import pytest
from app.models.session import CallSession, CallStatus, AttackState
from app.services.session_service import SessionService
from app.layer3.schemas import SecurityState, SecuritySignals, UserContext, TelemetryEvent
from app.layer3.brain import Layer3Brain
from app.layer3.reasoning import Layer3Reasoner
from app.layer3.service import Layer3Service
from app.layer3.memory import CallMemory


def test_security_signals_attribute_and_dict_access():
    """Validates that SecuritySignals supports both Person A attribute access and Person B dict access."""
    sig = SecuritySignals(
        authority=0.85,
        fear=0.90,
        urgency=0.75,
        isolation=0.80,
    )
    # Person A style: attribute access
    assert sig.authority == 0.85
    assert sig.fear == 0.90

    # Person B style: dict access & .get()
    assert sig["authority"] == 0.85
    assert sig.get("fear") == 0.90
    assert sig.get("non_existent", 0.0) == 0.0
    assert "authority" in sig.keys()


def test_security_state_bidirectional_mapping():
    """Validates that Person A fields map to Person B fields and vice-versa."""
    # Person A initialization format
    state_a = SecurityState(
        attack_state=AttackState.AUTHORITY_IMPERSONATION,
        risk=0.88,
        signals=SecuritySignals(authority=0.95),
        active_claim="Customs Officer Fraud",
        recommended_action="OUT_OF_BAND_VERIFY",
        reasoning="Caller claims legal narcotics violation.",
    )
    # Must automatically populate Person B aliases
    assert state_a.current_state == "AUTHORITY_IMPERSONATION"
    assert state_a.risk_score == 0.88
    assert state_a.running_summary == "Caller claims legal narcotics violation."
    assert state_a.action_required == "OUT_OF_BAND_VERIFY"

    # Person B initialization format
    state_b = SecurityState(
        current_state="ISOLATION",
        risk_score=0.92,
        running_summary="Target instructed not to speak with family.",
        action_required="TERMINATE",
        explanation="High severity coercion detected.",
    )
    # Must automatically populate Person A aliases
    assert state_b.attack_state == AttackState.ISOLATION
    assert state_b.risk == 0.92
    assert state_b.reasoning == "Target instructed not to speak with family."
    assert state_b.recommended_action == "TERMINATE"


def test_layer3_brain_resilient_fallback():
    """Layer3Brain must provide deterministic heuristic fallback if API key is not present."""
    brain = Layer3Brain()
    result = brain.analyze(
        transcript="This is Mumbai Police, you are under digital arrest. Transfer your funds now.",
        running_summary="",
        recent_events=[],
    )
    assert isinstance(result, SecurityState)
    assert result.risk > 0.5
    assert result.attack_state in (
        AttackState.SUSPICIOUS,
        AttackState.FEAR_INDUCTION,
        AttackState.AUTHORITY_IMPERSONATION,
        AttackState.ISOLATION,
        AttackState.NORMAL,
    )


@pytest.mark.asyncio
async def test_layer3_reasoner_with_session_service():
    """Validates Layer3Reasoner analyzing and updating a CallSession via SessionService."""
    sess_svc = SessionService()
    session = await sess_svc.create_session(
        caller_device_id="CALLER-01",
        callee_device_id="VICTIM-01",
        custom_session_id="CALL-REASONER-TEST",
    )

    reasoner = Layer3Reasoner(session_service=sess_svc)

    # 1. Analyze session without persisting
    sec_state = reasoner.analyze_session(
        session=session,
        transcript="I am director Sharma from vigilance department.",
    )
    assert isinstance(sec_state, SecurityState)
    assert sec_state.risk >= 0.0

    # 2. Analyze and update session state
    updated_state = await reasoner.analyze_and_update_session(
        session=session,
        transcript="You will be jailed immediately if you hang up.",
        new_event="Caller threatened victim with jail.",
        deepfake_score=0.85,
    )
    assert isinstance(updated_state, SecurityState)

    # Verify session persisted correctly in backend SessionService
    saved_sess = await sess_svc.get_session("CALL-REASONER-TEST")
    assert saved_sess is not None
    assert saved_sess.risk_score == updated_state.risk
    assert len(saved_sess.recent_events) >= 1
    assert len(saved_sess.deepfake_score_history) >= 1


@pytest.mark.asyncio
async def test_layer3_service_integrated_with_person_a_brain():
    """Validates Layer3Service orchestrating memory with Layer3Brain reasoning."""
    brain = Layer3Brain()
    service = Layer3Service()
    service.set_reasoning_engine(lambda ctx: brain.analyze(
        transcript=ctx["new_telemetry"]["transcript_delta"],
        running_summary=ctx["call_memory"].get("running_summary", ""),
        recent_events=[e["transcript_delta"] for e in ctx["call_memory"].get("recent_events", [])],
    ))

    t1 = TelemetryEvent(
        transcript_delta="Your account has been seized by customs. Provide your account number.",
        deepfake_score=0.75,
        is_critical=True,
    )

    res = await service.process_telemetry("CALL-INTEG-001", t1)
    assert res.current_state != "NORMAL" or res.risk_score > 0.4
    assert res.risk_score >= 0.0
