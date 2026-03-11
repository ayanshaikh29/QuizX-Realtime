"""
AI Service
Central integration point for the QuizX AI chatbot.
Production-safe logging + clean OpenRouter handling.
"""

from __future__ import annotations

import os
import json
import re
from datetime import datetime
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

    VALID_DIFFICULTIES = ("easy", "medium", "hard")
    VALID_QTYPES = ("mcq", "true_false", "short_answer", "checkbox", "mixed")

    @classmethod
    def generate_quiz(
        cls,
        prompt: str,
        difficulty: str = "medium",
        question_type: str = "mcq",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Admin Quiz Generation — supports mcq, true_false, short_answer, checkbox, mixed.
        """
        metadata = metadata or {}
        model_name = cls._get_model_name()

        difficulty = (difficulty or "medium").lower().strip()
        if difficulty not in cls.VALID_DIFFICULTIES:
            difficulty = "medium"

        question_type = (question_type or "mcq").lower().strip()
        if question_type not in cls.VALID_QTYPES:
            question_type = "mcq"

        topic = cls._extract_topic(prompt)
        system_prompt = cls._build_generation_prompt(difficulty, question_type)
        user_prompt = f"Admin Topic: {topic}"

        try:
            reply_text = cls._call_model_internal(user_prompt, system_prompt)
            questions_raw = cls._extract_json_array(reply_text)
            quiz_data = cls._normalize_generated_quiz(
                topic, questions_raw, difficulty, question_type
            )
            return {"success": True, "data": quiz_data, "model": model_name}
        except Exception as exc:
            current_app.logger.error("Admin AI Generation failed: %s", exc)
            return {"success": False, "error": str(exc), "model": model_name}

    @classmethod
    def _build_generation_prompt(cls, difficulty: str, question_type: str) -> str:
        """Build the system prompt based on requested question type."""
        base = (
            "You are an AI question generator for an online quiz platform.\n\n"
            f"Difficulty level: {difficulty}.\n"
            "Rules:\n"
            "- Generate exactly 10 questions.\n"
            "- Questions must be clear, exam-level and concise.\n"
            "- Avoid duplicate questions.\n"
            "- Each question must include a brief explanation.\n"
            "- Output strictly JSON array only (no extra text).\n\n"
        )

        if question_type == "mcq":
            base += (
                "All 10 questions must be MCQ (single choice, 4 options).\n"
                "JSON structure:\n"
                "[\n"
                '  {"type":"mcq","question":"...","option1":"...","option2":"...",'
                '"option3":"...","option4":"...","answer":"Correct option text",'
                '"explanation":"..."}\n'
                "]\n"
            )
        elif question_type == "true_false":
            base += (
                "All 10 questions must be True/False.\n"
                "JSON structure:\n"
                "[\n"
                '  {"type":"true_false","question":"...","answer":"True" or "False",'
                '"explanation":"..."}\n'
                "]\n"
            )
        elif question_type == "short_answer":
            base += (
                "All 10 questions must be Short Answer (one-word or short phrase answer).\n"
                "JSON structure:\n"
                "[\n"
                '  {"type":"short_answer","question":"...","answer":"...",'
                '"explanation":"..."}\n'
                "]\n"
            )
        elif question_type == "checkbox":
            base += (
                "All 10 questions must be Checkbox (multiple correct answers, 4 options).\n"
                "JSON structure:\n"
                "[\n"
                '  {"type":"checkbox","question":"...","option1":"...","option2":"...",'
                '"option3":"...","option4":"...",'
                '"correct_answers":["Correct option text 1","Correct option text 2"],'
                '"explanation":"..."}\n'
                "]\n"
            )
        else:  # mixed
            base += (
                "Generate a mix of question types: MCQ, True/False, Short Answer, Checkbox.\n"
                "Include at least 2 of each type where possible.\n"
                "JSON structure (each item must have a \"type\" field):\n"
                "MCQ: {\"type\":\"mcq\",\"question\":\"...\",\"option1\":\"...\","
                "\"option2\":\"...\",\"option3\":\"...\",\"option4\":\"...\","
                "\"answer\":\"Correct option text\",\"explanation\":\"...\"}\n"
                "True/False: {\"type\":\"true_false\",\"question\":\"...\","
                "\"answer\":\"True\" or \"False\",\"explanation\":\"...\"}\n"
                "Short Answer: {\"type\":\"short_answer\",\"question\":\"...\","
                "\"answer\":\"...\",\"explanation\":\"...\"}\n"
                "Checkbox: {\"type\":\"checkbox\",\"question\":\"...\","
                "\"option1\":\"...\",\"option2\":\"...\",\"option3\":\"...\","
                "\"option4\":\"...\",\"correct_answers\":[\"...\",\"...\"],"
                "\"explanation\":\"...\"}\n"
            )

        base += "\nReturn only the JSON array."
        return base

    @classmethod
    def _extract_topic(cls, prompt: str) -> str:
        """Extract topic from free-form prompt, including {topic} format."""
        text = (prompt or "").strip()
        if not text:
            return "General Knowledge"

        admin_topic_match = re.search(r"Admin Topic\s*:\s*\{?(.+?)\}?\s*$", text, re.IGNORECASE | re.DOTALL)
        if admin_topic_match:
            topic = admin_topic_match.group(1).strip()
            if topic:
                return topic

        brace_match = re.search(r"\{([^{}]{2,})\}", text)
        if brace_match:
            topic = brace_match.group(1).strip()
            if topic:
                return topic

        return text[:120]

    @classmethod
    def _extract_json_array(cls, reply_text: str) -> Any:
        """Extract the first JSON array from model output and parse it."""
        cleaned = (reply_text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        array_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if array_match:
            cleaned = array_match.group(0)

        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("AI output is not a JSON array.")
        return parsed

    @classmethod
    def _normalize_generated_quiz(
        cls, topic: str, questions_raw: Any,
        difficulty: str = "medium", question_type: str = "mcq"
    ) -> Dict[str, Any]:
        """Validate and normalize questions of any type to frontend-compatible payload."""
        if not questions_raw or len(questions_raw) == 0:
            raise ValueError("AI returned no questions.")
        if len(questions_raw) > 20:
            questions_raw = questions_raw[:20]

        questions = []
        for i, item in enumerate(questions_raw, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Question {i} is not a valid object.")

            qtype = str(item.get("type", question_type)).lower().strip()
            if qtype not in ("mcq", "true_false", "short_answer", "checkbox"):
                qtype = "mcq"

            question_text = str(item.get("question", "")).strip()
            explanation = str(item.get("explanation", "")).strip()
            if not question_text:
                raise ValueError(f"Question {i} has no question text.")

            q = {
                "order": i,
                "type": qtype,
                "question": question_text,
                "explanation": explanation,
            }

            if qtype == "mcq":
                opts = cls._extract_4_options(item, i)
                answer_text = str(item.get("answer", "")).strip()
                if answer_text not in opts:
                    raise ValueError(f"Q{i} MCQ answer must match one option.")
                q["options"] = opts
                q["correct_answer"] = chr(65 + opts.index(answer_text))

            elif qtype == "checkbox":
                opts = cls._extract_4_options(item, i)
                raw_answers = item.get("correct_answers", [])
                if isinstance(raw_answers, str):
                    raw_answers = [raw_answers]
                correct = [a.strip() for a in raw_answers if a.strip() in opts]
                if not correct:
                    raise ValueError(f"Q{i} checkbox must have valid correct_answers.")
                q["options"] = opts
                q["correct_answers"] = correct
                q["correct_answer_letters"] = [
                    chr(65 + opts.index(a)) for a in correct
                ]

            elif qtype == "true_false":
                answer = str(item.get("answer", "")).strip().capitalize()
                if answer not in ("True", "False"):
                    raise ValueError(f"Q{i} true_false answer must be True or False.")
                q["correct_answer"] = answer

            elif qtype == "short_answer":
                answer = str(item.get("answer", "")).strip()
                if not answer:
                    raise ValueError(f"Q{i} short_answer must have an answer.")
                q["correct_answer"] = answer

            questions.append(q)

        diff_label = difficulty.capitalize()
        type_label = question_type.upper() if question_type != "mixed" else "Mixed"
        quiz_id = f"QZ-{datetime.utcnow().strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}"
        summary = (
            f"Generated {len(questions)} {diff_label}-level {type_label} question(s) "
            f"for: {topic}. Review and edit before saving."
        )

        return {
            "type": "admin_quiz",
            "quiz_id": quiz_id,
            "title": f"{topic} Quiz",
            "topic": topic,
            "difficulty": diff_label,
            "question_type": question_type,
            "summary": summary,
            "questions": questions,
        }

    @staticmethod
    def _extract_4_options(item: dict, idx: int):
        """Extract 4 named options from an AI response dict."""
        o1 = str(item.get("option1", "")).strip()
        o2 = str(item.get("option2", "")).strip()
        o3 = str(item.get("option3", "")).strip()
        o4 = str(item.get("option4", "")).strip()
        if not all([o1, o2, o3, o4]):
            raise ValueError(f"Q{idx} must have 4 non-empty options.")
        return [o1, o2, o3, o4]

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