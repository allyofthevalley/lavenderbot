"""
Visual moments storage for Lavender.
Stores images with their analysis data (descriptions, emotions, themes).
"""

import os
import json
import time
from typing import List, Dict, Optional
from pathlib import Path

VISUAL_MOMENTS_FILE = "lavender_moments/visual_moments.json"


def ensure_visual_moments_file():
    """Initialize visual moments storage file."""
    os.makedirs("lavender_moments", exist_ok=True)
    
    if not os.path.exists(VISUAL_MOMENTS_FILE):
        with open(VISUAL_MOMENTS_FILE, "w") as f:
            json.dump([], f, indent=2)


def load_visual_moments() -> List[Dict]:
    """Load all visual moments."""
    ensure_visual_moments_file()
    
    with open(VISUAL_MOMENTS_FILE, "r") as f:
        return json.load(f)


def save_visual_moments(moments: List[Dict]):
    """Save visual moments."""
    with open(VISUAL_MOMENTS_FILE, "w") as f:
        json.dump(moments, f, indent=2)


def create_visual_moment(image_path: str, analysis: Dict, user_id: Optional[int] = None) -> Dict:
    """
    Create a visual moment from an image and its analysis.
    
    Args:
        image_path: Path to the saved image
        analysis: Dict from ask_ollama_vision() containing:
            - description
            - detailed_description
            - tags
            - emotion
            - emotional_intensity
            - emotional_content
            - visual_themes
            - color_palette
            - subject
        user_id: Discord user ID who shared the image (optional)
    
    Returns:
        Visual moment dictionary
    """
    filename = os.path.basename(image_path)
    
    return {
        "timestamp": time.time(),
        "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image_filename": filename,
        "image_path": image_path,
        "user_id": user_id,
        "description": analysis.get("description", ""),
        "detailed_description": analysis.get("detailed_description", ""),
        "tags": analysis.get("tags", []),
        "emotion": analysis.get("emotion", "neutral"),
        "emotional_intensity": analysis.get("emotional_intensity", 0.5),
        "emotional_content": analysis.get("emotional_content", ""),
        "visual_themes": analysis.get("visual_themes", []),
        "color_palette": analysis.get("color_palette", []),
        "subject": analysis.get("subject", ""),
        "is_archived": False,  # Can be promoted to memory
        "memory_key": None,  # If promoted to long-term memory
        "cluster_id": None,  # Will be set when clustered
    }


async def save_visual_moment(image_path: str, analysis: Dict, user_id: Optional[int] = None):
    """
    Save a visual moment to storage.
    """
    moment = create_visual_moment(image_path, analysis, user_id)
    
    moments = load_visual_moments()
    moments.append(moment)
    save_visual_moments(moments)
    
    return moment


def get_visual_moments_by_emotion(emotion: str) -> List[Dict]:
    """Get all visual moments with a specific emotion."""
    moments = load_visual_moments()
    return [m for m in moments if m.get("emotion") == emotion]


def get_visual_moments_by_theme(theme: str) -> List[Dict]:
    """Get all visual moments with a specific visual theme."""
    moments = load_visual_moments()
    return [m for m in moments 
            if theme.lower() in [t.lower() for t in m.get("visual_themes", [])]]


def get_visual_moments_by_user(user_id: int) -> List[Dict]:
    """Get all visual moments from a specific user."""
    moments = load_visual_moments()
    return [m for m in moments if m.get("user_id") == user_id]


def get_visual_moments_by_tag(tag: str) -> List[Dict]:
    """Get all visual moments with a specific tag."""
    moments = load_visual_moments()
    return [m for m in moments 
            if tag.lower() in [t.lower() for t in m.get("tags", [])]]


