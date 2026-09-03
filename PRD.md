# GuardianShield — Final Product Requirements Document (PRD)

**Project Type:** AI + Cybersecurity + Real-Time Edge/Cloud System  
**Hackathon:** Microsoft Innovation Club, VIT Chennai Hackathon  
**Prototype Strategy:** Software-only, Android + WebRTC + AI + Backend  
**Primary Objective:** Detect AI-generated voice and social-engineering attacks during a live call, understand how the attack is progressing, and trigger an appropriate verification/intervention workflow in real time.

---

# 1. Product Overview

GuardianShield is a real-time protection system for AI-powered voice scams.

The core idea is:

> **Do not only determine whether a call is suspicious. Determine what attack is happening, maintain the evolving context of the call, and take the appropriate counter-action while the call is still active.**

GuardianShield uses a hybrid **edge + cloud architecture**:

- The **Android device** handles latency-sensitive and privacy-sensitive audio processing.
    
- The **backend** handles contextual reasoning, memory, state management, and later verification/tool execution.
    
- Raw call audio is **never intentionally sent to the backend** during normal operation.
    
- Only compact derived telemetry is sent from the device.
    

The prototype uses a **GuardianShield-owned WebRTC VoIP call** rather than attempting to intercept arbitrary cellular calls through the normal Android dialer.

---

# 2. Core Innovation

The innovation is not the individual AI models.

Deepfake detection, speech recognition, scam detection, and out-of-band verification already exist independently.

GuardianShield combines them around a different decision mechanism:

```text
LIVE CALL
    ↓
AUTHENTICITY EVIDENCE
    +
ATTACK EVIDENCE
    ↓
UNDERSTAND CURRENT ATTACK STATE
    ↓
UNDERSTAND THE ATTACKER'S CLAIM / OBJECTIVE
    ↓
SELECT THE APPROPRIATE COUNTER-ACTION
    ↓
VERIFY / INTERRUPT / PROTECT
```

The intended differentiator is:

> **Adaptive attack-aware intervention instead of simple scam detection and warning.**

The system should be able to distinguish between:

- family emergency scam
    
- bank impersonation
    
- authority impersonation
    
- isolation/manipulation
    
- credential extraction
    
- financial pressure
    

and choose a different response depending on the situation.

---

# 3. Target Prototype

The hackathon prototype will consist of:

```text
GuardianShield Android App
        ↕
   WebRTC Live Call
        ↕
GuardianShield Backend
        ↕
Layer 3 Brain
        ↕
Verification Tools
        ↕
Other GuardianShield Devices
```

The same GuardianShield Android application can operate on multiple devices.

One device can act as the victim.

Another registered GuardianShield device can act as a trusted contact.

---

# 4. High-Level End-to-End Architecture

```text
                         CALLER
                           │
                           │ WebRTC
                           ▼
                ┌─────────────────────┐
                │ GuardianShield App  │
                │   Victim Device     │
                └──────────┬──────────┘
                           │
                    Remote Audio Track
                           │
                           ▼
                      PCM Audio
                           │
                 ┌─────────┴─────────┐
                 │                   │
                 ▼                   ▼
             LAYER 1              LAYER 2
           AASIST-L             IndicConformer
          Deepfake Detection       ASR
                 │                   │
                 │                   ▼
                 │             Live transcript
                 │                   │
                 └─────────┬─────────┘
                           │
                    Derived telemetry
                    every ~5–7 sec
                           │
              immediate on critical events
                           │
                           ▼
                     BACKEND SERVER
                           │
                           ▼
                    LAYER 3 BRAIN
                Gemini 3.1 Flash-Lite
                           │
                     Context Memory
                           │
                    State + Risk + Claim
                           │
                           ▼
                    LAYER 4 TOOLS
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       Verify Person   Notify Contact   Protect Action
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
                   Tool Result / Status
                           │
                           ▼
                    Backend Session
                           │
                           ▼
                     Layer 3 update
                           │
                           ▼
                    Victim Android
```

---

# 5. Android Application

## 5.1 Goal

The mobile application should remain deliberately simple.

This is the first mobile application implementation for the team, so the app should avoid unnecessary UI complexity.

### Main screen

```text
┌────────────────────────────┐
│       GUARDIANSHIELD       │
│                            │
│ Device ID: GS-7A21         │
│ Backend: ● Connected       │
│                            │
│       [ START ]            │
│                            │
│ Call Status: Idle          │
└────────────────────────────┘
```

