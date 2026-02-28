"""
AI Service
Central integration point for the QuizX AI chatbot.

This module is intentionally framework-agnostic and exposes a small
Python API that HTTP routes can call. The actual LLM integration is
kept behind this service so it can be swapped or extended later
without touching route code.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import os
from flask import current_app


class AIService:
    """
    QuizX AI service abstraction.

    For now this uses a safe local fallback implementation so that the
    app runs even if no external AI provider is configured. The
    integration with a real LLM (e.g. openai/gpt-oss-120b:free) can be
    implemented later inside this class.
    """

    DEFAULT_MODEL_NAME = "openai/gpt-oss-120b:free"

    @classmethod
    def _get_model_name(cls) -> str:
        """
        Return the configured model name, falling back to a sensible default.
        """
        return current_app.config.get(
            "AI_MODEL_NAME",
            os.getenv("AI_MODEL_NAME", cls.DEFAULT_MODEL_NAME),
        )

    @classmethod
    def _get_api_key(cls) -> Optional[str]:
        """
        Look up an API key from the Flask config or environment.

        This does NOT validate or use the key yet; it simply allows the
        rest of the app to be wired without failing if no key is set.
        """
        return current_app.config.get(
            "OPENAI_API_KEY",
            os.getenv("OPENAI_API_KEY"),
        )

    @classmethod
    def chat(
        cls,
        message: str,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        High-level chat API used by HTTP routes.

        Args:
            message: Raw user message from the client.
            mode: Optional logical mode (e.g. 'MCQ_GENERATION_TOPIC').
            metadata: Optional extra context like user id, quiz id, etc.

        Returns:
            A dict that can be returned directly as JSON.
        """
        metadata = metadata or {}
        model_name = cls._get_model_name()
        api_key = cls._get_api_key()

        # NOTE:
        # Real LLM integration should go here. For now we deliberately
        # keep a deterministic, local fallback so the endpoint works
        # without external services or extra dependencies.
        #
        # When wiring a real provider, prefer:
        # - Using model_name and api_key from above.
        # - Keeping network calls and provider-specific code inside this method
        #   or helpers in this module.

        base_reply = (
            "QuizX AI is wired but no external AI provider is configured yet. "
            "This is a placeholder response that echoes your message."
        )

        if api_key:
            # Even if an API key is present, we still use the safe local
            # fallback until a provider is implemented.
            provider = "configured-placeholder"
        else:
            provider = "local-placeholder"

        return {
            "reply": f"{base_reply} You said: {message}",
            "mode": mode or "default",
            "model": model_name,
            "provider": provider,
            "metadata": metadata,
        }

