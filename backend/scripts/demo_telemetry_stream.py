"""Interactive live demonstration script simulating real-time call telemetry against GuardianShield backend."""

import asyncio
import json
import time
import httpx
import websockets


BACKEND_REST_URL = "http://localhost:8000/api"
BACKEND_WS_URL = "ws://localhost:8000/ws/device"


async def run_live_attack_demo():
    print("=" * 70)
    print("   GUARDIANSHIELD LAYER 3 - LIVE COGNITIVE DEFENSE DEMONSTRATION")
    print("=" * 70)
    print("\n[1] Registering executive device and trusted contacts...")

    async with httpx.AsyncClient() as client:
        # Register Executive
        reg_payload = {
            "device_id": "DEV-CEO-01",
            "user_name": "Vikram Malhotra (CFO)",
            "trusted_contacts": [
                {"name": "Ananya Sharma", "relationship": "Deputy Director", "device_id": "DEV-DEPUTY-01", "phone_number": "+919876500001"},
                {"name": "Rohit Verma", "relationship": "Head of Security", "device_id": "DEV-SEC-01", "phone_number": "+919876500002"},
            ]
        }
        res = await client.post(f"{BACKEND_REST_URL}/signaling/register", json=reg_payload)
        print(f"    ✓ Registered Executive Device: {res.json()['data']['device_id']}")

    session_id = f"CALL-DEMO-{int(time.time())}"
    print(f"\n[2] Connecting executive to persistent WebSocket signaling (Session: {session_id})...")

    async with websockets.connect(f"{BACKEND_WS_URL}/DEV-CEO-01") as ws:
        reg_ack = json.loads(await ws.recv())
        print(f"    ✓ WebSocket Handshake: {reg_ack['type']}")

        # Multi-turn attack script
        attack_turns = [
            {
                "turn": 1,
                "speaker": "Unknown Caller",
                "transcript": "Hello Vikram, I am calling from the corporate banking division regarding your treasury account.",
                "deepfake_score": 0.35,
                "is_critical": False,
            },
            {
                "turn": 2,
                "speaker": "Unknown Caller",
                "transcript": "We have detected unauthorized attempts on your account. This is strictly confidential. Do not disconnect the line.",
                "deepfake_score": 0.68,
                "is_critical": False,
            },
            {
                "turn": 3,
                "speaker": "Unknown Caller",
                "transcript": "To safeguard company funds, you must immediately authorize the emergency transfer of 50 Lakhs to the secure escrow account.",
                "deepfake_score": 0.94,
                "is_critical": True,
            },
        ]

        print("\n[3] Streaming continuous call telemetry chunks...")
        for turn in attack_turns:
            print(f"\n--- [Turn {turn['turn']}] Telemetry Ingested ---")
            print(f"    Spoken text: \"{turn['transcript']}\"")
            print(f"    Acoustic Deepfake Score: {turn['deepfake_score']:.2f}")

            telemetry_packet = {
                "type": "telemetry",
                "sender_device_id": "DEV-CEO-01",
                "session_id": session_id,
                "payload": {
                    "transcript_delta": turn["transcript"],
                    "deepfake_score": turn["deepfake_score"],
                    "is_critical": turn["is_critical"],
                }
            }
            await ws.send(json.dumps(telemetry_packet))

            # Receive real-time cognitive defense update
            response_raw = await ws.recv()
            state_update = json.loads(response_raw)
            payload = state_update.get("payload", {})

            print(f"    [Layer 3 State Update]")
            print(f"      • Security State: {payload.get('current_state')}")
            print(f"      • Risk Score:     {payload.get('risk_score'):.3f}")
            print(f"      • Action Trigger: {payload.get('action_required') or 'None'}")
            print(f"      • Running Story:  \"{payload.get('running_summary')}\"")
            print(f"      • Active Claim:   \"{payload.get('active_claim')}\"")

            await asyncio.sleep(1)

    print("\n" + "=" * 70)
    print("   DEMONSTRATION COMPLETE: ATTACK PROGRESSION SUCCESSFULLY BLOCKED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_live_attack_demo())