The application mainly needs to:

- register the device
    
- connect to the backend
    
- show connection status
    
- become available for GuardianShield calls
    
- receive incoming GuardianShield calls
    
- start the WebRTC session
    
- run local Layer 1 and Layer 2 processing
    
- display security status
    
- receive verification updates
    
- display the final intervention/result
    

---

# 6. Calling Model

## 6.1 Why GuardianShield uses its own VoIP call

A normal Android third-party application cannot generally capture the raw audio of arbitrary cellular calls.

Therefore the prototype must **own the communication channel**.

The project will use:

> **WebRTC-based GuardianShield VoIP calling**

The application therefore has legitimate access to the incoming remote media stream.

---

# 7. Incoming Call Flow

The backend acts as the signalling/coordinating system.

### Before a call

The Android app starts and connects to the backend.

```text
GuardianShield App
        ↓
Connect backend
        ↓
Register device
        ↓
Device status = ONLINE
```

The backend stores:

```text
device_id
user_id
online/offline
trusted contacts
call availability
```

---

## 7.1 Caller initiates call

```text
Caller App
     ↓
Backend
     ↓
Find target device
     ↓
Send incoming-call event
     ↓
Victim GuardianShield App
```

The Android app receives:

```text
INCOMING GUARDIANSHIELD CALL
```

It displays:

```text
Caller: Unknown
[ ACCEPT ] [ REJECT ]
```

---

# 8. Call Acceptance

When the victim accepts:

```text
ACCEPT
  ↓
WebRTC session established
  ↓
Remote audio starts arriving
  ↓
Audio processing begins
```

At this point Layer 1 and Layer 2 start consuming the incoming audio stream.

The normal call continues while analysis happens in parallel.

---

# 9. WebRTC Audio Pipeline

WebRTC is responsible for transporting the live call.

Conceptually:

```text
Remote caller
      ↓
WebRTC media
      ↓
Victim Android
      ↓
Remote AudioTrack
      ↓
PCM audio frames
```

The application does not build its own:

- audio codec
    
- RTP implementation
    
- packetization
    
- jitter handling
    
- network transport
    

WebRTC provides the media transport.

GuardianShield only needs to access the received audio samples and pass them to the analysis pipeline.

---

# 10. Audio Representation

WebRTC's Android audio pipeline provides PCM-style audio data.

The exact sample rate/channel configuration must be verified experimentally rather than assumed.

The application should therefore inspect:

```text
sample rate
channels
bits per sample
frame size
```

The expected starting configuration is likely:

```text
PCM
16-bit
mono
~48 kHz
```

The actual runtime configuration becomes authoritative.

---

# 11. Audio Adapter

Different AI models may require different audio formats.

Therefore a dedicated **Audio Adapter** exists between WebRTC and the models.

```text
WebRTC PCM
    ↓
Audio Adapter
    ↓
common model-ready format
```

Potential operations:

- sample-rate conversion
    
- mono conversion
    
- integer-to-float conversion
    
- normalization
    
- buffering
    

For example:

```text
48 kHz / 16-bit PCM
        ↓
16 kHz / mono
        ↓
model-specific representation
```

The conversion should happen once whenever possible instead of independently for each model.

---

# 12. Audio Fan-Out

The same incoming audio stream feeds both local AI pipelines.

```text
                   PCM AUDIO
                       │
                       ▼
                 AUDIO BUFFER
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        LAYER 1                LAYER 2
        AASIST-L             IndicConformer
```

The pipelines must execute concurrently.

Layer 1 must not block Layer 2.

Layer 2 must not block Layer 1.

---

# 13. Layer 1 — Deepfake Detection

## Model

**AASIST-L**

A lightweight audio anti-spoofing model.

The selected deployment format is:

> **AASIST-L ONNX**

running through an Android-compatible ONNX runtime.

---

## 13.1 Layer 1 responsibility

Layer 1 answers:

> **“Is there evidence that the caller's voice is synthetic/spoofed?”**

It outputs a confidence/evidence score.

Example:

```json
{
  "deepfake_score": 0.87
}
```

---

## 13.2 Layer 1 processing

Conceptually:

