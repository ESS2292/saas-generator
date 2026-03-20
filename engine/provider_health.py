import os

from dotenv import load_dotenv
from openai import APIConnectionError, AuthenticationError, OpenAI, RateLimitError


def _message_from_exception(exc):
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error") or {}
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
    return str(exc)


def check_openai_generation_access():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "ok": False,
            "status": "missing_key",
            "message": "OPENAI_API_KEY is not configured.",
        }

    client = OpenAI(api_key=api_key)
    try:
        client.responses.create(
            model="gpt-4o-mini",
            input="ping",
            max_output_tokens=1,
        )
        return {
            "ok": True,
            "status": "ready",
            "message": "OpenAI generation access is ready.",
        }
    except AuthenticationError as exc:
        return {
            "ok": False,
            "status": "invalid_key",
            "message": _message_from_exception(exc),
        }
    except RateLimitError as exc:
        message = _message_from_exception(exc)
        status = "insufficient_quota" if "insufficient_quota" in message else "rate_limited"
        return {
            "ok": False,
            "status": status,
            "message": message,
        }
    except APIConnectionError as exc:
        return {
            "ok": False,
            "status": "connection_error",
            "message": _message_from_exception(exc),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "ok": False,
            "status": "unknown_error",
            "message": str(exc),
        }
