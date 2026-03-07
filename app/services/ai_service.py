"""
AI Service
Central integration point for the QuizX AI chatbot.
Production-safe logging + clean OpenRouter handling.
"""

from __future__ import annotations

import os
import json
import re
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
                timeout=60,
            )
        except requests.Timeout:
            raise RuntimeError("AI is taking too long to respond. Please try again.")

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
    # Admin Quiz Generation
    # ---------------------------------------------------

    @classmethod
    def generate_quiz(
        cls,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Specialized method for Admin Quiz Generation.
        Forces the AI to return structured JSON for MCQs.
        """
        metadata = metadata or {}
        model_name = cls._get_model_name()

        system_prompt = (
            "You are QuizX AI, a premium educational assistant. Your goal is to generate high-quality MCQs in a style inspired by Google Gemini: "
            "clear, concise, and with professional explanations.\n\n"
            "STRICT JSON OUTPUT FORMAT:\n"
            "{\n"
            "  \"type\": \"admin_quiz\",\n"
            "  \"quiz_id\": \"string (format: QZ-YYYYMMDD-XXXX)\",\n"
            "  \"title\": \"string (e.g., Python MCQ Set)\",\n"
            "  \"topic\": \"string\",\n"
            "  \"difficulty\": \"string\",\n"
            "  \"summary\": \"A VERY DETAILED Gemini-style formatted text for the chat bubble. Use the following structure EXACTLY:\n\n"
            "### [Title]\n"
            "(Designed for exam-style practice - clear, concise, and with brief explanations)\n"
            "---\n\n"
            "### 1️⃣ [Question Title]\n"
            "Question: [Text]\n\n"
            "A. [Opt]\nB. [Opt]\nC. [Opt]\nD. [Opt]\n\n"
            "Correct Answer: [Letter] – [Text]\n\n"
            "Explanation:\n- [Bullet points explaining why]\n\n"
            "---\n"
            "(Repeat for all questions)\n\n"
            "### Answer Key Summary\n"
            "| # | Correct Option |\n"
            "|---|----------------|\n"
            "| 1 | [Letter] |\n"
            "...\",\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"order\": number,\n"
            "      \"question\": \"string\",\n"
            "      \"options\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],\n"
            "      \"correct_answer\": \"A|B|C|D\",\n"
            "      \"explanation\": \"Brief explanation (used by the builder modal).\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Behavioral Guidelines:\n"
            "- The 'summary' field MUST be the full formatted text that the user will read in the chat bubble. It should look premium and structured.\n"
            "- Ensure the correct_answer is accurate.\n"
            "- Return ONLY the JSON object. No pre-text or post-text."
        )

        try:
            # We use _call_model but with the specialized system prompt logic override
            # To keep it clean, we'll call requests directly or refactor _call_model.
            # Let's refactor _call_model to accept an optional system_prompt.
            reply_text = cls._call_model_internal(prompt, system_prompt)
            
            # Clean up potential markdown code blocks
            json_match = re.search(r'\{.*\}', reply_text, re.DOTALL)
            if json_match:
                reply_text = json_match.group(0)
            
            quiz_data = json.loads(reply_text)
            return {
                "success": True,
                "data": quiz_data,
                "model": model_name
            }

        except Exception as exc:
            current_app.logger.error("Admin AI Generation failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "model": model_name
            }

    @classmethod
    def _call_model_internal(cls, user_message: str, system_prompt: str) -> str:
        """Internal helper for custom system prompts"""
        api_key = cls._get_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")

        payload = {
            "model": cls._get_model_name(),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.4, # Lower temperature for structural stability
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            cls.OPENROUTER_BASE_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if not response.ok:
            raise RuntimeError(f"AI API Error: {response.status_code}")
            
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

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