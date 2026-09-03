"""Gemini LLM Reasoning Engine for GuardianShield Layer 3."""

from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.config import settings
from .schemas import SecurityState
from .prompts import LAYER3_SYSTEM_PROMPT, REASONING_USER_PROMPT_TEMPLATE
from .mock_brain import mock_reasoning_engine

logger = logging.getLogger("guardianshield.layer3.brain")


class GeminiBrain:
    """
    Person A Cognitive Brain implementation connecting to Google Gemini.
    Features automatic fallback to mock/heuristic engine if API key is not set or network fails.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL or "gemini-2.5-flash"
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
        # If no client is available, use heuristic mock engine directly
        if not self._client:
            return mock_reasoning_engine(context)

        # Format user prompt with context payload
        user_prompt = REASONING_USER_PROMPT_TEMPLATE.format(
            user_context_json=json.dumps(context.get("user_context", {}), indent=2),
            call_memory_json=json.dumps(context.get("call_memory", {}), indent=2),
            new_telemetry_json=json.dumps(context.get("new_telemetry", {}), indent=2),
        )

        try:
            # Asynchronously invoke Gemini with system instruction
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config={
                    "system_instruction": LAYER3_SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "temperature": 0.1,  # Low temperature for deterministic threat scoring
                },
            )

            response_text = response.text or "{}"
            # Extract JSON cleanly
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
            # Fallback to local heuristic engine
            return mock_reasoning_engine(context)


# Global brain singleton
gemini_brain = GeminiBrain()


async def evaluate_reasoning(context: Dict[str, Any]) -> SecurityState:
    """Convenience functional interface for Person A reasoning engine."""
    return await gemini_brain.evaluate_context(context)
