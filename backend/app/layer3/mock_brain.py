"""Mock reasoning engine for testing Layer 3 memory and service before Person A's Gemini brain is wired."""

from __future__ import annotations
from typing import Any, Dict
from .schemas import SecurityState


def mock_reasoning_engine(context: Dict[str, Any]) -> SecurityState:
    """
    Deterministic rule-based mock of Person A's LLM reasoning engine.
    Interprets telemetry in context of previous running summary and current state.
    """
    new_telemetry = context.get("new_telemetry", {})
    call_memory = context.get("call_memory", {})

    transcript = str(new_telemetry.get("transcript_delta", "")).lower()
    df_score = float(new_telemetry.get("deepfake_score", 0.0))
    is_critical = bool(new_telemetry.get("is_critical", False))

    current_state = call_memory.get("current_state", "NORMAL")
    prev_summary = call_memory.get("running_summary", "Call initiated.")
    active_claim = call_memory.get("active_claim")
    signals = dict(call_memory.get("signals", {}))

    risk = float(call_memory.get("risk_score", 0.0))
    state = current_state
    action = None
    summary_additions = []

    # 1. Authority / Impersonation triggers
    if any(k in transcript for k in ["cfo", "director", "bank", "manager", "customs", "police", "cbi"]):
        state = "AUTHORITY_IMPERSONATION" if state == "NORMAL" else state
        risk = max(risk, 0.45)
        signals["authority"] = 0.85
        active_claim = "Caller claims high-level executive / law-enforcement authority."
        summary_additions.append("Caller established high-authority persona.")

    # 2. Fear, Threat & Digital Arrest triggers
    if any(k in transcript for k in ["arrest", "digital arrest", "jailed", "narcotics", "court", "crime"]):
        state = "FEAR_INDUCTION" if state in ["NORMAL", "AUTHORITY_IMPERSONATION"] else state
        risk = max(risk, 0.60)
        signals["fear"] = 0.90
        signals["threat"] = 0.85
        summary_additions.append("Caller induced fear of arrest or criminal prosecution.")

    # 3. Urgency & Secrecy triggers
    if any(k in transcript for k in ["urgent", "immediately", "secret", "don't tell", "dont tell", "do not tell", "confidential", "disconnect"]):
        state = "URGENCY" if state in ["NORMAL", "AUTHORITY_IMPERSONATION"] else state
        risk = max(risk, 0.65)
        signals["urgency"] = 0.90
        signals["isolation"] = 0.80
        summary_additions.append("Caller applied urgency and requested secrecy/isolation.")

    # 4. Credential & Financial Extraction triggers
    if any(k in transcript for k in ["otp", "pin", "password", "transfer", "upi", "account compromised", "wire"]):
        signals["credential_request"] = 0.95
        signals["financial_pressure"] = 0.90
        if df_score > 0.6 or is_critical:
            state = "ISOLATION"
            risk = max(risk, 0.88)
            action = "OUT_OF_BAND_VERIFY"
            summary_additions.append("Caller demanded credential/fund transfer with elevated synthetic voice risk.")
        else:
            state = "SUSPICIOUS"
            risk = max(risk, 0.70)
            action = "STEP_UP_AUTH"
            summary_additions.append("Caller requested sensitive credentials/funds.")

    # 4. Critical Deepfake Threat
    if df_score >= 0.80 and (risk > 0.5 or is_critical):
        state = "BLOCKED"
        risk = max(risk, 0.96)
        action = "TERMINATE"
        summary_additions.append("Confirmed high-confidence synthetic audio with active threat progression.")

    # Build updated running summary
    if summary_additions:
        new_summary_text = " ".join(summary_additions)
        if prev_summary == "Call initiated.":
            running_summary = new_summary_text
        else:
            running_summary = f"{prev_summary} {new_summary_text}".strip()
    else:
        running_summary = prev_summary

    return SecurityState(
        current_state=state,
        risk_score=round(risk, 3),
        running_summary=running_summary,
        active_claim=active_claim,
        signals=signals,
        action_required=action,
        explanation=f"Evaluated transcript '{transcript}' with deepfake score {df_score}",
    )
