"""Tests for GuardianShield Layer 4 — Verification & Intervention Service."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.layer4.schemas import (
    VerificationStatus,
    VerificationRequest,
    VerificationResponse,
    VerificationRecord,
)
from app.layer4.verification_service import VerificationService
from app.layer3.schemas import SecurityState, UserContext, TrustedContact


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_security_state(action: str, risk: float = 0.85) -> SecurityState:
    return SecurityState(
        session_id="sess-001",
        current_state="FINANCIAL_PRESSURE",
        risk_score=risk,
        running_summary="Caller demands urgent wire transfer.",
        active_claim="Wire Rs 10 lakh to 'sister hospital account' immediately.",
        signals={"authority": 0.7, "urgency": 0.9, "financial_pressure": 0.85},
        action_required=action,
        explanation="High fraud confidence.",
    )


def _make_user_context() -> UserContext:
    return UserContext(
        user_id="victim-001",
        user_name="Rajit",
        trusted_contacts=[
            TrustedContact(
                name="Priya (Spouse)",
                relationship="spouse",
                device_id="contact-device-001",
            )
        ],
    )


def _make_mock_manager(sent: list) -> MagicMock:
    mock = MagicMock()
    async def fake_send(msg, device_id):
        sent.append({"to": device_id, "msg": msg})
        return True
    mock.send_personal_message = fake_send
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# 1. OOB Verification dispatch
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_oob_verify_creates_record_and_notifies_contact():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    record = await svc.dispatch_action(
        session_id="sess-001",
        security_state=_make_security_state("OUT_OF_BAND_VERIFY"),
        victim_device_id="victim-device-001",
        user_context=_make_user_context(),
    )

    assert record is not None
    assert record.status == VerificationStatus.WAITING_CONTACT
    assert record.target_contact_device_id == "contact-device-001"
    assert record.target_contact_name == "Priya (Spouse)"

    # Exactly two messages sent: one to contact, one to victim
    assert len(sent) == 2
    recipients = {m["to"] for m in sent}
    assert "contact-device-001" in recipients
    assert "victim-device-001" in recipients

    contact_msg = next(m["msg"] for m in sent if m["to"] == "contact-device-001")
    assert contact_msg["type"] == "verification_update"
    assert "prompt" in contact_msg["payload"]


@pytest.mark.asyncio
async def test_oob_verify_no_contacts_returns_none():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))
    ctx = UserContext(user_id="u", user_name="X", trusted_contacts=[])

    record = await svc.dispatch_action(
        session_id="sess-002",
        security_state=_make_security_state("OUT_OF_BAND_VERIFY"),
        victim_device_id="victim-device-002",
        user_context=ctx,
    )

    assert record is None
    assert len(sent) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. STEP_UP_AUTH dispatch
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step_up_auth_sends_prompt_to_victim():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    record = await svc.dispatch_action(
        session_id="sess-003",
        security_state=_make_security_state("STEP_UP_AUTH"),
        victim_device_id="victim-device-003",
        user_context=_make_user_context(),
    )

    assert record is None  # No OOB record created for step-up
    assert len(sent) == 1
    assert sent[0]["to"] == "victim-device-003"
    assert sent[0]["msg"]["payload"]["status"] == "STEP_UP_PROMPTED"


# ─────────────────────────────────────────────────────────────────────────────
# 3. TERMINATE dispatch
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_terminate_sends_critical_alert_to_victim():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    record = await svc.dispatch_action(
        session_id="sess-004",
        security_state=_make_security_state("TERMINATE"),
        victim_device_id="victim-device-004",
        user_context=_make_user_context(),
    )

    assert record is None
    assert len(sent) == 1
    assert sent[0]["to"] == "victim-device-004"
    assert sent[0]["msg"]["payload"]["status"] == "CALL_TERMINATED"
    assert "CRITICAL" in sent[0]["msg"]["payload"]["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. No action_required → nothing dispatched
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_action_required_returns_none():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))
    state = _make_security_state("OUT_OF_BAND_VERIFY")
    state.action_required = None

    record = await svc.dispatch_action(
        session_id="sess-005",
        security_state=state,
        victim_device_id="victim-device-005",
    )
    assert record is None
    assert len(sent) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Verification response — confirmed FRAUD
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verification_response_fraud_notifies_victim():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    # First dispatch to create a record
    await svc.dispatch_action(
        session_id="sess-010",
        security_state=_make_security_state("OUT_OF_BAND_VERIFY"),
        victim_device_id="victim-device-010",
        user_context=_make_user_context(),
    )
    sent.clear()

    # Trusted contact responds: fraud
    resp = VerificationResponse(
        session_id="sess-010",
        contact_device_id="contact-device-001",
        is_legitimate=False,
        notes="I never asked for any money transfer."
    )
    record = await svc.record_response(resp)

    assert record is not None
    assert record.status == VerificationStatus.CONFIRMED_FRAUD
    assert len(sent) == 1
    victim_msg = sent[0]
    assert victim_msg["to"] == "victim-device-010"
    assert victim_msg["msg"]["payload"]["is_legitimate"] is False
    assert "FRAUDULENT" in victim_msg["msg"]["payload"]["message"]


@pytest.mark.asyncio
async def test_verification_response_legitimate_confirms_safe():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    await svc.dispatch_action(
        session_id="sess-011",
        security_state=_make_security_state("OUT_OF_BAND_VERIFY"),
        victim_device_id="victim-device-011",
        user_context=_make_user_context(),
    )
    sent.clear()

    resp = VerificationResponse(
        session_id="sess-011",
        contact_device_id="contact-device-001",
        is_legitimate=True,
        notes="Yes, I am the one calling."
    )
    record = await svc.record_response(resp)

    assert record.status == VerificationStatus.CONFIRMED_LEGITIMATE
    assert sent[0]["msg"]["payload"]["is_legitimate"] is True
    assert "authentic" in sent[0]["msg"]["payload"]["message"].lower()


@pytest.mark.asyncio
async def test_response_for_nonexistent_session_returns_none():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    resp = VerificationResponse(
        session_id="no-such-session",
        contact_device_id="contact-xyz",
        is_legitimate=False,
    )
    record = await svc.record_response(resp)
    assert record is None
    assert len(sent) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 6. get_record
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_record_returns_existing_record():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    await svc.dispatch_action(
        session_id="sess-020",
        security_state=_make_security_state("OUT_OF_BAND_VERIFY"),
        victim_device_id="victim-020",
        user_context=_make_user_context(),
    )
    record = await svc.get_record("sess-020")
    assert record is not None
    assert record.session_id == "sess-020"


@pytest.mark.asyncio
async def test_get_record_returns_none_for_missing():
    svc = VerificationService(conn_manager=_make_mock_manager([]))
    record = await svc.get_record("nonexistent")
    assert record is None


# ─────────────────────────────────────────────────────────────────────────────
# 7. Concurrency / multi-session isolation
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_multiple_sessions_are_isolated():
    sent = []
    svc = VerificationService(conn_manager=_make_mock_manager(sent))

    ctx_a = UserContext(
        user_id="u-a", user_name="Alice",
        trusted_contacts=[TrustedContact(name="Bob", relationship="spouse", device_id="bob-device")]
    )
    ctx_b = UserContext(
        user_id="u-b", user_name="Charlie",
        trusted_contacts=[TrustedContact(name="Dana", relationship="sister", device_id="dana-device")]
    )

    await svc.dispatch_action("sess-A", _make_security_state("OUT_OF_BAND_VERIFY"), "alice-device", ctx_a)
    await svc.dispatch_action("sess-B", _make_security_state("OUT_OF_BAND_VERIFY"), "charlie-device", ctx_b)

    rec_a = await svc.get_record("sess-A")
    rec_b = await svc.get_record("sess-B")

    assert rec_a.target_contact_name == "Bob"
    assert rec_b.target_contact_name == "Dana"
    assert rec_a.victim_device_id != rec_b.victim_device_id
