import time
import json
import os
from memory import remember
from mood import analyze_emotion
import aiohttp
from config import get_ollama_base_url

# -----------------------------
# Embeddings via Ollama HTTP API
# -----------------------------
async def embed_text(text: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{get_ollama_base_url()}/api/embed",
                json={"model": "nomic-embed-text", "input": text}
            ) as response:
                if response.status != 200:
                    print(f"DEBUG: Ollama API error: {response.status}")
                    return [0.0] * 768  # Return a zero vector as fallback
                data = await response.json()
                if "embedding" in data:
                    return data["embedding"]
                elif "embeddings" in data and len(data["embeddings"]) > 0:
                    return data["embeddings"][0]
                else:
                    print(f"DEBUG: Ollama response: {data}")
                    return [0.0] * 768  # Fallback
    except Exception as e:
        print(f"DEBUG: Embedding failed: {e}")
        return [0.0] * 768  # Return zero vector as fallback

# Folder for episodic memories
os.makedirs("lavender_moments", exist_ok=True)
MOMENT_FILE = "lavender_moments/moments.json"

# -----------------------------
# Load + Save Moment Storage
# -----------------------------
def load_moments():
    if not os.path.exists(MOMENT_FILE):
        return []
    with open(MOMENT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_moments(data):
    with open(MOMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# -----------------------------
# Determine if a message is meaningful
# -----------------------------
def is_meaningful(text: str) -> bool:
    text_lower = text.lower()

    emotional_keywords = [
        "scared", "sad", "happy", "excited", "worried", "anxious",
        "proud", "lonely", "overwhelmed", "love", "hate", "afraid"
    ]

    identity_keywords = [
        "i am", "i'm", "my favorite", "i like", "i dislike",
        "i prefer", "i want", "i wish", "i hope"
    ]

    relationship_keywords = [
        "muggy", "partner", "friend", "family", "you mean a lot",
        "i care", "i trust", "i feel close"
    ]

    goal_keywords = [
        "goal", "dream", "plan", "future", "learn", "become", "improve"
    ]

    for group in (emotional_keywords, identity_keywords, relationship_keywords, goal_keywords):
        if any(word in text_lower for word in group):
            return True

    if len(text.split()) > 12:
        return True

    return False

# -----------------------------
# Create a moment object
# -----------------------------
async def create_moment(user_message: str, lavender_reply: str, emotion: str = "neutral"):
    ts = time.time()
    readable = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

    return {
        "timestamp": ts,
        "timestamp_readable": readable,
        "user_message": user_message,
        "lavender_reply": lavender_reply,
        "emotion": emotion,
        "embedding": await embed_text(user_message),
    }

# -----------------------------
# Save a meaningful moment
# -----------------------------
async def save_moment_if_important(user_message: str, lavender_reply: str):
    if not is_meaningful(user_message):
        return

    try:
        emotion = analyze_emotion(user_message)
    except:
        emotion = "neutral"

    moment = await create_moment(user_message, lavender_reply, emotion)

    moments = load_moments()
    moments.append(moment)
    save_moments(moments)

    summary = f"Moment: {user_message[:80]}..."
    # Do not write moments directly into long-term memory here.
    # Moments are stored in episodic storage only; promotion happens via clustering.

# -----------------------------
# Semantic Search
# -----------------------------
async def semantic_search_moments(query: str, top_k=5):
    query_vec = await embed_text(query)
    moments = load_moments()

    scored = []
    for m in moments:
        emb = m.get("embedding")
        if not emb:
            continue

        dot = sum(a*b for a, b in zip(query_vec, emb))
        scored.append((dot, m))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [m for _, m in scored[:top_k]]
