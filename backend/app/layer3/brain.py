"""Gemini LLM Reasoning Engine for GuardianShield Layer 3.

Provides both:
  - Layer3Brain: Person A (Anoop) implementation with structured outputs via google-genai
  - GeminiBrain & evaluate_reasoning: Person B (Rajith) implementation with heuristic fallback
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.models.session import AttackState
from .schemas import SecurityState, SecuritySignals
from .prompts import LAYER3_SYSTEM_PROMPT, REASONING_USER_PROMPT_TEMPLATE
from .mock_brain import mock_reasoning_engine

logger = logging.getLogger("guardianshield.layer3.brain")


class Layer3Brain:
    """
    GuardianShield Layer 3 (Person A / Anoop):
    Uses Gemini to analyze call context and determine
    the current social-engineering attack state.
    Includes safe offline/resilience fallback to prevent unhandled test failures.
    """

    MODEL = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")

    def __init__(
        self,
        api_key: Optional[str] = None,
        require_api_key: bool = False,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)

        if require_api_key and not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        self.client = None
        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key.strip())
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}")
                self.client = None

    def analyze(
        self,
        transcript: str,
        running_summary: str = "",
        recent_events: Optional[List[str]] = None,
    ) -> SecurityState:
        """
        Analyze the latest call context and return a structured
        GuardianShield security state.
        """
        recent_events = recent_events or []

        # If client is not available, gracefully use heuristic fallback
        if not self.client:
            heuristic_ctx = {
                "user_context": {},
                "call_memory": {
                    "running_summary": running_summary,
                    "recent_events": recent_events,
                    "current_state": "NORMAL",
                    "risk_score": 0.0,
                },
                "new_telemetry": {
                    "transcript_delta": transcript,
                    "deepfake_score": 0.0,
                },
            }
            return mock_reasoning_engine(heuristic_ctx)

        prompt = self._build_prompt(
            transcript=transcript,
            running_summary=running_summary,
            recent_events=recent_events,
        )

        try:
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SecurityState,
                    temperature=0.1,
                ),
            )

            if response.parsed:
                return response.parsed

            # Fallback if parsed is empty
            if response.text:
                parsed_dict = json.loads(response.text.strip())
                return SecurityState(**parsed_dict)

            raise ValueError("Gemini returned an empty or invalid structured response.")

        except Exception as exc:
            logger.warning(f"Gemini analyze failed ({exc}). Falling back to heuristic reasoning.")
            heuristic_ctx = {
                "user_context": {},
                "call_memory": {
                    "running_summary": running_summary,
                    "recent_events": recent_events,
                },
                "new_telemetry": {
                    "transcript_delta": transcript,
                },
            }
            return mock_reasoning_engine(heuristic_ctx)

    @staticmethod
    def _build_prompt(
        transcript: str,
        running_summary: str,
        recent_events: List[str],
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


class GeminiBrain:
    """
    Person B Cognitive Brain implementation connecting to Google Gemini.
    Features automatic fallback to mock/heuristic engine if API key is not set or network fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initializes the google-genai client if API key is present."""
        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key.strip())
                logger.info(f"Initialized Gemini Client with model '{self.model_name}'")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai client: {e}. Falling back to heuristic mock.")
                self._client = None
        else:
            self._client = None

    async def evaluate_context(self, context: Dict[str, Any]) -> SecurityState:
        """
        Evaluates the compact reasoning context using Gemini or resilient heuristic fallback.
        """
        if not self._client:
            return mock_reasoning_engine(context)

        user_prompt = REASONING_USER_PROMPT_TEMPLATE.format(
            user_context_json=json.dumps(context.get("user_context", {}), indent=2),
            call_memory_json=json.dumps(context.get("call_memory", {}), indent=2),
            new_telemetry_json=json.dumps(context.get("new_telemetry", {}), indent=2),
        )

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config={
                    "system_instruction": LAYER3_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )

            response_text = response.text or "{}"
            cleaned_text = response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]

            parsed_data = json.loads(cleaned_text.strip())
            return SecurityState(**parsed_data)

        except Exception as exc:
            logger.warning(f"Gemini evaluation failed ({exc}). Falling back to heuristic reasoning.")
            return mock_reasoning_engine(context)


# Global brain singleton
gemini_brain = GeminiBrain()


async def evaluate_reasoning(context: Dict[str, Any]) -> SecurityState:
    """Convenience functional interface for Person A reasoning engine."""
    return await gemini_brain.evaluate_context(context)