```text
PCM audio
   ↓
16 kHz mono
   ↓
rolling audio window
   ↓
AASIST-L
   ↓
spoof probability
```

The model uses a multi-second audio window rather than making a meaningful decision from a single tiny audio frame.

The system therefore maintains a rolling buffer.

---

## 13.3 Layer 1 design principle

Deepfake detection is **evidence, not the final verdict**.

For example:

```text
Deepfake risk = LOW
Psychological attack = HIGH
```

The overall system must still identify the call as potentially dangerous.

---

# 14. Layer 2 — Multilingual Speech Recognition

## Model

> **IndicConformer quantized ONNX + sherpa-onnx**

Target languages:

- English
    
- Hindi
    
- Tamil
    

The system should also tolerate common Indian code-switching where feasible.

Example:

```text
Hindi + English
Tamil + English
```

---

# 15. Layer 2 Responsibility

Layer 2 is intentionally **stateless**.

It should NOT maintain call memory.

Its responsibility is only:

```text
live audio
   ↓
continuous ASR
   ↓
current transcript
   ↓
send transcript to backend
```

Layer 2 should not perform:

- long-term reasoning
    
- tool calling
    
- verification
    
- call-level memory
    
- complex attack reasoning
    

Those belong to Layer 3.

---

# 16. Live ASR Operation

The system should not record the complete call and process it afterwards.

Instead:

```text
LIVE AUDIO
    ↓
small audio chunks
    ↓
streaming ASR
    ↓
partial transcript
```

The transcript continuously evolves during the call.

Example:

```text
"your account..."
        ↓
"your account has..."
        ↓
"your account has suspicious..."
        ↓
"your account has suspicious activity..."
```

---

# 17. Layer 2 Output

Layer 2 produces transcript data.

Example:

```json
{
  "timestamp": 31.4,
  "transcript_delta": "Don't disconnect. Tell me the OTP."
}
```

Language information may also be attached:

```json
{
  "language": "ta-en"
}
```

The transcript remains compact and incremental.

---

# 18. Mobile-Side Privacy Architecture

Raw audio remains on the victim's device.

```text
RAW AUDIO
   ↓
AASIST-L
   +
IndicConformer
   ↓
Derived information
   ↓
RAW AUDIO discarded / not transmitted
```

The backend receives:

- transcript delta
    
- deepfake score
    
- timestamps
    
- other derived telemetry
    

It does not need the original audio recording.

---

# 19. Telemetry Transfer

Normal operation:

> **Send telemetry approximately every 5–7 seconds.**

Example:

```json
{
  "session_id": "CALL123",
  "timestamp": 42,

  "transcript_delta":
    "Don't disconnect. Tell me the OTP.",

  "deepfake_score": 0.84
}
```

---

## 19.1 Critical Event Fast Path

If the local device recognizes an obvious critical event, it should not wait for the next normal batch.

Examples:

```text
OTP
transfer money
send money
don't tell anyone
password
PIN
urgent transfer
```

Then:

```text
CRITICAL EVENT
     ↓
IMMEDIATE TELEMETRY
     ↓
BACKEND
```

Therefore the system is:

> **Periodic by default + event-driven when critical.**

---

# 20. Backend Architecture

The backend is responsible for:

- device registration
    
- signalling
    
- active sessions
    
- telemetry reception
    
- Layer 3 processing
    
- context memory
    
- state management
    
- tool orchestration later
    
- verification status
    
- pushing results to devices
    

Recommended stack:

```text
FastAPI
WebSocket
Python
Session store
Gemini API
```

For the hackathon, the simplest session-memory implementation is initially an in-memory Python dictionary.

A Redis-backed implementation may be introduced if needed.

---

# 21. Layer 3 — Contextual Brain

Layer 3 is the main intelligence layer.

It receives:

```text
telemetry
+
existing call state
+
user profile context
```

and generates an updated structured security state.

---

# 22. Gemini Model

Primary model:

> **Gemini 3.1 Flash-Lite**

Reason:

- low-latency model
    
- suitable for high-frequency lightweight requests
    
- structured output support
    
- function-calling capability for later Layer 4 integration
    
- managed inference removes the need to operate a large LLM server during the hackathon
    

The model should not be treated as the memory store.

> **Our backend owns memory. Gemini processes the current state.**

---

# 23. Layer 3 Memory Architecture

Each active call receives a unique:

