import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from app.main import app
from app.models.session import SignalingType


@pytest.mark.asyncio
async def test_device_registration_and_listing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register device
        reg_payload = {
            "device_id": "DEV-TEST-01",
            "user_name": "Alice Victim",
            "trusted_contacts": [
                {
                    "name": "Bob Contact",
                    "relationship": "brother",
                    "device_id": "DEV-TEST-02"
                }
            ]
        }
        res = await ac.post("/api/signaling/register", json=reg_payload)
        assert res.status_code == 200
        assert res.json()["success"] is True

        # List devices
        list_res = await ac.get("/api/signaling/devices")
        assert list_res.status_code == 200
        devices = list_res.json()
        assert any(d["device_id"] == "DEV-TEST-01" for d in devices)


def test_websocket_signaling_flow():
    client = TestClient(app)

    # 1. Connect Caller and Victim via WebSocket
    with client.websocket_connect("/ws/device/DEV-CALLER") as ws_caller:
        # Check registration event
        reg_caller = ws_caller.receive_json()
        assert reg_caller["type"] == SignalingType.REGISTERED.value

        with client.websocket_connect("/ws/device/DEV-VICTIM") as ws_victim:
            reg_victim = ws_victim.receive_json()
            assert reg_victim["type"] == SignalingType.REGISTERED.value

            # 2. Caller initiates call to Victim
            initiate_msg = {
                "type": SignalingType.CALL_INITIATE.value,
                "sender_device_id": "DEV-CALLER",
                "target_device_id": "DEV-VICTIM",
                "session_id": "CALL-UNIT-TEST-1"
            }
            ws_caller.send_json(initiate_msg)

            # 3. Victim receives INCOMING_CALL event
            incoming_event = ws_victim.receive_json()
            assert incoming_event["type"] == SignalingType.INCOMING_CALL.value
            assert incoming_event["sender_device_id"] == "DEV-CALLER"
            session_id = incoming_event["session_id"]

            # 4. Victim accepts call
            accept_msg = {
                "type": SignalingType.CALL_ACCEPT.value,
                "sender_device_id": "DEV-VICTIM",
                "target_device_id": "DEV-CALLER",
                "session_id": session_id
            }
            ws_victim.send_json(accept_msg)

            # 5. Caller receives CALL_ACCEPT event
            accepted_event = ws_caller.receive_json()
            assert accepted_event["type"] == SignalingType.CALL_ACCEPT.value

            # 6. Caller sends SDP OFFER
            offer_msg = {
                "type": SignalingType.OFFER.value,
                "sender_device_id": "DEV-CALLER",
                "target_device_id": "DEV-VICTIM",
                "session_id": session_id,
                "sdp": "v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 5004 RTP/AVP 0\r\n",
                "sdp_type": "offer"
            }
            ws_caller.send_json(offer_msg)

            # 7. Victim receives SDP OFFER
            offer_received = ws_victim.receive_json()
            assert offer_received["type"] == SignalingType.OFFER.value
            assert offer_received["sdp"] == offer_msg["sdp"]

            # 8. Victim sends SDP ANSWER
            answer_msg = {
                "type": SignalingType.ANSWER.value,
                "sender_device_id": "DEV-VICTIM",
                "target_device_id": "DEV-CALLER",
                "session_id": session_id,
                "sdp": "v=0\r\no=- 54321 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 5004 RTP/AVP 0\r\n",
                "sdp_type": "answer"
            }
            ws_victim.send_json(answer_msg)

            # 9. Caller receives SDP ANSWER
            answer_received = ws_caller.receive_json()
            assert answer_received["type"] == SignalingType.ANSWER.value

            # 10. ICE Candidate exchange
            ice_msg = {
                "type": SignalingType.ICE_CANDIDATE.value,
                "sender_device_id": "DEV-CALLER",
                "target_device_id": "DEV-VICTIM",
                "session_id": session_id,
                "candidate": {"candidate": "candidate:1 1 UDP 2130706431 192.168.1.1 5004 typ host", "sdpMid": "0"}
            }
            ws_caller.send_json(ice_msg)

            ice_received = ws_victim.receive_json()
            assert ice_received["type"] == SignalingType.ICE_CANDIDATE.value

            # 11. Caller ends call
            end_msg = {
                "type": SignalingType.CALL_END.value,
                "sender_device_id": "DEV-CALLER",
                "target_device_id": "DEV-VICTIM",
                "session_id": session_id
            }
            ws_caller.send_json(end_msg)

            end_received = ws_victim.receive_json()
            assert end_received["type"] == SignalingType.CALL_END.value
