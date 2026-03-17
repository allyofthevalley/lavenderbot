"""
Visual Memory Promotion System for Lavender.
Promotes visual moments and clusters from short-term visual memory to long-term episodic memory.
"""

import json
import asyncio
from typing import Optional, List, Dict
from datetime import datetime
import aiosqlite

DB_PATH = "lavender_memory/lavender_memory.db"


async def promote_visual_moment_to_memory(
    image_filename: str,
    memory_key: str,
    additional_context: str = ""
) -> bool:
    """
    Promote a single visual moment to long-term memory.
    
    Args:
        image_filename: The image filename from visual moments
        memory_key: Key to store in long-term memory
        additional_context: Extra context to store with the memory
    
    Returns:
        True if successful
    """
    from tools.visual_moments import get_moment_by_filename, promote_to_memory
    
    # Get the visual moment
    moment = get_moment_by_filename(image_filename)
    if not moment:
        return False
    
    # Create memory entry
    memory_value = json.dumps({
        "type": "visual_moment",
        "image_filename": image_filename,
        "subject": moment.get("subject"),
        "description": moment.get("detailed_description"),
        "emotion": moment.get("emotion"),
        "emotional_intensity": moment.get("emotional_intensity"),
        "visual_themes": moment.get("visual_themes"),
        "color_palette": moment.get("color_palette"),
        "tags": moment.get("tags"),
        "timestamp": moment.get("timestamp_readable"),
        "additional_context": additional_context
    })
    
    # Store in long-term memory
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO memories (key, value) VALUES (?, ?)",
                (memory_key, memory_value)
            )
            await db.commit()
        
        # Mark as promoted in visual moments
        promote_to_memory(image_filename, memory_key)
        return True
    
    except Exception as e:
        print(f"Error promoting visual moment: {e}")
        return False


async def promote_visual_cluster_to_memory(
    cluster_index: int,
    summary_title: str,
    custom_summary: str = ""
) -> bool:
    """
    Promote a visual cluster (group of similar images) to long-term memory.
    
    Args:
        cluster_index: Index of the cluster in visual clusters
        summary_title: Title for this cluster in memories
        custom_summary: Optional custom summary of the cluster
    
    Returns:
        True if successful
    """
    from tools.vision_clustering import load_clusters, get_cluster_theme
    
    clusters = load_clusters()
    if cluster_index < 0 or cluster_index >= len(clusters):
        return False
    
    cluster = clusters[cluster_index]
    cluster_theme = get_cluster_theme(cluster)
    
    # Create cluster summary if not provided
    if not custom_summary:
        custom_summary = (
            f"A visual theme: {cluster_theme.get('theme_summary', '')}. "
            f"Includes {cluster_theme.get('cluster_size')} images with "
            f"{', '.join(cluster_theme.get('primary_emotions', []))} feelings. "
            f"Uses colors like {', '.join(cluster_theme.get('dominant_colors', []))}."
        )
    
    # Create memory entry
    memory_value = json.dumps({
        "type": "visual_cluster",
        "cluster_index": cluster_index,
        "cluster_size": cluster_theme.get("cluster_size"),
        "images": cluster,
        "themes": cluster_theme.get("primary_themes"),
        "emotions": cluster_theme.get("primary_emotions"),
        "colors": cluster_theme.get("dominant_colors"),
        "summary": custom_summary,
        "timestamp": datetime.now().isoformat()
    })
    
    # Store in long-term memory
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO memories (key, value) VALUES (?, ?)",
                (summary_title, memory_value)
            )
            await db.commit()
        
        return True
    
    except Exception as e:
        print(f"Error promoting cluster: {e}")
        return False