```text
session_id
```

Example:

```text
CALL123
```

The backend associates a state object with that session.

---

## 23.1 Session Memory

Example:

```json
{
  "session_id": "CALL123",

  "current_state": "ISOLATION",

  "risk_score": 0.82,

  "running_summary":
    "Caller claims to be a bank employee and is pressuring the victim.",

  "signals": {
    "authority": 0.92,
    "fear": 0.76,
    "urgency": 0.68,
    "isolation": 0.91,
    "financial_pressure": 0.30
  },

  "active_claim":
    "Victim's bank account is compromised.",

  "recent_events": []
}
```

---

# 24. Three Memory Levels

## 24.1 Current State

What is happening now.

```text
state
risk
signals
active claim
```

## 24.2 Recent Events

A small rolling list of recent events.

```text
Event N-2
Event N-1
Event N
```

This prevents ambiguity without keeping the complete transcript in every request.

## 24.3 Running Summary

One compact continuously updated summary of the call.

Example:

> "Caller impersonates a bank employee, claims account compromise and pressures the victim to provide an OTP."

---

# 25. Gemini Processing Cycle

When telemetry arrives:

```text
NEW TELEMETRY
      +
CURRENT MEMORY
      ↓
Gemini
      ↓
UPDATED JSON STATE
      ↓
VALIDATE
      ↓
STORE
      ↓
RETURN STATUS TO MOBILE
```

Gemini should receive:

```text
user context
+
current call state
+
recent events
+
new telemetry
```

It should NOT receive the entire historical transcript every six seconds.

---

# 26. Why the Entire Transcript Is Not Resent

Bad:

```text
Event 1
Event 2
Event 3
Event 4
...
Event 50
+
Event 51
```

every time.

This causes continuously growing prompts.

Correct:

```text
compact current state
+
small recent history
+
new event
```

This keeps the Gemini request approximately constant in size.

---

# 27. User Profile Context

The backend also maintains persistent information about the GuardianShield user.

Example:

```json
{
  "user_id": "USER123",

  "name": "Arun",

  "trusted_contacts": [
    {
      "name": "Krishna",
      "relationship": "son",
      "device_id": "DEV-KRISHNA"
    },
    {
      "name": "Priya",
      "relationship": "daughter",
      "device_id": "DEV-PRIYA"
    }
  ]
}
```

This is not call memory.

It is **persistent user context**.

---

# 28. Layer 3 Input Structure

Conceptually:

```json
{
  "user_context": {...},

  "call_memory": {
    "current_state": "ISOLATION",
    "risk_score": 0.82,
    "running_summary": "...",
    "signals": {...},
    "active_claim": "...",
    "recent_events": [...]
  },

  "new_telemetry": {
    "transcript_delta":
      "Give me the OTP immediately.",
    "deepfake_score": 0.88
  }
}
```

---

# 29. Layer 3 Output

Gemini produces a structured state.

Example:

```json
{
  "current_state": "CREDENTIAL_EXTRACTION",

  "risk_score": 0.96,

  "summary":
    "Caller is urgently requesting the victim's OTP.",

  "signals": {
    "authority": 0.92,
    "fear": 0.76,
    "urgency": 0.94,
    "isolation": 0.91,
    "financial_pressure": 0.72,
    "credential_request": 0.99
  },

  "active_claim":
    "The victim's bank account is compromised."
}
```

The backend validates this JSON and stores it as the current session state.

---

# 30. Structured Output

Layer 3 must use a fixed schema.

Possible states:

```text
NORMAL
AUTHORITY_IMPERSONATION
FEAR_INDUCTION
ISOLATION
URGENCY
FINANCIAL_PRESSURE
CREDENTIAL_EXTRACTION
FAMILY_EMERGENCY
PAYMENT_REQUEST
```

Possible signals:

```text
authority
fear
urgency
isolation
financial_pressure
credential_request
threat
```

This keeps output predictable.

---

# 31. State Evolution

Example:

```text
0–7 sec
AUTHORITY_IMPERSONATION

7–14 sec
FEAR_INDUCTION

14–21 sec
ISOLATION

21–28 sec
FINANCIAL_PRESSURE

28–35 sec
CREDENTIAL_EXTRACTION
```

Layer 3 therefore sees the **attack progression** rather than isolated sentences.

---

# 32. Layer 3 Timing