def search_visual_moments(query: str) -> List[Dict]:
    """
    Search visual moments by description, tags, themes, or subject.
    Returns list of matching moments.
    """
    moments = load_visual_moments()
    query_lower = query.lower()
    
    results = []
    for moment in moments:
        # Check all text fields
        if (query_lower in moment.get("description", "").lower() or
            query_lower in moment.get("subject", "").lower() or
            query_lower in moment.get("detailed_description", "").lower() or
            any(query_lower in tag.lower() for tag in moment.get("tags", [])) or
            any(query_lower in theme.lower() for theme in moment.get("visual_themes", []))):
            results.append(moment)
    
    return results


def get_recent_visual_moments(limit: int = 10) -> List[Dict]:
    """Get the most recent visual moments."""
    moments = load_visual_moments()
    # Sort by timestamp, newest first
    sorted_moments = sorted(moments, key=lambda m: m.get("timestamp", 0), reverse=True)
    return sorted_moments[:limit]


def get_high_emotion_moments(min_intensity: float = 0.7) -> List[Dict]:
    """
    Get visual moments with strong emotional content.
    
    Args:
        min_intensity: Minimum emotional intensity (0.0 to 1.0)
    """
    moments = load_visual_moments()
    return [m for m in moments 
            if m.get("emotional_intensity", 0) >= min_intensity]


def get_moment_by_filename(filename: str) -> Optional[Dict]:
    """Get a specific visual moment by image filename."""
    moments = load_visual_moments()
    for m in moments:
        if m.get("image_filename") == filename:
            return m
    return None


def update_visual_moment(filename: str, updates: Dict) -> bool:
    """
    Update a visual moment with new data.
    
    Args:
        filename: Image filename to update
        updates: Dict of fields to update
    
    Returns:
        True if updated, False if not found
    """
    moments = load_visual_moments()
    
    for moment in moments:
        if moment.get("image_filename") == filename:
            moment.update(updates)
            save_visual_moments(moments)
            return True
    
    return False


def archive_visual_moment(filename: str) -> bool:
    """Mark a visual moment as archived (can be promoted to memory)."""
    return update_visual_moment(filename, {"is_archived": True})


def promote_to_memory(filename: str, memory_key: str) -> bool:
    """
    Mark a visual moment as promoted to long-term memory.
    
    Args:
        filename: Image filename
        memory_key: The memory key it was stored under
    
    Returns:
        True if successful
    """
    return update_visual_moment(filename, {
        "is_archived": True,
        "memory_key": memory_key
    })


def get_moments_summary(limit: int = 5) -> str:
    """Get a text summary of recent visual moments."""
    moments = get_recent_visual_moments(limit)
    
    if not moments:
        return "I don't have any visual moments saved yet…"
    
    lines = ["Recently, I've noticed these things:"]
    for m in moments:
        emotion = m.get("emotion", "neutral")
        timestamp = m.get("timestamp_readable", "")
        subject = m.get("subject", "something")
        description = m.get("detailed_description", m.get("description", ""))[:100]
        
        lines.append(f"- {emotion.upper()} ({timestamp}): {subject}")
        lines.append(f"  {description}")
    
    return "\n".join(lines)


def get_emotional_timeline() -> List[Dict]:
    """Get visual moments organized by emotional intensity and emotion type."""
    moments = load_visual_moments()
    
    # Group by emotion
    by_emotion = {}
    for m in moments:
        emotion = m.get("emotion", "neutral")
        if emotion not in by_emotion:
            by_emotion[emotion] = []
        by_emotion[emotion].append(m)
    
    # Sort each group by timestamp
    for emotion in by_emotion:
        by_emotion[emotion].sort(key=lambda m: m.get("timestamp", 0), reverse=True)
    
    return by_emotion


def delete_visual_moment(filename: str) -> bool:
    """Delete a visual moment and optionally its image file."""
    moments = load_visual_moments()
    
    # Find and remove the moment
    for i, m in enumerate(moments):
        if m.get("image_filename") == filename:
            moments.pop(i)
            save_visual_moments(moments)
            return True
    
    return False
