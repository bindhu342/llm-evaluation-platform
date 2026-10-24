import asyncio
import json
import os

import httpx
from dotenv import load_dotenv


load_dotenv()


class GeminiConfigError(RuntimeError):
    """Raised when the Gemini API key is missing."""


_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)


class BaseAgent:
    """
    Base class for all LLM-as-a-Judge evaluation agents.

    Required environment variables:
        GEMINI_API_KEY
        GEMINI_MODEL (optional)
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise GeminiConfigError(
                "Gemini API key is not configured. "
                "Set GEMINI_API_KEY in your .env file."
            )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-2.5-flash",
        )

    def _generate(self, prompt: str) -> dict:
        """Send a prompt to Gemini REST API and parse the JSON response."""

        full_prompt = (
            prompt
            + "\n\nRespond ONLY with one valid JSON object. "
            "Follow the exact fields requested in the prompt. "
            "Do not add markdown, code fences, or extra text."
        )

        url = _GEMINI_URL.format(model=self.model)

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt,
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 500,
                "responseMimeType": "application/json",
            },
        }

        raw = ""

        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=60,
            )

            response.raise_for_status()

            response_json = response.json()
            candidates = response_json.get("candidates", [])

            if not candidates:
                raise ValueError(
                    f"Gemini returned no candidates: {response_json}"
                )

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            if not parts:
                raise ValueError(
                    f"Gemini returned no response parts: {response_json}"
                )

            raw = parts[0].get("text", "").strip()

            if not raw:
                raise ValueError(
                    f"Gemini returned empty text: {response_json}"
                )

            if raw.startswith("```"):
                raw = raw.split("```", 2)[1].strip()

                if raw.lower().startswith("json"):
                    raw = raw[4:].strip()

            data = json.loads(raw)

            if not isinstance(data, dict):
                raise ValueError(
                    "Gemini response is not a JSON object."
                )

            if "score" not in data:
                raise KeyError(
                    "Missing 'score' field in Gemini response."
                )

            score = max(
                0.0,
                min(1.0, float(data["score"])),
            )

            # Preserve every field returned by the agent.
            # This is required for structured outputs such as:
            # addressed_aspects
            # missing_aspects
            # flagged_claims
            # status
            result = dict(data)

            # Always normalize the score.
            result["score"] = score

            # Always provide an explanation field.
            result["explanation"] = str(
                result.get("explanation", "")
            ).strip()

            return result

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                "Gemini API request failed with "
                f"HTTP {exc.response.status_code}: "
                f"{exc.response.text}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Gemini network request failed: {exc}"
            ) from exc

        except (
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError(
                "Gemini returned an unexpected response format: "
                f"{exc}\nRaw response: {raw!r}"
            ) from exc

    async def generate(self, prompt: str) -> dict:
        """Run the synchronous Gemini request in a background thread."""

        return await asyncio.to_thread(
            self._generate,
            prompt,
        )