Normal:

```text
5–7 second telemetry
      ↓
Gemini
      ↓
state update
```

Critical:

```text
critical telemetry
      ↓
immediate Gemini processing
```

The backend should therefore process telemetry asynchronously so that one model request does not block the rest of the call session.

---

# 33. Layer 4 — Verification / Tool Execution

Layer 4 will be defined separately from Layer 3.

Layer 3 does **not directly execute external actions**.

It can request:

```text
tool name
arguments
```

The backend executes the actual function.

Basic pattern:

```text
Gemini
  ↓
tool request
  ↓
backend executor
  ↓
tool execution
  ↓
result
  ↓
Layer 3
```

---

# 34. GuardianShield Device Network

The same Android application can exist on multiple devices.

```text
                  BACKEND
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       VICTIM     KRISHNA      PRIYA
       DEVICE      DEVICE      DEVICE
```

The backend maintains device identity and relationships.

This allows one GuardianShield device to request verification from another.

---

# 35. Example: Family Emergency Verification

Caller:

> "Krishna has been arrested. Send money immediately."

GuardianShield detects:

```text
deepfake risk
+
family emergency
+
fear
+
urgency
+
financial pressure
```

Layer 3 decides that the claim should be independently checked.

Later Layer 4 executes:

```text
verify_person("Krishna")
```

Backend finds Krishna's registered GuardianShield device.

It sends:

```text
"GuardianShield verification request:
Are you safe?"

[YES, I'M SAFE]
[NO]
```

Krishna responds.

Backend receives:

```json
{
  "status": "VERIFIED",
  "result": "SAFE"
}
```

The result is returned to Layer 3.

The victim then sees:

```text
CLAIM:
"Krishna is in danger"

INDEPENDENT VERIFICATION:
✅ Krishna reports safe
```

---

# 36. Verification Communication

The GuardianShield app should be the actual verification endpoint.

The backend is the coordinator.

```text
Victim App
    ↓
Backend
    ↓
Trusted Contact GuardianShield App
    ↓
Backend
    ↓
Victim App
```

The system should use reliable Android notification delivery for waking/alerting a trusted device when required.

A persistent WebSocket connection can be used while the application is active, but mobile background restrictions mean the system should not assume a permanently alive WebSocket.

---

# 37. Live Status Updates

The victim app should maintain a backend WebSocket.

Example:

```text
PHONE ←──────── WebSocket ────────→ BACKEND
```

Backend can push:

```json
{
  "type": "state_update",
  "state": "CREDENTIAL_EXTRACTION",
  "risk": 0.96
}
```

And:

```json
{
  "type": "verification_update",
  "status": "WAITING"
}
```

Then:

```json
{
  "type": "verification_update",
  "status": "VERIFIED",
  "result": "Krishna is safe"
}
```

---

# 38. Mobile UI During Call

The actual call screen can remain extremely simple.

```text
┌───────────────────────────────┐
│       GUARDIANSHIELD          │
│                               │
│     Call: Unknown Caller      │
│     ● LIVE                    │
│                               │
│ Deepfake Evidence: 87%        │
│ Scam Risk:        HIGH        │
│                               │
│ State: CREDENTIAL EXTRACTION  │
│                               │
│ "Caller is requesting an OTP" │
│                               │
│ Verification: RUNNING...      │
└───────────────────────────────┘
```

The UI should display live state but should not be responsible for the underlying reasoning.

---

# 39. End-to-End Example

## Step 1 — Call

```text
Caller
 ↓
WebRTC
 ↓
Victim GuardianShield
```

## Step 2 — Local audio

```text
Remote audio
 ↓
PCM
 ↓
AASIST-L + IndicConformer
```

## Step 3 — Local results

```text
Deepfake = 0.84

Transcript:
"Don't disconnect. Your account is in danger."
```

## Step 4 — Telemetry

```text
Phone → Backend
```

## Step 5 — Layer 3

```text
Existing state:
AUTHORITY_IMPERSONATION

New event:
ISOLATION + FEAR
```

Gemini updates:

```text
state = ISOLATION
risk = 0.82
```

## Step 6 — Next event

```text
"Tell me the OTP immediately."
```

Layer 3 updates:

```text
state = CREDENTIAL_EXTRACTION
risk = 0.96
```

## Step 7 — Counter-action

