import re
from typing import Dict, Tuple, Optional
from app.models.session import AttackState
from app.core.config import settings


class RiskService:
    """Heuristics and signal extraction engine for voice scam analysis."""

    def __init__(self):
        # Keyword & pattern sets for Indian/Global Voice Scam archetypes
        self.authority_patterns = [
            r"\b(police|cbi|customs|court|officer|inspector|trai|rbi|cyber crime|enforcement directorate|ed|department|headquarters)\b",
            r"\b(warrant|arrest|legal action|court order|official investigation|non-bailable)\b"
        ]
        self.fear_patterns = [
            r"\b(arrested|jailed|prison|crime|drugs|narcotics|seized|illegal package|frozen|blocked|penalty|penalty clause)\b",
            r"\b(serious trouble|compromised|criminal offense|in danger|accident|hospitalized)\b"
        ]
        self.urgency_patterns = [
            r"\b(immediately|right now|urgent|hurry|5 minutes|within an hour|do not delay|quick|expire|instant|action required)\b",
            r"\b(don't wait|act now|time is running out)\b"
        ]
        self.isolation_patterns = [
            r"\b(do not disconnect|don't disconnect|stay on the line|keep this line open|don't tell anyone|keep this secret|do not inform family|stay in a room alone|confidential)\b",
            r"\b(digital arrest|stay on video)\b"
        ]
        self.credential_patterns = [
            r"\b(otp|one time password|pin|upi pin|password|cvv|card number|account number|verification code|security code)\b",
            r"\b(tell me the code|share the code|read out the otp)\b"
        ]
        self.financial_patterns = [
            r"\b(transfer|send money|wire|deposit|pay now|fee|bail|penalty amount|security deposit|rbi verification account|clearance fee)\b",
            r"(₹|\brs\.?|\binr\b|\blakh\b|\bthousand\b|\b\d{4,}\b|\b50,?000\b|\bbank balance\b)"
        ]
        self.family_emergency_patterns = [
            r"\b(your son|your daughter|your child|your father|your mother|krishna|priya|relative|in accident|in custody)\b"
        ]

    def evaluate_signals(self, text: str) -> Dict[str, float]:
        """Calculates normalized signal scores (0.0 to 1.0) from text."""
        lower_text = text.lower()
        signals = {
            "authority": 0.0,
            "fear": 0.0,
            "urgency": 0.0,
            "isolation": 0.0,
            "financial_pressure": 0.0,
            "credential_request": 0.0,
            "threat": 0.0
        }

        # Authority
        for p in self.authority_patterns:
            if re.search(p, lower_text):
                signals["authority"] = min(1.0, signals["authority"] + 0.5)

        # Fear / Threat
        for p in self.fear_patterns:
            if re.search(p, lower_text):
                signals["fear"] = min(1.0, signals["fear"] + 0.5)
                signals["threat"] = min(1.0, signals["threat"] + 0.4)

        # Urgency
        for p in self.urgency_patterns:
            if re.search(p, lower_text):
                signals["urgency"] = min(1.0, signals["urgency"] + 0.5)

        # Isolation
        for p in self.isolation_patterns:
            if re.search(p, lower_text):
                signals["isolation"] = min(1.0, signals["isolation"] + 0.6)

        # Credential Request
        for p in self.credential_patterns:
            if re.search(p, lower_text):
                signals["credential_request"] = min(1.0, signals["credential_request"] + 0.7)

        # Financial Pressure
        for p in self.financial_patterns:
            if re.search(p, lower_text):
                signals["financial_pressure"] = min(1.0, signals["financial_pressure"] + 0.5)

        return signals

    def determine_state(
        self,
        signals: Dict[str, float],
        text: str,
        current_state: AttackState
    ) -> Tuple[AttackState, str, Optional[str]]:
        """
        Determines state progression, summary explanation, and active claim.
        Following PRD Sections 30-31 state evolution.
        """
        lower_text = text.lower()

        # Check Family Emergency
        for p in self.family_emergency_patterns:
            if re.search(p, lower_text) and (signals["fear"] > 0.2 or signals["financial_pressure"] > 0.2):
                claim = "Family member reported to be in danger / custody."
                return AttackState.FAMILY_EMERGENCY, "Caller claims family member is in critical danger/custody.", claim

        # Check Credential Extraction (Highest immediate risk)
        if signals["credential_request"] >= 0.5:
            claim = "Caller is demanding sensitive credentials or OTP."
            return AttackState.CREDENTIAL_EXTRACTION, "Caller is actively pressuring the victim to disclose OTP / credentials.", claim

        # Check Financial Pressure / Payment
        if signals["financial_pressure"] >= 0.4 and (signals["urgency"] >= 0.3 or signals["authority"] >= 0.3 or signals["fear"] >= 0.3):
            claim = "Demanding immediate monetary transfer."
            return AttackState.FINANCIAL_PRESSURE, "Caller is demanding immediate money transfer to avoid consequence.", claim

        # Check Isolation
        if signals["isolation"] >= 0.4:
            claim = "Caller is forcing the victim into isolation / digital arrest."
            return AttackState.ISOLATION, "Caller is instructing the victim to stay alone and not inform anyone.", claim

        # Check Fear Induction
        if signals["fear"] >= 0.4:
            claim = "Caller is threatening severe legal or physical consequences."
            return AttackState.FEAR_INDUCTION, "Caller is fabricating severe threats or legal consequences.", claim

        # Check Authority Impersonation
        if signals["authority"] >= 0.4:
            claim = "Caller impersonates law enforcement or government official."
            return AttackState.AUTHORITY_IMPERSONATION, "Caller is claiming to represent police, CBI, customs, or bank officials.", claim

        # Check Urgency
        if signals["urgency"] >= 0.4:
            return AttackState.URGENCY, "Caller is creating artificial time pressure.", None

        # Check standalone financial mention
        if signals["financial_pressure"] >= 0.4:
            return AttackState.FINANCIAL_PRESSURE, "Caller is discussing monetary payments or transfers.", None

        # If no new strong signals, maintain previous dangerous state or remain NORMAL
        if current_state != AttackState.NORMAL:
            return current_state, f"Call ongoing in {current_state.value} state.", None

        return AttackState.NORMAL, "Call appears normal so far.", None

    def calculate_risk_score(
        self,
        signals: Dict[str, float],
        deepfake_score: Optional[float] = None
    ) -> float:
        """
        Synthesizes composite risk score (0.0 to 1.0) combining:
        - Deepfake evidence (authenticity)
        - Behavioral / linguistic scam signals (attack progression)
        """
        linguistic_score = (
            signals.get("credential_request", 0.0) * 0.35 +
            signals.get("isolation", 0.0) * 0.25 +
            signals.get("financial_pressure", 0.0) * 0.25 +
            signals.get("fear", 0.0) * 0.20 +
            signals.get("authority", 0.0) * 0.15 +
            signals.get("urgency", 0.0) * 0.15
        )
        linguistic_score = min(1.0, linguistic_score)

        if deepfake_score is not None:
            # Evidence fusion: if synthetic voice is detected alongside scam signals, risk spikes
            if linguistic_score > 0.1 and deepfake_score > 0.5:
                fused = 0.4 * linguistic_score + 0.5 * deepfake_score + 0.2
            else:
                fused = 0.5 * linguistic_score + 0.5 * deepfake_score
            return round(min(1.0, fused), 2)

        return round(linguistic_score, 2)

    def is_critical_event(self, text: str, deepfake_score: Optional[float] = None) -> bool:
        """Fast-path trigger condition (PRD Section 19.1)."""
        lower = text.lower()
        # Immediate match on critical scam keywords
        for kw in settings.CRITICAL_KEYWORDS:
            if kw in lower:
                return True
        # Immediate match if deepfake confidence is exceptionally high
        if deepfake_score is not None and deepfake_score >= 0.85:
            return True
        return False


risk_service = RiskService()
