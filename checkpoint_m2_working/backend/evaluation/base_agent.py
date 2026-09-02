import os
import json
import asyncio
import httpx


class GeminiConfigError(RuntimeError):
    """Raised when the Gemini API key is missing."""


_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class BaseAgent:
    """
    Base class for all LLM-as-a-Judge evaluation agents.
    Calls the Gemini REST API directly with the API key as a query parameter,
    which supports both AIzaSy... and AQ... key formats.

    Required environment variable:
        GEMINI_API_KEY  — your Google Gemini API key
        GEMINI_MODEL    — model name (default: gemini-2.5-flash)
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiConfigError(
                "Gemini API key is not configured. "
                "Set GEMINI_API_KEY in your .env file."
            )
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _generate(self, prompt: str) -> dict:
        """
        Send a prompt to Gemini REST API and parse the JSON response.
        Returns {"score": float, "explanation": str}.
        """
        full_prompt = (
            prompt
            + "\n\nRespond ONLY with a valid JSON object in this exact format:\n"
            + '{"score": <number between 0.0 and 1.0>, "explanation": "<one sentence>"}'
        )
        url = _GEMINI_URL.format(model=self.model)
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 500},
        }
        raw = ""
        try:
            resp = httpx.post(url, params={"key": self.api_key}, json=payload, timeout=30)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            data = json.loads(raw)
            score = max(0.0, min(1.0, float(data["score"])))
            explanation = str(data.get("explanation", ""))
            return {"score": score, "explanation": explanation}

        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Gemini returned an unexpected response format: {e}\nRaw: {raw!r}"
            ) from e

    async def generate(self, prompt: str) -> dict:
        """Async wrapper around _generate — runs in a thread to avoid blocking."""
        return await asyncio.to_thread(self._generate, prompt)
