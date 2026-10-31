"""AI health-risk prediction.

Uses the Google Gemini API when GEMINI_API_KEY is set (free tier, no billing needed),
otherwise the Anthropic Messages API when ANTHROPIC_API_KEY is set.
"""
import os
from datetime import date, datetime

import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

TIMEOUT_SECONDS = 30

SYSTEM_PROMPT = (
    "You are a clinical decision-support assistant. Given a patient's age and three blood "
    "test values, state the most likely health condition or disease risk (for example "
    "diabetes or pre-diabetes, anaemia, high cholesterol / cardiovascular risk), or say the "
    "results look within normal range. Reply with at most two short sentences of plain text, "
    "no markdown. This is a screening aid, not a diagnosis."
)


class AIServiceError(Exception):
    pass


def _age(dob_text):
    dob = datetime.strptime(dob_text, "%d/%m/%Y").date()
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _build_prompt(dob, glucose, haemoglobin, cholesterol):
    return (
        f"Age: {_age(dob)} years\n"
        f"Fasting glucose: {glucose} mg/dL\n"
        f"Haemoglobin: {haemoglobin} g/dL\n"
        f"Total cholesterol: {cholesterol} mg/dL"
    )


def _call_gemini(api_key, prompt):
    resp = requests.post(
        GEMINI_URL.format(model=GEMINI_MODEL),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    candidates = resp.json().get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def _call_anthropic(api_key, prompt):
    resp = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 200,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    blocks = resp.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


def predict_remarks(dob, glucose, haemoglobin, cholesterol):
    """Return a short AI-generated remark. Raises AIServiceError on any failure."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not gemini_key and not anthropic_key:
        raise AIServiceError("No API key set (GEMINI_API_KEY or ANTHROPIC_API_KEY).")

    prompt = _build_prompt(dob, glucose, haemoglobin, cholesterol)
    try:
        if gemini_key:
            text = _call_gemini(gemini_key, prompt)
        else:
            text = _call_anthropic(anthropic_key, prompt)
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else "unknown"
        raise AIServiceError(f"AI API returned HTTP {code}.") from exc
    except requests.RequestException as exc:
        raise AIServiceError(f"AI API request failed: {exc.__class__.__name__}") from exc
    except ValueError as exc:
        raise AIServiceError("AI API returned an unreadable response.") from exc

    if not text:
        raise AIServiceError("AI API returned an empty response.")
    return text