import time
import logging
from fastapi import APIRouter, HTTPException, status
from app.models.telemetry import TelemetryPayload, TelemetryIngestResponse
from app.models.responses import StateUpdatePush
from app.models.session import AttackState
from app.services.session_service import session_service
from app.services.risk_service import risk_service
from app.services.gemini_service import gemini_service
from app.websocket.connection_manager import manager

logger = logging.getLogger("guardianshield.telemetry")
router = APIRouter()


@router.post("/telemetry", response_model=TelemetryIngestResponse, tags=["Telemetry"])
async def ingest_telemetry(payload: TelemetryPayload):
    """
    Ingests derived telemetry (transcript delta, deepfake score, timestamp)
    from Android victim device without transmitting any raw audio (PRD Sections 18-19).
    Updates session memory and pushes live security state over WebSocket.
    """
    session = await session_service.get_session(payload.session_id)
    if not session:
        # Create an ad-hoc session if not pre-registered (for quick dev testing)
        session = await session_service.create_session(
            caller_device_id="UNKNOWN_CALLER",
            callee_device_id=payload.device_id,
            custom_session_id=payload.session_id
        )

    # Check fast-path critical event condition (PRD Section 19.1)
    is_critical = payload.is_critical or risk_service.is_critical_event(
        payload.transcript_delta, payload.deepfake_score
    )

    # Run Layer 3 Brain analysis (Gemini or deterministic fallback)
    analysis = await gemini_service.analyze_telemetry(
        session=session,
        transcript_delta=payload.transcript_delta,
        deepfake_score=payload.deepfake_score,
        language=payload.language
    )

    # Parse and validate returned state
    state_str = analysis.get("current_state", "NORMAL")
    try:
        new_state = AttackState(state_str)
    except ValueError:
        new_state = AttackState.NORMAL

    risk_score = float(analysis.get("risk_score", 0.0))
    summary = analysis.get("summary", session.running_summary)
    signals = analysis.get("signals", session.signals)
    active_claim = analysis.get("active_claim")

    # If critical event, bump urgency/risk
    if is_critical and risk_score < 0.8:
        risk_score = 0.85

    # Update session memory (PRD Sections 23-26)
    updated_session = await session_service.update_session_state(
        session_id=session.session_id,
        current_state=new_state,
        risk_score=risk_score,
        summary=summary,
        signals=signals,
        active_claim=active_claim,
        new_event=payload.transcript_delta if payload.transcript_delta else None,
        deepfake_score=payload.deepfake_score
    )

    # Prepare push notification for the victim device
    state_push = StateUpdatePush(
        session_id=session.session_id,
        state=new_state.value,
        risk=risk_score,
        summary=summary,
        signals=signals,
        active_claim=active_claim,
        is_critical=is_critical,
        timestamp=time.time()
    )

    # Push state update in real-time over WebSocket to the device
    await manager.send_personal_message(state_push.model_dump(), payload.device_id)

    logger.info(
        f"Telemetry processed for session {session.session_id}: "
        f"State={new_state.value}, Risk={risk_score:.2f}, Critical={is_critical}"
    )

    return TelemetryIngestResponse(
        status="success",
        session_id=session.session_id,
        current_state=new_state.value,
        risk_score=risk_score,
        is_critical=is_critical,
        summary=summary,
        timestamp=time.time()
    )
