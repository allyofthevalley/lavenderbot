import os
from dotenv import load_dotenv

from user_db import get_persona_for_user, get_setting, is_allowed_user

load_dotenv()

# -----------------------------------------------------------------------------
# Token / secret accessors (stored in user.db, but fall back to env vars for
# backwards compatibility).
# -----------------------------------------------------------------------------

def get_discord_token() -> str:
    return get_setting("DiscordToken") or os.getenv("DISCORD_TOKEN") or ""


def get_openweather_key() -> str:
    return get_setting("OPENWEATHER_KEY") or os.getenv("OPENWEATHER_KEY") or ""


def get_news_key() -> str:
    return get_setting("NEWS_API_KEY") or os.getenv("NEWS_API_KEY") or ""


# -----------------------------------------------------------------------------
# User/permission helpers
# -----------------------------------------------------------------------------

def who_is(user_id: int) -> str:
    """Return a persona string for a user ID (e.g. ally / muggy)."""
    persona = get_persona_for_user(user_id)
    return persona or "someone else"


# -----------------------------------------------------------------------------
# Application metadata (no PII)
# -----------------------------------------------------------------------------

lavender_mood = "neutral"
lavender_mood_score = 0  # ranges from -10 (sad) to +10 (happy)

TIMEZONE = "America/Vancouver"
