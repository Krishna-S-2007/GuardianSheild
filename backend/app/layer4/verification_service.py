"""Layer 4 Verification and Intervention Dispatcher Service."""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Dict, Optional

from app.models.session import SignalingType
from app.websocket.connection_manager import manager, ConnectionManager
from app.layer3.schemas import UserContext, SecurityState
from .schemas import VerificationStatus, VerificationRecord, VerificationResponse

logger = logging.getLogger("guardianshield.layer4")


class VerificationService:
    """
    Manages automated intervention tools, out-of-band verification challenges,
    and trusted contact notification dispatch.
    """

    def __init__(self, conn_manager: Optional[ConnectionManager] = None):
        self.conn_manager = conn_manager or manager
        self._records: Dict[str, VerificationRecord] = {}
        self._lock = asyncio.Lock()

    async def dispatch_action(
        self,
        session_id: str,
        security_state: SecurityState,
        victim_device_id: str,
        user_context: Optional[UserContext] = None,
    ) -> Optional[VerificationRecord]:
        """
        Interprets action_required from Layer 3 and triggers the corresponding Layer 4 workflow.
        """
        action = security_state.action_required
        if not action:
            return None

        async with self._lock:
            # 1. OUT_OF_BAND_VERIFY: Dispatch challenge to trusted contact
            if action == "OUT_OF_BAND_VERIFY":
                trusted_contacts = user_context.trusted_contacts if user_context else []
                if not trusted_contacts:
                    logger.warning(f"No trusted contacts found for session {session_id} to verify OOB.")
                    return None

                # Select primary trusted contact
                primary_contact = trusted_contacts[0]
                contact_device_id = primary_contact.device_id or "UNKNOWN_CONTACT"

                record = VerificationRecord(
                    session_id=session_id,
                    victim_device_id=victim_device_id,
                    status=VerificationStatus.WAITING_CONTACT,
                    active_claim=security_state.active_claim or "High-risk transaction authorization requested.",
                    target_contact_name=primary_contact.name,
                    target_contact_device_id=contact_device_id,
                )
                self._records[session_id] = record

                # Send challenge message to trusted contact device
                challenge_msg = {
                    "type": SignalingType.VERIFICATION_UPDATE.value,
                    "sender_device_id": "guardian_security_layer4",
                    "session_id": session_id,
                    "payload": {
                        "status": "WAITING_CONTACT",
                        "victim_device_id": victim_device_id,
                        "victim_name": user_context.user_name if user_context else "Executive",
                        "claim": record.active_claim,
                        "risk_score": security_state.risk_score,
                        "prompt": f"Urgent security verification: {record.active_claim}. Did you authorize this request?",
                    }
                }
                await self.conn_manager.send_personal_message(challenge_msg, contact_device_id)

                # Send status to victim device
                victim_notify = {
                    "type": SignalingType.VERIFICATION_UPDATE.value,
                    "sender_device_id": "guardian_security_layer4",
                    "session_id": session_id,
                    "payload": {
                        "status": "WAITING_CONTACT",
                        "contact_name": primary_contact.name,
                        "claim": record.active_claim,
                        "message": f"Out-of-band verification challenge dispatched to {primary_contact.name}.",
                    }
                }
                await self.conn_manager.send_personal_message(victim_notify, victim_device_id)
                logger.info(f"Dispatched OOB challenge for session {session_id} to {primary_contact.name}")
                return record

            # 2. STEP_UP_AUTH: Prompt victim for device biometric confirmation
            elif action == "STEP_UP_AUTH":
                step_up_msg = {
                    "type": SignalingType.VERIFICATION_UPDATE.value,
                    "sender_device_id": "guardian_security_layer4",
                    "session_id": session_id,
                    "payload": {
                        "status": "STEP_UP_PROMPTED",
                        "claim": security_state.active_claim,
                        "message": "Step-up biometric verification required before proceeding.",
                    }
                }
                await self.conn_manager.send_personal_message(step_up_msg, victim_device_id)
                return None

            # 3. TERMINATE: Immediate intervention warning
            elif action == "TERMINATE":
                term_msg = {
                    "type": SignalingType.VERIFICATION_UPDATE.value,
                    "sender_device_id": "guardian_security_layer4",
                    "session_id": session_id,
                    "payload": {
                        "status": "CALL_TERMINATED",
                        "claim": security_state.active_claim,
                        "message": "CRITICAL ATTACK DETECTED. Disconnect immediately. Transaction locked.",
                    }
                }
                await self.conn_manager.send_personal_message(term_msg, victim_device_id)
                return None

        return None

    async def record_response(
        self,
        resp: VerificationResponse
    ) -> Optional[VerificationRecord]:
        """
        Receives verification response from trusted contact and notifies victim device.
        """
        async with self._lock:
            record = self._records.get(resp.session_id)
            if not record:
                logger.warning(f"No active verification record for session {resp.session_id}")
                return None

            record.status = (
                VerificationStatus.CONFIRMED_LEGITIMATE
                if resp.is_legitimate
                else VerificationStatus.CONFIRMED_FRAUD
            )
            record.outcome = resp.notes or ("Legitimate" if resp.is_legitimate else "Fraudulent / Unauthorized")
            record.updated_at = time.time()

            # Push outcome to victim device
            outcome_msg = {
                "type": SignalingType.VERIFICATION_UPDATE.value,
                "sender_device_id": "guardian_security_layer4",
                "session_id": resp.session_id,
                "payload": {
                    "status": record.status.value,
                    "is_legitimate": resp.is_legitimate,
                    "contact_name": record.target_contact_name,
                    "notes": resp.notes,
                    "message": (
                        f"Verified by {record.target_contact_name}: Transaction confirmed authentic."
                        if resp.is_legitimate
                        else f"ALERT: {record.target_contact_name} confirmed this call is FRAUDULENT!"
                    ),
                }
            }
            await self.conn_manager.send_personal_message(outcome_msg, record.victim_device_id)
            logger.info(f"Recorded verification response for {resp.session_id}: status={record.status}")
            return record

    async def get_record(self, session_id: str) -> Optional[VerificationRecord]:
        async with self._lock:
            return self._records.get(session_id)


# Global singleton instance
verification_service = VerificationService()
