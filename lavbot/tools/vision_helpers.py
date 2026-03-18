import os
import json
from tools.vision import ask_ollama_vision
from memory import remember_image, search_images_by_tag
from moments import save_moment_if_important
from mood import adjust_mood_from_vision, personality_shift_from_vision


def save_image_locally(filename: str, image_bytes: bytes) -> str:
    os.makedirs("lavender_images", exist_ok=True)
    filepath = f"lavender_images/{filename}"
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return filepath


def format_tags(tags):
    return ", ".join(tags) if tags else ""


async def store_image_memory(filename: str, description: str, tags: list):
    # Store image-related text as episodic moments, not long-term memory.
    await save_moment_if_important(description, "")
    if tags:
        await save_moment_if_important(", ".join(tags), "")
    await remember_image(filename, tags, description)


async def process_image(filename: str, image_bytes: bytes):
    filepath = save_image_locally(filename, image_bytes)

    result = ask_ollama_vision(filepath)

    description = result.get("description", "I saw something, but I'm not sure what…")
    tags = result.get("tags", [])
    emotion = result.get("emotion", "neutral")

    # Mood integration
    adjust_mood_from_vision(emotion)

    # Personality shift based on tags
    personality_shift_from_vision(tags)

    # Memory storage
    await store_image_memory(filename, description, tags)

    return description


async def search_images_with_tag(tag: str):
    rows = await search_images_by_tag(tag)
    if not rows:
        return None

    return [filename for filename, tags in rows]
