import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from app.main import app
from app.models.session import AttackState


@pytest.mark.asyncio
async def test_normal_telemetry_ingestion():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "session_id": "CALL-NORM-01",
            "device_id": "DEV-USER-01",
            "transcript_delta": "Hello, good morning how are you doing today?",
            "deepfake_score": 0.05,
            "language": "en",
            "is_critical": False
        }
        res = await ac.post("/api/telemetry", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["current_state"] == AttackState.NORMAL.value
        assert data["risk_score"] < 0.3
        assert data["is_critical"] is False


@pytest.mark.asyncio
async def test_scam_attack_progression_and_critical_path():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        session_id = "CALL-SCAM-01"
        device_id = "DEV-VICTIM-99"

        # Step 1: Authority Impersonation
        t1 = {
            "session_id": session_id,
            "device_id": device_id,
            "transcript_delta": "This is Inspector Sharma from Delhi Police and CBI headquarters.",
            "deepfake_score": 0.40,
            "language": "en"
        }
        r1 = await ac.post("/api/telemetry", json=t1)
        d1 = r1.json()
        assert d1["current_state"] == AttackState.AUTHORITY_IMPERSONATION.value
        assert d1["risk_score"] > 0.1

        # Step 2: Fear & Isolation (Digital arrest)
        t2 = {
            "session_id": session_id,
            "device_id": device_id,
            "transcript_delta": "Your bank account is seized for narcotics crime. Do not disconnect and don't tell anyone.",
            "deepfake_score": 0.75,
            "language": "en"
        }
        r2 = await ac.post("/api/telemetry", json=t2)
        d2 = r2.json()
        assert d2["current_state"] in (AttackState.ISOLATION.value, AttackState.FEAR_INDUCTION.value)
        assert d2["risk_score"] >= 0.5

        # Step 3: Critical Credential Extraction (Fast path)
        t3 = {
            "session_id": session_id,
            "device_id": device_id,
            "transcript_delta": "To clear your name, read out the OTP sent to your phone immediately!",
            "deepfake_score": 0.88,
            "language": "en"
        }
        r3 = await ac.post("/api/telemetry", json=t3)
        d3 = r3.json()
        assert d3["current_state"] == AttackState.CREDENTIAL_EXTRACTION.value
        assert d3["risk_score"] >= 0.8
        assert d3["is_critical"] is True


def test_telemetry_triggers_websocket_state_push():
    client = TestClient(app)

    # Connect device over WebSocket
    with client.websocket_connect("/ws/device/DEV-PUSH-TEST") as ws:
        # Initial registration message
        init_msg = ws.receive_json()
        assert init_msg["type"] == "registered"

        # Post telemetry for this device via HTTP
        telemetry_data = {
            "session_id": "CALL-PUSH-SESS",
            "device_id": "DEV-PUSH-TEST",
            "transcript_delta": "Immediate action required. Transfer ₹50,000 security deposit.",
            "deepfake_score": 0.82
        }
        http_res = client.post("/api/telemetry", json=telemetry_data)
        assert http_res.status_code == 200

        # Verify WebSocket receives real-time state_update push
        push_event = ws.receive_json()
        assert push_event["type"] == "state_update"
        assert push_event["session_id"] == "CALL-PUSH-SESS"
        assert push_event["state"] in (AttackState.FINANCIAL_PRESSURE.value, AttackState.URGENCY.value)
        assert push_event["risk"] >= 0.5
