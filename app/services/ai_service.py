"""
AI Service
Central integration point for the QuizX AI chatbot.
Production-safe logging + clean OpenRouter handling.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests
from flask import current_app


class AIService:
    """QuizX AI service using OpenRouter"""

    DEFAULT_MODEL_NAME = "openrouter/free"
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    # ---------------------------------------------------
    # Internal Helpers
    # ---------------------------------------------------

    @classmethod
    def _get_model_name(cls) -> str:
        return (
            current_app.config.get("AI_MODEL_NAME")
            or os.getenv("AI_MODEL_NAME")
            or cls.DEFAULT_MODEL_NAME
        )

    @classmethod
    def _get_api_key(cls) -> Optional[str]:
        return (
            current_app.config.get("OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

    # ---------------------------------------------------
    # Core Model Call
    # ---------------------------------------------------

    @classmethod
    def _call_model(
        cls,
        message: str,
        mode: Optional[str],
        metadata: Dict[str, Any],
    ) -> str:

        api_key = cls._get_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")

        model_name = cls._get_model_name()

        current_app.logger.info(
            "AIService started | model=%s",
            model_name
        )

        system_prompt = (
            "You are QuizX AI, an educational assistant for quizzes and exam preparation. "
            "Keep answers clear, structured, and exam-focused."
        )

        if mode:
            system_prompt += f" Current mode: {mode}."

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            "temperature": 0.7,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                cls.OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=40,
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Network error: {e}")

        # -------- CLEAN LOGGING (NO BLANK CMD) --------
        try:
            json_preview = response.json()
            clean_preview = str(json_preview).replace("\n", " ")
            current_app.logger.info(
                "OpenRouter [%s] JSON: %s",
                response.status_code,
                clean_preview[:300]
            )
        except Exception:
            clean_text = response.text.replace("\n", " ")
            current_app.logger.info(
                "OpenRouter [%s] RAW: %s",
                response.status_code,
                clean_text[:300]
            )

        # -------- ERROR HANDLING --------

        if response.status_code == 429:
            raise RuntimeError("Rate limit exceeded. Try again shortly.")

        if not response.ok:
            raise RuntimeError(
                f"API Error {response.status_code}: {response.text[:200]}"
            )

        try:
            data = response.json()
        except Exception:
            raise RuntimeError("Invalid JSON response from AI.")

        choices = data.get("choices")
        if not choices:
            raise RuntimeError("No response choices returned.")

        message_data = choices[0].get("message", {})
        content = message_data.get("content", "")

        if not content.strip():
            raise RuntimeError("Empty response from AI.")

        return content.strip()

    # ---------------------------------------------------
    # Public Chat Method
    # ---------------------------------------------------

    @classmethod
    def chat(
        cls,
        message: str,
        mode: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        metadata = metadata or {}
        model_name = cls._get_model_name()

        try:
            reply_text = cls._call_model(message, mode, metadata)
            provider = "openrouter"

        except Exception as exc:
            current_app.logger.error(
                "AIService error: %s — %s",
                type(exc).__name__,
                exc,
            )

            reply_text = (
                "QuizX AI is temporarily unavailable.\n\n"
                f"Reason: {exc}"
            )
            provider = "error"

        return {
            "reply": reply_text,
            "mode": mode or "default",
            "model": model_name,
            "provider": provider,
            "metadata": metadata,
        }