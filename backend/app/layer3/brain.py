from typing import Optional

from google import genai
from google.genai import types

from app.core.config import settings
from app.layer3.schemas import SecurityState


class Layer3Brain:
    """
    GuardianShield Layer 3:
    Uses Gemini to analyze call context and determine
    the current social-engineering attack state.
    """

    MODEL = settings.GEMINI_MODEL

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(api_key=self.api_key)

    def analyze(
        self,
        transcript: str,
        running_summary: str = "",
        recent_events: Optional[list[str]] = None,
    ) -> SecurityState:
        """
        Analyze the latest call context and return a structured
        GuardianShield security state.
        """

        recent_events = recent_events or []

        prompt = self._build_prompt(
            transcript=transcript,
            running_summary=running_summary,
            recent_events=recent_events,
        )

        response = self.client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SecurityState,
                temperature=0.1,
            ),
        )

        if not response.parsed:
            raise ValueError(
                "Gemini returned an empty or invalid structured response."
            )

        return response.parsed

    @staticmethod
    def _build_prompt(
        transcript: str,
        running_summary: str,
        recent_events: list[str],
    ) -> str:
        events_text = "\n".join(
            f"- {event}" for event in recent_events
        ) or "- None"

        return f"""
You are GuardianShield's Layer 3 security reasoning engine.

Your job is to analyze a live phone-call conversation and identify
whether the caller is exhibiting social-engineering or scam behavior.

IMPORTANT:
- Do not assume that every suspicious phrase is a scam.
- Consider the conversation as a sequence of events.
- Use the running summary and recent events as context.
- Detect combinations of signals, not just isolated keywords.
- Be conservative when evidence is weak.
- Never invent facts that are not present in the supplied context.
- Return ONLY the structured SecurityState requested by the system.

Possible attack states:
NORMAL
AUTHORITY_IMPERSONATION
FEAR_INDUCTION
ISOLATION
URGENCY
FINANCIAL_PRESSURE
CREDENTIAL_EXTRACTION
FAMILY_EMERGENCY
PAYMENT_REQUEST

Signal dimensions:
- authority
- fear
- urgency
- isolation
- financial_pressure
- credential_request
- threat

Risk must be between 0.0 and 1.0.

Running summary:
{running_summary or "No previous summary available."}

Recent events:
{events_text}

Latest transcript:
{transcript}

Analyze the latest transcript together with the available context.
Identify the strongest current attack state, estimate the overall risk,
extract the most important active claim if one exists, and recommend
the appropriate next security action.
"""