async def get_promoted_visual_memories() -> Dict:
    """
    Retrieve all visual memory promotions from long-term memory.
    Returns dict organized by visual vs text memories.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT key, value FROM memories WHERE value LIKE ?",
                ('%"type":"visual_%',)
            )
            rows = await cursor.fetchall()
        
        visual_memories = {}
        for key, value in rows:
            try:
                data = json.loads(value)
                visual_memories[key] = data
            except:
                pass
        
        return visual_memories
    
    except Exception as e:
        print(f"Error retrieving promoted visual memories: {e}")
        return {}


async def create_thematic_summary(
    theme_name: str,
    visual_moments_list: List[Dict]
) -> Dict:
    """
    Create a thematic summary from multiple visual moments.
    Useful for creating memory entries about recurring themes.
    
    Args:
        theme_name: Name of the theme
        visual_moments_list: List of visual moment dicts
    
    Returns:
        Thematic summary dict
    """
    from collections import Counter
    
    if not visual_moments_list:
        return {}
    
    # Aggregate data across moments
    all_emotions = [m.get("emotion") for m in visual_moments_list]
    all_themes = []
    all_colors = []
    all_tags = []
    
    for m in visual_moments_list:
        all_themes.extend(m.get("visual_themes", []))
        all_colors.extend(m.get("color_palette", []))
        all_tags.extend(m.get("tags", []))
    
    # Find most common elements
    emotion_counts = Counter(all_emotions)
    theme_counts = Counter(all_themes)
    color_counts = Counter(all_colors)
    tag_counts = Counter(all_tags)
    
    return {
        "theme_name": theme_name,
        "moment_count": len(visual_moments_list),
        "primary_emotion": emotion_counts.most_common(1)[0][0] if emotion_counts else "neutral",
        "secondary_emotions": [e[0] for e in emotion_counts.most_common(3)[1:]],
        "common_themes": [t[0] for t in theme_counts.most_common(3)],
        "color_palette": [c[0] for c in color_counts.most_common(3)],
        "common_tags": [t[0] for t in tag_counts.most_common(5)],
        "description": (
            f"A collection of {len(visual_moments_list)} visual moments "
            f"characterized primarily by {emotion_counts.most_common(1)[0][0]} feelings. "
            f"These moments often feature {', '.join([t[0] for t in theme_counts.most_common(2)])} "
            f"themes and use {', '.join([c[0] for c in color_counts.most_common(2)])} colors."
        )
    }


async def suggest_promotions() -> List[Dict]:
    """
    Analyze visual moments and suggest what should be promoted to memory.
    Returns list of promotion suggestions with reasons.
    """
    from tools.visual_moments import (
        get_recent_visual_moments,
        get_high_emotion_moments,
        load_visual_moments
    )
    from tools.vision_clustering import load_clusters
    
    suggestions = []
    
    # Suggest high-emotion moments
    high_emotion = get_high_emotion_moments(min_intensity=0.8)
    if high_emotion:
        suggestions.append({
            "type": "emotional_moments",
            "count": len(high_emotion),
            "reason": f"Found {len(high_emotion)} visual moments with strong emotional content",
            "examples": [m.get("subject") for m in high_emotion[:3]]
        })
    
    # Suggest dense clusters
    clusters = load_clusters()
    large_clusters = [c for c in clusters if len(c) >= 5]
    if large_clusters:
        suggestions.append({
            "type": "large_clusters",
            "count": len(large_clusters),
            "reason": f"Found {len(large_clusters)} visual clusters with 5+ similar images",
            "examples": [f"Cluster with {len(c)} images" for c in large_clusters[:3]]
        })
    
    # Suggest thematic groups
    all_moments = load_visual_moments()
    theme_groups = {}
    for moment in all_moments:
        for theme in moment.get("visual_themes", []):
            if theme not in theme_groups:
                theme_groups[theme] = []
            theme_groups[theme].append(moment)
    
    significant_themes = {k: v for k, v in theme_groups.items() if len(v) >= 3}
    if significant_themes:
        suggestions.append({
            "type": "thematic_patterns",
            "count": len(significant_themes),
            "reason": f"Found {len(significant_themes)} recurring visual themes",
            "examples": list(significant_themes.keys())[:5]
        })
    
    return suggestions


def extract_visual_insight(visual_memory: Dict) -> str:
    """
    Convert a visual memory to a natural language insight.
    Used to describe promoted visual memories in Lavender's voice.
    """
    mem_type = visual_memory.get("type", "unknown")
    
    if mem_type == "visual_moment":
        subject = visual_memory.get("subject", "something")
        emotion = visual_memory.get("emotion", "neutral")
        description = visual_memory.get("description", "")
        
        return (
            f"A moment of {emotion} feelings with {subject}: {description[:100]}…"
        )
    
    elif mem_type == "visual_cluster":
        themes = visual_memory.get("themes", [])
        emotions = visual_memory.get("emotions", [])
        size = visual_memory.get("cluster_size", 0)
        
        return (
            f"A collection of {size} similar images with "
            f"{', '.join(themes)} themes and {', '.join(emotions)} emotions"
        )
    
    return "A visual memory I've saved"
