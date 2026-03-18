from typing import Optional

from user_db import delete_setting, get_persona_for_user, get_setting, set_setting


PERSONALITY_PROMPT_KEY_PREFIX = "PERSONALITY_PROMPT_"
MAX_CUSTOM_PERSONALITY_CHARS = 1200


def _personality_prompt_key(user_id: int) -> str:
    return f"{PERSONALITY_PROMPT_KEY_PREFIX}{user_id}"

def personality_for(user_id: int):
    """Return a mood/personality style for a given user."""
    persona = get_persona_for_user(user_id)
    if persona == "ally":
        return "affectionate"
    if persona == "muggy":
        return "playful"
    return "neutral"


def get_custom_personality_prompt(user_id: int) -> Optional[str]:
    prompt = get_setting(_personality_prompt_key(user_id))
    if not prompt:
        return None
    cleaned = prompt.strip()
    return cleaned or None


def set_custom_personality_prompt(user_id: int, prompt: str):
    cleaned = (prompt or "").strip()
    if not cleaned:
        raise ValueError("Custom personality prompt cannot be empty.")
    if len(cleaned) > MAX_CUSTOM_PERSONALITY_CHARS:
        raise ValueError(
            f"Custom personality prompt must be {MAX_CUSTOM_PERSONALITY_CHARS} characters or fewer."
        )
    set_setting(_personality_prompt_key(user_id), cleaned)


def clear_custom_personality_prompt(user_id: int) -> bool:
    return delete_setting(_personality_prompt_key(user_id))
