from user_db import get_persona_for_user
from mood import update_last_interaction, decay_mood_over_time

def personality_for(user_id: int):
    """Return a mood/personality style for a given user."""
    persona = get_persona_for_user(user_id)
    if persona == "ally":
        return "affectionate"
    if persona == "muggy":
        return "playful"
    return "neutral"