Layer 3 requests the appropriate verification/protection tool.

## Step 8 — Tool executes

Backend communicates with the required GuardianShield device or intervention mechanism.

## Step 9 — Result

Tool result returns to Layer 3.

## Step 10 — Mobile

```text
🚨 CRITICAL
Caller requesting OTP.

GuardianShield recommends:
DO NOT SHARE OTP.
```

---

# 40. Latency Architecture

The system should avoid unnecessary sequential processing.

Correct:

```text
                 WEBRTC
                    │
                    ▼
                 PCM AUDIO
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       AASIST-L            ASR
          │                   │
          │              transcript
          │                   │
          └─────────┬─────────┘
                    ▼
                telemetry
                    │
               ~5–7 sec
                    ▼
                 BACKEND
                    │
                    ▼
                 Gemini
                    │
                    ▼
              state update
```

Critical events bypass the normal timer.

---

# 41. Latency Budget

The following values should be treated as **targets to measure**, not guaranteed numbers.

```text
WebRTC audio availability       → measure
Audio buffering                 → minimize
Deepfake inference              → measure
ASR first useful text           → measure
Telemetry transmission          → minimize
Backend request                 → minimize
Gemini inference                → measure
Tool execution                  → measure
Mobile update                   → measure
```

The primary performance metric is:

> **Time from a meaningful attack signal appearing in the call to the corresponding intervention appearing on the victim device.**

---

# 42. Privacy Requirements

GuardianShield should follow:

```text
RAW AUDIO
   ↓
LOCAL PROCESSING
   ↓
DISCARD / MEMORY ONLY
```

Only derived data leaves the device.

The backend should receive the minimum information required:

```text
transcript delta
deepfake score
timestamp
session ID
```

The application should not persist raw call recordings unless explicitly enabled for development testing.

---

# 43. Failure Handling

## Internet unavailable

The local call and local analysis should not crash simply because backend communication fails.

At minimum:

```text
AASIST-L continues
ASR continues
```

Telemetry can retry when connectivity returns.

---

## ASR failure

```text
Deepfake detection continues
```

---

## Deepfake model failure

```text
ASR continues
```

---

## Gemini failure

The backend should preserve the most recent state and fall back to a deterministic high-risk policy where appropriate.

---

## Verification timeout

Backend should mark:

```text
TIMEOUT
```

rather than waiting indefinitely.

The victim should receive an appropriate warning instead of a silent failure.

---

# 44. Technology Stack

## Android

```text
Kotlin
Native Android
WebRTC
ONNX Runtime / sherpa-onnx
Foreground/service lifecycle as required
WebSocket client
```

## Layer 1

```text
AASIST-L
ONNX
ONNX Runtime
```

## Layer 2

```text
IndicConformer
Quantized ONNX
sherpa-onnx
VAD as required
```

## Backend

```text
Python
FastAPI
WebSocket
```

## Layer 3

```text
Gemini 3.1 Flash-Lite API
Structured JSON output
```

## Memory

Hackathon MVP:

```text
Python in-memory session store
```

Upgrade path:

```text
Redis
```

## Device-to-device signalling

```text
GuardianShield app instances
+
Backend coordination
+
Android notification mechanism
```

---

# 45. What We Reuse

We should NOT build the following ourselves:

```text
WebRTC transport
Audio codecs
RTP
Network traversal
Deepfake model
ASR model
LLM
Android notification infrastructure
```

We integrate proven components.

Our engineering work is the **system and security orchestration layer**.

---

# 46. What We Build

We build:

```text
GuardianShield Android app
GuardianShield call/signalling layer
Audio extraction adapter
Local model pipeline
Telemetry protocol
Backend session manager
Context-memory system
Layer 3 state engine
Structured state schema
Verification tool framework
Device identity system
Live status UI
```

---

# 47. 24-Hour Hackathon MVP

The official schedule starts development at **11:30 AM**, has idea evaluation from **2:00–3:00 PM**, requires GitHub submission by **2:00 AM**, and Devfolio submission by **8:00 AM**.

Therefore, the practical build target is the **2 AM GitHub deadline**, not a theoretical 24-hour development window.

---

## P0 — Must work

```text
WebRTC live call
        ↓
Remote PCM
        ↓
AASIST-L
        +
IndicConformer
        ↓
Telemetry
        ↓
FastAPI
        ↓
Session memory
        ↓
Gemini
        ↓
Structured state
        ↓
One real verification workflow
        ↓
Result back to victim
```

