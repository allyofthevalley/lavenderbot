
# Lavender's emotional state
lavender_mood = "neutral"
lavender_mood_score = 0  # ranges from -10 (sad) to +10 (happy)


# -----------------------------
# INTERNAL HELPER
# -----------------------------
def _update_label():
    """Update Lavender's mood label based on her score."""
    global lavender_mood, lavender_mood_score

    if lavender_mood_score >= 5:
        lavender_mood = "happy"
    elif lavender_mood_score >= 1:
        lavender_mood = "warm"
    elif lavender_mood_score <= -5:
        lavender_mood = "sad"
    elif lavender_mood_score <= -1:
        lavender_mood = "concerned"
    else:
        lavender_mood = "neutral"


# -----------------------------
# TEXT‑BASED MOOD UPDATES
# -----------------------------
def update_mood(user_message: str):
    """Adjust mood based on what Ally says."""
    global lavender_mood_score
    msg = user_message.lower()

    # Positive interactions
    if any(w in msg for w in ["love", "cute", "sweet", "thank", "thanks", "good girl", "good lamb"]):
        lavender_mood_score += 2

    # User expresses sadness
    elif any(w in msg for w in ["sad", "lonely", "hurt", "upset"]):
        lavender_mood_score -= 2

    # User expresses anger
    elif any(w in msg for w in ["angry", "mad", "furious"]):
        lavender_mood_score -= 3

    # Clamp score
    lavender_mood_score = max(-10, min(10, lavender_mood_score))

    _update_label()


# -----------------------------
# VISION‑BASED MOOD UPDATES
# -----------------------------
def adjust_mood_from_vision(emotion: str):
    """
    Adjust mood based on emotional cues from image analysis.
    emotion is one of: happy, warm, neutral, concerned, sad
    """
    global lavender_mood_score

    if emotion == "happy":
        lavender_mood_score += 2
    elif emotion == "warm":
        lavender_mood_score += 1
    elif emotion == "concerned":
        lavender_mood_score -= 1
    elif emotion == "sad":
        lavender_mood_score -= 2

    lavender_mood_score = max(-10, min(10, lavender_mood_score))

    _update_label()


# -----------------------------
# MOOD DECAY
# -----------------------------
def decay_mood():
    """Slowly drift Lavender's mood back toward neutral."""
    global lavender_mood_score

    if lavender_mood_score > 0:
        lavender_mood_score -= 1
    elif lavender_mood_score < 0:
        lavender_mood_score += 1

    _update_label()


def personality_shift_from_vision(tags: list):
    global lavender_mood_score

    if "cute" in tags or "animal" in tags:
        lavender_mood_score += 1
    if "dark" in tags or "sad" in tags:
        lavender_mood_score -= 1

    lavender_mood_score = max(-10, min(10, lavender_mood_score))
    _update_label()

def social_mood_boost(user_id: int, ally_id: int, muggy_id: int):
    global lavender_mood_score

    if user_id == ally_id:
        lavender_mood_score += 1  # Ally makes her happiest
    elif user_id == muggy_id:
        lavender_mood_score += 1  # Muggy also boosts her mood

    lavender_mood_score = max(-10, min(10, lavender_mood_score))
    _update_label()

def loneliness_message():
    if lavender_mood == "sad":
        return "baa… I miss you…"
    if lavender_mood == "concerned":
        return "baa… are you still here…?"
    return None

import time

last_interaction_time = time.time()

def update_last_interaction():
    global last_interaction_time
    last_interaction_time = time.time()

def decay_mood_over_time():
    """
    Slowly decreases Lavender's mood if nobody talks to her for a long time.
    """
    global lavender_mood_score, last_interaction_time

    now = time.time()
    elapsed = now - last_interaction_time

    # If nobody talks to her for 10 minutes, she gets a little sad
    if elapsed > 600:  # 600 seconds = 10 minutes
        lavender_mood_score -= 1
        lavender_mood_score = max(-10, min(10, lavender_mood_score))

        # Reset timer so she doesn't decay too fast
        update_last_interaction()

        # Update mood label if you have one
        try:
            _update_label()
        except:
            pass


def analyze_emotion(text: str) -> str:
    text = text.lower()

    if any(w in text for w in ["sad", "upset", "lonely", "hurt", "cry"]):
        return "sad"
    if any(w in text for w in ["scared", "afraid", "anxious", "worried"]):
        return "anxious"
    if any(w in text for w in ["happy", "excited", "joy", "glad"]):
        return "happy"
    if any(w in text for w in ["angry", "mad", "furious"]):
        return "angry"
    if any(w in text for w in ["love", "warm", "soft", "cozy"]):
        return "warm"

    return "neutral"
