import time
from moments import load_moments, save_moments, embed_text, save_moment_if_important
from memory import remember
import math
import os
import json
import time

IMAGE_FOLDER = "lavender_images"
FAVORITES_FILE = "favorites.json"
IMAGE_MAX_AGE_DAYS = 30
CLUSTER_PROMOTION_THRESHOLD = 5


def load_favorites():
    if not os.path.exists(FAVORITES_FILE):
        return {"images": []}
    with open(FAVORITES_FILE, "r") as f:
        return json.load(f)


def save_favorites(data):
    with open(FAVORITES_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def prune_images():
    """
    Deletes images that:
    - are older than 30 days
    - AND are not referenced by any moment
    - AND are not in favorites.json
    """

    # Load favorites
    favorites = load_favorites().get("images", [])

    # Load all moments to see which images are referenced
    moments = load_moments()  # <-- correct function

    referenced_images = set()
    for m in moments:
        if "image_path" in m and m["image_path"]:
            referenced_images.add(m["image_path"])

    # Time threshold
    now = time.time()
    max_age = IMAGE_MAX_AGE_DAYS * 24 * 60 * 60

    # Ensure folder exists
    if not os.path.exists(IMAGE_FOLDER):
        return

    for filename in os.listdir(IMAGE_FOLDER):
        path = os.path.join(IMAGE_FOLDER, filename)

        # Skip non-files
        if not os.path.isfile(path):
            continue

        # Skip favorites
        if path in favorites:
            continue

        # Skip referenced images
        if path in referenced_images:
            continue

        # Check age
        age = now - os.path.getmtime(path)
        if age > max_age:
            try:
                os.remove(path)
                print(f"Pruned old image: {path}")
            except Exception as e:
                print(f"Failed to delete {path}: {e}")
# -----------------------------
# Helper: cosine similarity
# -----------------------------
def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x*x for x in a))
    mag_b = math.sqrt(sum(x*x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0
    return dot / (mag_a * mag_b)

# -----------------------------
# 1. Delete old moments
# -----------------------------
def delete_old_moments(days=90):
    cutoff = time.time() - (days * 86400)
    moments = load_moments()
    kept = [m for m in moments if m["timestamp"] >= cutoff]
    save_moments(kept)
    return len(moments) - len(kept)

# -----------------------------
# 2. Remove duplicates
# -----------------------------
def remove_duplicates(threshold=0.97):
    moments = load_moments()
    new_list = []

    for m in moments:
        if not m.get("embedding"):
            continue
        is_duplicate = False
        for existing in new_list:
            if not existing.get("embedding"):
                continue
            sim = cosine(m["embedding"], existing["embedding"])
            if sim >= threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            new_list.append(m)

    save_moments(new_list)
    return len(moments) - len(new_list)

# -----------------------------
# 3. Merge similar moments
# -----------------------------
async def merge_similar_moments(threshold=0.85):
    moments = load_moments()
    merged = []
    used = set()

    for i, m in enumerate(moments):
        if i in used or not m.get("embedding"):
            continue

        cluster = [m]
        used.add(i)

        for j, other in enumerate(moments):
            if j in used or not other.get("embedding"):
                continue
            sim = cosine(m["embedding"], other["embedding"])
            if sim >= threshold:
                cluster.append(other)
                used.add(j)

        combined_text = " | ".join(c["user_message"] for c in cluster)

        if len(cluster) >= CLUSTER_PROMOTION_THRESHOLD:
            # Promote cluster to long-term memory as a theme summary
            summary_text = f"Summary of {len(cluster)} similar moments: {combined_text[:500]}..."
            key = f"theme_{int(time.time())}"
            await remember(key, summary_text)

            # Also keep a condensed summary in episodic storage
            summary_moment = {
                "timestamp": max(c["timestamp"] for c in cluster),
                "user_message": summary_text,
                "lavender_reply": "(promoted summary)",
                "emotion": cluster[0]["emotion"],
                "embedding": await embed_text(combined_text)
            }
            merged.append(summary_moment)
        else:
            # Create a summary moment (not promoted)
            summary = {
                "timestamp": max(c["timestamp"] for c in cluster),
                "user_message": f"Summary of {len(cluster)} similar moments: {combined_text[:200]}...",
                "lavender_reply": "(merged summary)",
                "emotion": cluster[0]["emotion"],
                "embedding": await embed_text(combined_text)
            }
            merged.append(summary)

    save_moments(merged)
    return len(moments) - len(merged)

# -----------------------------
# 4. Summarize clusters into chapters
# -----------------------------
def summarize_clusters():
    moments = load_moments()
    if len(moments) < 10:
        return 0

    combined = " ".join(m["user_message"] for m in moments)
    chapter_summary = combined[:500] + "..."

    # Save chapter to main memory DB
    key = f"chapter_{int(time.time())}"
    text = f"Chapter summary: {chapter_summary}"
    return key, text

# -----------------------------
# 5. Master pruning function
# -----------------------------
async def prune_all():
    deleted = delete_old_moments()
    deduped = remove_duplicates()
    merged = await merge_similar_moments()

    chapter = summarize_clusters()
    if chapter:
        # Store chapter summaries as episodic moments, not direct long-term memory.
        key, text = chapter
        await save_moment_if_important(text, "")

    return deleted, deduped, merged