---

# 48. P1 — Important

```text
Multiple GuardianShield devices
Live status WebSocket
Critical-event fast path
Connection handling
Clean dashboard
Better state visualization
```

---

# 49. P2 — Cut if time becomes tight

```text
Multiple institution integrations
Multiple authority integrations
Complex authentication
Production database
Advanced UI
Fancy animations
Multiple verification scenarios
Custom ML training
Perfect offline support
```

---

# 50. Development Milestones

## Milestone 1

### WebRTC foundation

```text
Device A
   ↕
Device B
```

Must establish a live call.

Then verify:

```text
remote PCM frames arriving
```

---

## Milestone 2

### Layer 1

```text
PCM
 ↓
AASIST-L
 ↓
score
```

---

## Milestone 3

### Layer 2

```text
PCM
 ↓
IndicConformer
 ↓
live Hindi/Tamil/English text
```

---

## Milestone 4

### Device telemetry

```text
transcript
+
deepfake score
 ↓
backend
```

---

## Milestone 5

### Layer 3

```text
telemetry
+
state
 ↓
Gemini
 ↓
JSON
 ↓
memory
```

---

## Milestone 6

### Verification

```text
Layer 3
 ↓
verification request
 ↓
GuardianShield trusted device
 ↓
response
 ↓
backend
 ↓
victim
```

---

# 51. Demo Scenario

The preferred demonstration should be a **family emergency / financial scam** because it naturally demonstrates the entire system.

Example attack:

```text
"I am calling because Krishna has been arrested."

"Don't tell anyone."

"You only have five minutes."

"Transfer ₹50,000 immediately."
```

System evolution:

```text
AUTHORITY
     ↓
FEAR
     ↓
ISOLATION
     ↓
URGENCY
     ↓
FINANCIAL PRESSURE
```

Meanwhile:

```text
AASIST-L
→ synthetic voice evidence
```

Layer 2:

```text
live transcript
```

Layer 3:

```text
attack progression
+
claim
+
risk
```

Then:

```text
verification tool
```

Trusted GuardianShield device:

```text
Krishna:
"I'm safe."
```

Victim sees:

```text
🚨 SCAM INTERVENTION

Caller claim:
"Krishna is in danger."

Independent verification:
✅ Krishna is safe.

Recommended action:
Do NOT transfer money.
```

---

# 52. Product Success Criteria

GuardianShield succeeds as a hackathon prototype when it demonstrates all of the following in one continuous live flow:

```text
✅ Incoming GuardianShield call
✅ WebRTC connection
✅ Live remote audio
✅ Local PCM access
✅ AASIST-L processing
✅ Multilingual live ASR
✅ No raw audio sent to backend
✅ Periodic telemetry
✅ Critical-event fast path
✅ Backend session memory
✅ Gemini structured state output
✅ Attack-state progression
✅ One working verification tool
✅ Trusted-device response
✅ Verification result returned to victim
✅ Live UI update
```

---

# 53. Final System Responsibility Map

|Component|Responsibility|
|---|---|
|**Android App**|Calling, local audio processing, UI|
|**WebRTC**|Live voice transport|
|**Audio Adapter**|Convert/prepare PCM for models|
|**AASIST-L**|Voice authenticity/deepfake evidence|
|**IndicConformer**|Live Hindi/Tamil/English ASR|
|**Telemetry Layer**|Send compact derived data|
|**FastAPI Backend**|Signalling, sessions, communication|
|**Session Memory**|Store current call context|
|**Gemini 3.1 Flash-Lite**|Contextual reasoning/state update|
|**Layer 4 Tools**|Execute verification/intervention|
|**Trusted GuardianShield Device**|Independent verification endpoint|
|**WebSocket**|Live backend ↔ device status|

---

# 54. Final Architectural Principle

The system should always preserve this division:

```text
              DEVICE
      "Hear and detect quickly."

                ↓

             BACKEND
       "Remember and reason."

                ↓

          VERIFICATION
       "Check reality externally."

                ↓

              DEVICE
        "Protect the victim."
```

Or even more simply:

> **The phone senses. The backend thinks. The trusted device verifies.**

This is the complete end-to-end GuardianShield architecture for the hackathon.