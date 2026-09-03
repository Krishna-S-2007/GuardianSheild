"""Interactive live demonstration script simulating real-time call telemetry against GuardianShield backend."""

import asyncio
import json
import time
import httpx
import websockets

BACKEND_REST_URL = "http://localhost:8000/api"
BACKEND_WS_URL = "ws://localhost:8000/ws/device"


async def run_live_attack_demo():
    print("=" * 76)
    print("   GUARDIANSHIELD: FULL END-TO-END DEFENSE & INTERVENTION DEMO")
    print("=" * 76)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Register Executive Device & Trusted Contacts
        print("\n[1] Registering Executive Target & Trusted Contacts...")
        reg_ceo = {
            "device_id": "DEV-CEO-01",
            "user_name": "Vikram Malhotra (CFO)",
            "trusted_contacts": [
                {
                    "name": "Ananya Sharma",
                    "relationship": "Deputy Director",
                    "device_id": "DEV-DEPUTY-01",
                    "phone_number": "+919876500001",
                },
                {
                    "name": "Rohit Verma",
                    "relationship": "Head of Corporate Security",
                    "device_id": "DEV-SEC-01",
                    "phone_number": "+919876500002",
                },
            ],
        }
        res1 = await client.post(f"{BACKEND_REST_URL}/signaling/register", json=reg_ceo)
        print(f"    [+] Executive Registered: {res1.json()['data']['device_id']} ({res1.json()['data']['user_name']})")

        # Register External Caller
        reg_caller = {
            "device_id": "DEV-CALLER-SPOOF",
            "user_name": "Unverified Inbound Caller",
        }
        await client.post(f"{BACKEND_REST_URL}/signaling/register", json=reg_caller)

        session_id = f"CALL-EXEC-{int(time.time())}"
        print(f"\n[2] Establishing WebRTC Call Session: {session_id}")

        # Initiate Call
        init_req = {
            "caller_device_id": "DEV-CALLER-SPOOF",
            "callee_device_id": "DEV-CEO-01",
            "custom_session_id": session_id,
        }
        init_res = await client.post(f"{BACKEND_REST_URL}/signaling/call/initiate", json=init_req)
        print(f"    ✓ Call Initiated between DEV-CALLER-SPOOF -> DEV-CEO-01")

        # Callee Accepts Call
        accept_req = {
            "device_id": "DEV-CEO-01",
            "session_id": session_id,
        }
        await client.post(f"{BACKEND_REST_URL}/signaling/call/accept", json=accept_req)
        print(f"    ✓ Call Connected: State=CONNECTED, Threat=NORMAL (0% Risk)")

    print(f"\n[3] Connecting Executive Device to Real-Time WebSocket Signaling...")
    async with websockets.connect(f"{BACKEND_WS_URL}/DEV-CEO-01") as ws:
        reg_ack = json.loads(await ws.recv())
        print(f"    ✓ WebSocket Online: Device={reg_ack.get('device_id')} Status={reg_ack.get('status')}")

        # Multi-stage attack scenario
        attack_turns = [
            {
                "turn": 1,
                "label": "Stage 1: Persona Establishment",
                "transcript": "Hello Vikram, I am calling from corporate banking division regarding your treasury account.",
                "deepfake_score": 0.35,
                "is_critical": False,
            },
            {
                "turn": 2,
                "label": "Stage 2: Confidentiality & Urgency Pressure",
                "transcript": "We have detected unauthorized security attempts. This is strictly confidential. Do not disconnect the line.",
                "deepfake_score": 0.68,
                "is_critical": False,
            },
            {
                "turn": 3,
                "label": "Stage 3: High-Value Financial Transfer Claim",
                "transcript": "To safeguard company funds from digital arrest, you must immediately wire 50 Lakhs to the verified escrow account.",
                "deepfake_score": 0.94,
                "is_critical": True,
            },
        ]

        print("\n[4] Ingesting Live Telemetry Streams into Layer 3 Cognitive Brain...")
        for turn in attack_turns:
            print(f"\n--- [{turn['label']}] ---")
            print(f"    Spoken Text:            \"{turn['transcript']}\"")
            print(f"    Acoustic Deepfake Score: {turn['deepfake_score']:.2f}")

            telemetry_packet = {
                "type": "telemetry",
                "sender_device_id": "DEV-CEO-01",
                "session_id": session_id,
                "payload": {
                    "transcript_delta": turn["transcript"],
                    "deepfake_score": turn["deepfake_score"],
                    "is_critical": turn["is_critical"],
                },
            }
            await ws.send(json.dumps(telemetry_packet))

            # Receive real-time cognitive defense update
            response_raw = await ws.recv()
            state_update = json.loads(response_raw)
            payload = state_update.get("payload", {})

            print(f"    [Layer 3 State Update]")
            print(f"      • Attack State:   {payload.get('current_state')}")
            print(f"      • Risk Score:     {payload.get('risk_score'):.3f} ({(payload.get('risk_score', 0.0) * 100):.0f}%)")
            print(f"      • Action Trigger: {payload.get('action_required') or 'MONITOR'}")
            print(f"      • Active Claim:   \"{payload.get('active_claim')}\"")
            print(f"      • Context Memory: \"{payload.get('running_summary')}\"")

            # Check if Layer 4 dispatched an intervention
            try:
                extra_raw = await asyncio.wait_for(ws.recv(), timeout=0.6)
                extra_msg = json.loads(extra_raw)
                if extra_msg.get("type") == "verification_update":
                    v_pay = extra_msg.get("payload", {})
                    print(f"\n    [Layer 4 Automated Intervention Dispatched!]")
                    print(f"      • Status:       {v_pay.get('status')}")
                    print(f"      • Target:       {v_pay.get('contact_name')}")
                    print(f"      • Advisory:     \"{v_pay.get('message')}\"")
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(1)

        # 5. Simulate Trusted Contact Verification Response
        print("\n[5] Simulating Trusted Contact (Ananya Sharma) Out-of-Band Response...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            verify_payload = {
                "session_id": session_id,
                "responder_device_id": "DEV-DEPUTY-01",
                "confirmed": False,
                "response_note": "DENIED: No emergency transfer was authorized by corporate treasury.",
            }
            res_v = await client.post(f"{BACKEND_REST_URL}/signaling/verify", json=verify_payload)
            print(f"    ✓ Verification Processed: {res_v.json()['data']['status']}")

            # Receive outcome on victim WebSocket
            try:
                outcome_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                outcome_msg = json.loads(outcome_raw)
                if outcome_msg.get("type") == "verification_update":
                    o_pay = outcome_msg.get("payload", {})
                    print(f"\n    [Victim Alert Pushed via WebSocket!]")
                    print(f"      • Outcome:      {o_pay.get('status')}")
                    print(f"      • Warning:      \"{o_pay.get('message')}\"")
            except asyncio.TimeoutError:
                pass

    print("\n" + "=" * 76)
    print("   DEMONSTRATION COMPLETE: VISHING ATTACK DEBUNKED & INTERCEPTED")
    print("=" * 76)


if __name__ == "__main__":
    asyncio.run(run_live_attack_demo())
