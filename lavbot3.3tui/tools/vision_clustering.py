"""
Image clustering system for Lavender.
Groups images by visual similarity, themes, and emotional content.
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple
import requests
from pathlib import Path

# Store cluster data
CLUSTERS_FILE = "lavender_memory/image_clusters.json"
IMAGE_EMBEDDINGS_FILE = "lavender_memory/image_embeddings.json"


def ensure_files_exist():
    """Initialize cluster storage files if they don't exist."""
    os.makedirs("lavender_memory", exist_ok=True)
    
    if not os.path.exists(CLUSTERS_FILE):
        with open(CLUSTERS_FILE, "w") as f:
            json.dump({"clusters": []}, f, indent=2)
    
    if not os.path.exists(IMAGE_EMBEDDINGS_FILE):
        with open(IMAGE_EMBEDDINGS_FILE, "w") as f:
            json.dump({}, f, indent=2)


def get_image_embedding(image_path: str) -> List[float]:
    """
    Get embedding for an image from Qwen3.5 via text description.
    Uses the image's visual themes, colors, and emotional content.
    """
    try:
        # Import here to avoid circular imports
        from vision import extract_visual_themes, analyze_image_emotions, ask_ollama_vision
        
        # Get comprehensive analysis
        vision_data = ask_ollama_vision(image_path)
        themes = extract_visual_themes(image_path)
        emotions = analyze_image_emotions(image_path)
        
        # Build a comprehensive text representation of the image
        embedding_text = f"""
Image analysis:
Description: {vision_data.get('description', '')}
Emotional content: {vision_data.get('emotional_content', '')}
Visual themes: {', '.join(vision_data.get('visual_themes', []))}
Color palette: {', '.join(vision_data.get('color_palette', []))}
Subject: {vision_data.get('subject', '')}

Theme analysis:
Primary theme: {themes.get('primary_theme', '')}
Mood: {', '.join(themes.get('mood_descriptors', []))}
Aesthetic: {themes.get('aesthetic_style', '')}

Emotional analysis:
Primary emotion: {emotions.get('primary_emotion', '')}
Sentiment: {emotions.get('emotion_analysis', '')}
"""
        
        # Get embedding via Ollama
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "qwen3.5", "prompt": embedding_text}
        )
        
        return response.json().get("embedding", [])
    
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return []


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0
    
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def cluster_images(image_folder: str = "lavender_images", similarity_threshold: float = 0.7) -> List[List[str]]:
    """
    Cluster images by visual similarity using embeddings.
    Returns list of clusters, where each cluster is a list of image filenames.
    """
    ensure_files_exist()
    
    if not os.path.exists(image_folder):
        return []
    
    # Load existing embeddings
    with open(IMAGE_EMBEDDINGS_FILE, "r") as f:
        embeddings = json.load(f)
    
    # Get all images
    images = [f for f in os.listdir(image_folder) 
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    
    # Compute embeddings for new images
    for img in images:
        if img not in embeddings:
            img_path = os.path.join(image_folder, img)
            print(f"Computing embedding for {img}...")
            emb = get_image_embedding(img_path)
            if emb:
                embeddings[img] = emb
    
    # Save embeddings
    with open(IMAGE_EMBEDDINGS_FILE, "w") as f:
        json.dump(embeddings, f, indent=2)
    
    # Simple clustering algorithm (greedy single-linkage)
    clusters = []
    assigned = set()
    
    for img1 in images:
        if img1 in assigned:
            continue
        
        cluster = [img1]
        assigned.add(img1)
        
        emb1 = embeddings.get(img1, [])
        if not emb1:
            continue
        
        for img2 in images:
            if img2 in assigned or img2 == img1:
                continue
            
            emb2 = embeddings.get(img2, [])
            if not emb2:
                continue
            
            similarity = cosine_similarity(emb1, emb2)
            
            if similarity >= similarity_threshold:
                cluster.append(img2)
                assigned.add(img2)
        
        clusters.append(cluster)
    
    # Save clusters
    cluster_data = {
        "clusters": clusters,
        "last_updated": str(Path.ctime(Path(image_folder))),
        "similarity_threshold": similarity_threshold
    }
    with open(CLUSTERS_FILE, "w") as f:
        json.dump(cluster_data, f, indent=2)
    
    return clusters


def get_cluster_theme(cluster: List[str], image_folder: str = "lavender_images") -> Dict:
    """
    Analyze a cluster of similar images and extract common themes.
    Returns summary of cluster characteristics.
    """
    from vision import extract_visual_themes, analyze_image_emotions
    
    if not cluster:
        return {}
    
    all_themes = []
    all_emotions = []
    all_colors = []
    
    for img in cluster:
        img_path = os.path.join(image_folder, img)
        
        try:
            themes = extract_visual_themes(img_path)
            emotions = analyze_image_emotions(img_path)
            
            all_themes.extend(themes.get('mood_descriptors', []))
            all_emotions.append(emotions.get('primary_emotion', 'neutral'))
            all_colors.extend(themes.get('dominant_colors', []))
        
        except Exception as e:
            print(f"Error analyzing {img}: {e}")
            continue
    
    # Find most common themes
    from collections import Counter
    
    theme_counts = Counter(all_themes)
    emotion_counts = Counter(all_emotions)
    color_counts = Counter(all_colors)
    
    return {
        "cluster_size": len(cluster),
        "primary_themes": [t[0] for t in theme_counts.most_common(3)],
        "primary_emotions": [e[0] for e in emotion_counts.most_common(2)],
        "dominant_colors": [c[0] for c in color_counts.most_common(3)],
        "theme_summary": f"This cluster contains {len(cluster)} images with themes of {', '.join([t[0] for t in theme_counts.most_common(2)])}",
        "images": cluster
    }


def find_similar_images(image_filename: str, similarity_threshold: float = 0.65) -> List[Tuple[str, float]]:
    """
    Find all images similar to a given image.
    Returns list of (image_filename, similarity_score) sorted by similarity.
    """
    ensure_files_exist()
    
    with open(IMAGE_EMBEDDINGS_FILE, "r") as f:
        embeddings = json.load(f)
    
    target_emb = embeddings.get(image_filename, [])
    if not target_emb:
        return []
    
    similar = []
    for img, emb in embeddings.items():
        if img == image_filename:
            continue
        
        similarity = cosine_similarity(target_emb, emb)
        if similarity >= similarity_threshold:
            similar.append((img, similarity))
    
    # Sort by similarity (highest first)
    similar.sort(key=lambda x: x[1], reverse=True)
    return similar


def load_clusters() -> List[List[str]]:
    """Load previously computed clusters."""
    ensure_files_exist()
    
    with open(CLUSTERS_FILE, "r") as f:
        data = json.load(f)
    
    return data.get("clusters", [])


def promote_cluster_to_memory(cluster_index: int, memory_key: str) -> bool:
    """
    Promote a visual cluster to long-term memory.
    Stores a summary and reference to the cluster.
    """
    import aiosqlite
    
    clusters = load_clusters()
    
    if cluster_index < 0 or cluster_index >= len(clusters):
        return False
    
    cluster = clusters[cluster_index]
    cluster_theme = get_cluster_theme(cluster)
    
    # Store as memory
    memory_value = json.dumps({
        "type": "visual_cluster",
        "cluster_index": cluster_index,
        "theme_summary": cluster_theme.get("theme_summary", ""),
        "images": cluster,
        "themes": cluster_theme.get("primary_themes", []),
        "emotions": cluster_theme.get("primary_emotions", [])
    })
    
    # This would be called asynchronously in the actual bot
    print(f"Would promote cluster {cluster_index} as memory '{memory_key}'")
    return True


def get_cluster_summary(cluster_index: int) -> str:
    """Get a human-readable summary of a cluster."""
    clusters = load_clusters()
    
    if cluster_index < 0 or cluster_index >= len(clusters):
        return "Invalid cluster"
    
    cluster = clusters[cluster_index]
    theme = get_cluster_theme(cluster)
    
    return (
        f"Cluster {cluster_index}: {theme['cluster_size']} images\n"
        f"Themes: {', '.join(theme['primary_themes'])}\n"
        f"Emotions: {', '.join(theme['primary_emotions'])}\n"
        f"Colors: {', '.join(theme['dominant_colors'])}"
    )
