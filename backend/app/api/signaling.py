import json
import logging
from typing import List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from pydantic import BaseModel

from app.models.session import (
    DeviceProfile,
    CallSession,
    CallStatus,
    SignalingMessage,
    SignalingType
)
from app.models.responses import BaseResponse
from app.websocket.connection_manager import manager
from app.services.session_service import session_service

logger = logging.getLogger("guardianshield.signaling")
router = APIRouter()


class InitiateCallRequest(BaseModel):
    caller_device_id: str
    callee_device_id: str
    custom_session_id: Optional[str] = None


class CallActionRequest(BaseModel):
    session_id: str
    device_id: str


# --- REST Endpoints ---

@router.post("/signaling/register", response_model=BaseResponse, tags=["Signaling"])
async def register_device_rest(profile: DeviceProfile):
    """Registers a device profile and trusted contacts."""
    saved_profile = await session_service.register_device(profile)
    return BaseResponse(
        message=f"Device {profile.device_id} registered successfully.",
        data=saved_profile.model_dump()
    )


@router.get("/signaling/devices", response_model=List[DeviceProfile], tags=["Signaling"])
async def list_devices():
    """Returns all registered devices with their online statuses."""
    devices = await session_service.get_all_devices()
    for dev in devices:
        dev.online = manager.is_online(dev.device_id)
    return devices


@router.get("/signaling/sessions", response_model=List[CallSession], tags=["Signaling"])
async def list_sessions():
    """Returns all currently active call sessions."""
    return await session_service.get_all_active_sessions()


@router.get("/signaling/session/{session_id}", response_model=CallSession, tags=["Signaling"])
async def get_session_details(session_id: str):
    """Returns details for a specific call session."""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/signaling/call/initiate", response_model=BaseResponse, tags=["Signaling"])
async def initiate_call_rest(req: InitiateCallRequest):
    """Initiates a WebRTC call session from caller to callee."""
    # Verify callee is online
    if not manager.is_online(req.callee_device_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Callee device {req.callee_device_id} is not online."
        )

    session = await session_service.create_session(
        caller_device_id=req.caller_device_id,
        callee_device_id=req.callee_device_id,
        custom_session_id=req.custom_session_id
    )

    # Send incoming_call event to callee over WebSocket
    incoming_msg = {
        "type": SignalingType.INCOMING_CALL.value,
        "sender_device_id": req.caller_device_id,
        "target_device_id": req.callee_device_id,
        "session_id": session.session_id,
        "payload": {
            "caller_name": req.caller_device_id,
            "session_id": session.session_id
        }
    }
    await manager.send_personal_message(incoming_msg, req.callee_device_id)

    return BaseResponse(
        message=f"Call initiated. Session {session.session_id} created.",
        data=session.model_dump()
    )


@router.post("/signaling/call/accept", response_model=BaseResponse, tags=["Signaling"])
async def accept_call_rest(req: CallActionRequest):
    """Callee accepts the incoming call."""
    session = await session_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_service.update_session_status(req.session_id, CallStatus.CONNECTED)

    # Notify caller that call was accepted
    msg = {
        "type": SignalingType.CALL_ACCEPT.value,
        "sender_device_id": req.device_id,
        "target_device_id": session.caller_device_id,
        "session_id": req.session_id
    }
    await manager.send_personal_message(msg, session.caller_device_id)

    return BaseResponse(message="Call accepted successfully.")


@router.post("/signaling/call/reject", response_model=BaseResponse, tags=["Signaling"])
async def reject_call_rest(req: CallActionRequest):
    """Callee rejects the incoming call."""
    session = await session_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_service.update_session_status(req.session_id, CallStatus.REJECTED)

    # Notify caller that call was rejected
    msg = {
        "type": SignalingType.CALL_REJECT.value,
        "sender_device_id": req.device_id,
        "target_device_id": session.caller_device_id,
        "session_id": req.session_id
    }
    await manager.send_personal_message(msg, session.caller_device_id)

    return BaseResponse(message="Call rejected.")


@router.post("/signaling/call/hangup", response_model=BaseResponse, tags=["Signaling"])
async def hangup_call_rest(req: CallActionRequest):
    """Ends the active call session."""
    session = await session_service.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_service.update_session_status(req.session_id, CallStatus.ENDED)

    # Determine peer device to notify
    peer_device_id = (
        session.callee_device_id if req.device_id == session.caller_device_id else session.caller_device_id
    )

    msg = {
        "type": SignalingType.CALL_END.value,
        "sender_device_id": req.device_id,
        "target_device_id": peer_device_id,
        "session_id": req.session_id
    }
    await manager.send_personal_message(msg, peer_device_id)

    return BaseResponse(message="Call ended successfully.")


