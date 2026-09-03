# GuardianShield

> **Real-Time Edge/Cloud Protection Against AI Voice Clones and Social Engineering Attacks**

GuardianShield is a real-time defense system designed to detect AI-generated voice scams and social engineering attacks during live calls, understand how the attack is progressing, and trigger appropriate counter-actions and verification workflows in real time.

---

## 🏗 Recommended Repository Structure

```text
GuardianShield/
│
├── README.md
├── .gitignore
│
├── docs/
│   │
│   ├── architecture/
│   │   ├── system_architecture.md
│   │   ├── audio_pipeline.md
│   │   └── data_contracts.md
│   │
│   ├── api/
│   │   └── backend_api.md
│   │
│   └── integration/
│       └── testing_plan.md
│
├── android/
│   │
│   ├── app/
│   │   └── src/
│   │       └── main/
│   │           │
│   │           ├── java/.../guardianshield/
│   │           │   │
│   │           │   ├── ui/
│   │           │   │   ├── screens/
│   │           │   │   └── components/
│   │           │   │
│   │           │   ├── webrtc/
│   │           │   │   ├── WebRTCManager.kt
│   │           │   │   ├── SignalingClient.kt
│   │           │   │   └── AudioPipeline.kt
│   │           │   │
│   │           │   ├── audio/
│   │           │   │   ├── PCMBuffer.kt
│   │           │   │   └── AudioContract.kt
│   │           │   │
│   │           │   ├── layer1/
│   │           │   │   ├── AASISTManager.kt
│   │           │   │   └── Layer1Result.kt
│   │           │   │
│   │           │   ├── layer2/
│   │           │   │   ├── ASRManager.kt
│   │           │   │   └── TranscriptResult.kt
│   │           │   │
│   │           │   ├── network/
│   │           │   │   ├── ApiClient.kt
│   │           │   │   └── WebSocketClient.kt
│   │           │   │
│   │           │   └── MainActivity.kt
│   │           │
│   │           └── res/
│   │
│   └── build.gradle.kts
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── signaling.py
│   │   │   └── telemetry.py
│   │   │
│   │   ├── websocket/
│   │   │   └── connection_manager.py
│   │   │
│   │   ├── services/
│   │   │   ├── session_service.py
│   │   │   ├── risk_service.py
│   │   │   └── gemini_service.py
│   │   │
│   │   ├── models/
│   │   │   ├── telemetry.py
│   │   │   ├── session.py
│   │   │   └── responses.py
│   │   │
│   │   └── core/
│   │       └── config.py
│   │
│   └── requirements.txt
│
├── contracts/
│   │
│   ├── audio_contract.md
│   ├── telemetry_contract.json
│   ├── layer1_contract.json
│   └── layer2_contract.json
│
└── tests/
    │
    ├── backend/
    └── integration/
```

---

## ⚡ Backend Architecture

```text
                    ANDROID APP
                         │
             ┌───────────┴───────────┐
             │                       │
          HTTP/API               WebSocket
             │                       │
             └───────────┬───────────┘
                         ▼
                   FASTAPI APP
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Signaling      Telemetry       Health
          │              │
          ▼              ▼
      Call Session    Session Service
                         │
                         ▼
                    Risk Engine
                         │
                         ▼
                   Gemini Service
                         │
                         ▼
                    Risk Decision
                         │
                         ▼
                    WebSocket
                         │
                         ▼
                   ANDROID APP
```

---

## 🌿 Branching Strategy

```text
main
 │
 ├── feature/base-android
 │
 ├── feature/webrtc-audio
 │
 ├── feature/layer1
 │
 ├── feature/layer2
 │
 └── feature/backend-risk
```
