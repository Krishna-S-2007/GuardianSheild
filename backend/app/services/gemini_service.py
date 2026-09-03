import json
import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.models.session import CallSession, AttackState
from app.services.risk_service import risk_service

logger = logging.getLogger("guardianshield.gemini")

# Try importing google-genai or google.generativeai if installed
try:
    from google import genai
    GENAI_CLIENT_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai_legacy
        GENAI_CLIENT_AVAILABLE = True
    except ImportError:
        GENAI_CLIENT_AVAILABLE = False


class GeminiService:
    """Layer 3 Contextual Brain (PRD Sections 21-32)."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None
        if self.api_key and GENAI_CLIENT_AVAILABLE:
            try:
                # New google-genai SDK
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}")

    async def analyze_telemetry(
        self,
        session: CallSession,
        transcript_delta: str,
        deepfake_score: Optional[float] = None,
        language: Optional[str] = "en"
    ) -> Dict[str, Any]:
        """
        Analyzes call progression using Gemini 3.1 Flash-Lite / 2.5 Flash,
        or deterministic heuristics fallback.
        """
        # If API key is not configured or client failed, use local deterministic engine
        if not self._client or not self.api_key:
            return self._fallback_analysis(session, transcript_delta, deepfake_score)

        try:
            # Build compact 3-level memory prompt (PRD Sections 24-28)
            payload = {
                "call_memory": {
                    "current_state": session.current_state.value,
                    "risk_score": session.risk_score,
                    "running_summary": session.running_summary,
                    "signals": session.signals,
                    "active_claim": session.active_claim,
                    "recent_events": session.recent_events
                },
                "new_telemetry": {
                    "transcript_delta": transcript_delta,
                    "deepfake_score": deepfake_score,
                    "language": language
                }
            }

            system_instruction = (
                "You are GuardianShield Layer 3 Contextual Brain. Your job is to analyze real-time "
                "telemetry from a live voice call, track the attack state progression, evaluate scam risk, "
                "extract the attacker's active claim, and return a strictly structured JSON response.\n"
                "Allowed states: NORMAL, AUTHORITY_IMPERSONATION, FEAR_INDUCTION, ISOLATION, URGENCY, "
                "FINANCIAL_PRESSURE, CREDENTIAL_EXTRACTION, FAMILY_EMERGENCY, PAYMENT_REQUEST.\n"
                "Return only valid JSON matching this schema:\n"
                "{\n"
                '  "current_state": "<STATE>",\n'
                '  "risk_score": <float 0.0 to 1.0>,\n'
                '  "summary": "<compact running summary>",\n'
                '  "signals": {"authority": 0.0, "fear": 0.0, "urgency": 0.0, "isolation": 0.0, "financial_pressure": 0.0, "credential_request": 0.0, "threat": 0.0},\n'
                '  "active_claim": "<active claim or null>",\n'
                '  "recommended_action": "<action description or null>"\n'
                "}"
            )

            prompt = f"{system_instruction}\n\nInput:\n{json.dumps(payload, indent=2)}"

            # Call Gemini
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )

            if response and response.text:
                result = json.loads(response.text)
                return result

        except Exception as e:
            logger.error(f"Gemini API call failed, falling back to heuristics: {e}")

        return self._fallback_analysis(session, transcript_delta, deepfake_score)

    def _fallback_analysis(
        self,
        session: CallSession,
        transcript_delta: str,
        deepfake_score: Optional[float]
    ) -> Dict[str, Any]:
        """Local deterministic fallback matching PRD attack progression rules."""
        signals = risk_service.evaluate_signals(transcript_delta)
        # Merge with existing session signals
        merged_signals = {}
        for k in session.signals.keys():
            merged_signals[k] = max(session.signals.get(k, 0.0), signals.get(k, 0.0))

        state, summary, claim = risk_service.determine_state(
            merged_signals, transcript_delta, session.current_state
        )
        risk = risk_service.calculate_risk_score(merged_signals, deepfake_score)

        return {
            "current_state": state.value,
            "risk_score": risk,
            "summary": summary,
            "signals": merged_signals,
            "active_claim": claim or session.active_claim,
            "recommended_action": "Do NOT share OTP or transfer funds" if risk > 0.7 else None
        }


gemini_service = GeminiService()