# --- WebSocket Signaling Endpoint ---

@router.websocket("/ws/device/{device_id}")
async def websocket_signaling_endpoint(websocket: WebSocket, device_id: str):
    """
    Persistent WebSocket connection for a GuardianShield device.
    Handles device registration, WebRTC SDP offer/answer relay,
    ICE candidate exchange, and real-time state push.
    """
    await manager.connect(device_id, websocket)
    await session_service.update_device_presence(device_id, True)

    # Send registration confirmation
    await manager.send_personal_message(
        {
            "type": SignalingType.REGISTERED.value,
            "sender_device_id": "backend",
            "target_device_id": device_id,
            "payload": {"status": "connected", "device_id": device_id}
        },
        device_id
    )

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                msg_type = data.get("type")
                target_id = data.get("target_device_id")
                session_id = data.get("session_id")

                logger.debug(f"Received WS message {msg_type} from {device_id} -> {target_id}")

                if msg_type == SignalingType.PING.value:
                    await manager.send_personal_message(
                        {"type": SignalingType.PONG.value, "sender_device_id": "backend"},
                        device_id
                    )

                elif msg_type == SignalingType.CALL_INITIATE.value:
                    if target_id and manager.is_online(target_id):
                        session = await session_service.create_session(
                            caller_device_id=device_id,
                            callee_device_id=target_id,
                            custom_session_id=session_id
                        )
                        # Relay to callee
                        incoming_event = {
                            "type": SignalingType.INCOMING_CALL.value,
                            "sender_device_id": device_id,
                            "target_device_id": target_id,
                            "session_id": session.session_id,
                            "payload": {"caller_name": device_id, "session_id": session.session_id}
                        }
                        await manager.send_personal_message(incoming_event, target_id)
                    else:
                        await manager.send_personal_message(
                            {
                                "type": SignalingType.ERROR.value,
                                "sender_device_id": "backend",
                                "payload": {"error": f"Target device {target_id} is offline"}
                            },
                            device_id
                        )

                elif msg_type == SignalingType.CALL_ACCEPT.value:
                    if session_id:
                        await session_service.update_session_status(session_id, CallStatus.CONNECTED)
                    if target_id:
                        await manager.send_personal_message(data, target_id)

                elif msg_type == SignalingType.CALL_REJECT.value:
                    if session_id:
                        await session_service.update_session_status(session_id, CallStatus.REJECTED)
                    if target_id:
                        await manager.send_personal_message(data, target_id)

                elif msg_type in (SignalingType.OFFER.value, SignalingType.ANSWER.value, SignalingType.ICE_CANDIDATE.value):
                    # Relay WebRTC SDP Offer / Answer / ICE Candidates directly to target peer
                    if target_id:
                        relayed = await manager.send_personal_message(data, target_id)
                        if not relayed:
                            logger.warning(f"Failed to relay {msg_type} to {target_id} (offline)")

                elif msg_type == SignalingType.CALL_END.value:
                    if session_id:
                        await session_service.update_session_status(session_id, CallStatus.ENDED)
                    if target_id:
                        await manager.send_personal_message(data, target_id)

                else:
                    logger.warning(f"Unknown signaling message type: {msg_type}")

            except json.JSONDecodeError:
                logger.error(f"Malformed JSON from device {device_id}: {data_text}")

    except WebSocketDisconnect:
        await manager.disconnect(device_id)
        await session_service.update_device_presence(device_id, False)
        # End any active call for this disconnected device
        active_sess = await session_service.get_active_session_for_device(device_id)
        if active_sess:
            await session_service.update_session_status(active_sess.session_id, CallStatus.ENDED)
            peer_id = active_sess.callee_device_id if active_sess.caller_device_id == device_id else active_sess.caller_device_id
            await manager.send_personal_message(
                {
                    "type": SignalingType.CALL_END.value,
                    "sender_device_id": device_id,
                    "session_id": active_sess.session_id,
                    "payload": {"reason": "Peer disconnected unexpectedly"}
                },
                peer_id
            )
    except Exception as e:
        logger.error(f"WebSocket error on device {device_id}: {e}")
        await manager.disconnect(device_id)
        await session_service.update_device_presence(device_id, False)
