# Lavender Bot - Qwen 3.5 Upgrade - v3.0

## 🎉 Major Changes

### Model Migration
- **Previous**: Llama 3.1 (text) + Llava (vision)
- **Now**: Qwen 3.5 for all tasks (text + multimodal vision)
- **Files Updated**: bot.py, moments.py, tools/vision.py

### New Visual & Memory Features

Lavender can now:

1. **Store Visual Moments** 📸
   - Automatically saves every image with comprehensive analysis
   - Stores: description, emotional content, visual themes, colors, subject
   - Found in: `lavender_moments/visual_moments.json`

2. **Cluster Images by Similarity** 🎨
   - Groups similar images using visual embeddings
   - Uses cosine similarity to find related images
   - Computes cluster themes automatically
   - Command: `!vcluster`

3. **Summarize Visual Themes** ✨
   - Analyzes dominant visual characteristics
   - Extracts mood, aesthetic, colors, composition
   - Creates summaries of image clusters
   - Commands: `!vtheme [cluster#]`

4. **Promote Visual Clusters to Memory** 💾
   - Save important visual collections to long-term memory
   - Links images to memory keys
   - Command: `!vpromote [index] [memory_key]`

5. **Describe Pictures in Natural Language** 💬
   - Uses Qwen 3.5 for detailed, poetic descriptions
   - Writes in Lavender's voice
   - Includes emotional insights
   - Shared in image responses and `!vmoments`

6. **Understand Emotional Content** 😊
   - Analyzes emotions conveyed by images
   - Tracks emotional intensity (0-1 scale)
   - Creates emotional timelines
   - Command: `!vemotions`

## 📋 New Commands

### Visual Moments
- `!vmoments [limit]` - Show recent visual moments I've saved
- `!visearch <query>` - Search my visual moments by description/theme/tag
- `!vemotions` - Show emotional timeline of visual moments

### Image Clustering
- `!vcluster` - Analyze and cluster similar images by similarity
- `!vtheme [cluster_num]` - Show the visual theme summary of a cluster
- `!vsuggestions` - Get AI suggestions for what to promote to memory

### Visual Memory Integration
- `!vpromote <index> <memory_key>` - Promote a visual moment to long-term memory

## 🗂️ New Files Created

### Core Vision Modules
1. **tools/vision_clustering.py**
   - Image embedding computation
   - Similarity-based clustering algorithm
   - Cluster theme extraction
   - Functions: `cluster_images()`, `get_cluster_theme()`, `find_similar_images()`

2. **tools/visual_moments.py**
   - Visual moment creation and storage
   - Search and filtering functions
   - Emotional timeline tracking
   - Storage file: `lavender_moments/visual_moments.json`

3. **tools/visual_memory.py**
   - Promotion from visual moments to long-term memory
   - Thematic summary creation
   - Promotion suggestions
   - Integration with existing memory database

### Enhanced Existing Modules
1. **tools/vision.py** - Extended with:
   - `analyze_image_emotions()` - Deep emotional analysis
   - `extract_visual_themes()` - Theme and aesthetic extraction
   - Enhanced `ask_ollama_vision()` with more detailed fields

## 🔄 Integration Points

### Image Handling Pipeline
```
User sends image
    ↓
Qwen analyzes: description, emotion, themes, colors, subject
    ↓
Saves visual moment to lavender_moments/visual_moments.json
    ↓
Lavender responds with emotional-aware description in her voice
    ↓
Optional: Cluster analysis runs in background
    ↓
User can promote to memory, search, or view clusters
```

### Memory Storage Structure
- **Text memories**: `lavender_memory/lavender_memory.db` (existing)
- **Visual moments**: `lavender_moments/visual_moments.json` (new)
- **Image embeddings**: `lavender_memory/image_embeddings.json` (new)
- **Clusters**: `lavender_memory/image_clusters.json` (new)

## 🚀 Usage Examples

### Basic Image Interaction
```
User: [sends image]
Lavender: "baa... I see a cozy autumn scene with warm lighting. 
It makes me feel peaceful and romantic... 🍂 The colors are golden and deep red."
```

### Cluster and Theme Analysis
```
!vcluster
→ "I found 5 visual groups:
   - Cluster 0: 3 images
   - Cluster 1: 7 images
   - Cluster 2: 2 images"

!vtheme 1
→ "Cluster 1: 7 images
   Themes: warm, cozy, natural
   Emotions: peaceful, inspired
   Colors: golden, brown, cream"
```

### Visual Memory Promotion
```
!vsuggestions
→ "Things I think are worth remembering:
   - Found 3 visual moments with strong emotional content
   - Found 2 visual clusters with 5+ similar images
   - Found natural as a recurring visual theme"

!vpromote 0 aesthetic_cozy_vibes
→ "✨ I'll remember this as aesthetic_cozy_vibes!"
```

### Searching Visual Memories
```
!visearch "warm colors"
→ "Found 4 visual moments:
   - Sunset over water: A warm golden moment...
   - Autumn leaves: Rich amber tones...
   - Fireplace glow: Cozy orange light...
   - Sunset painting: Oranges and reds..."

!vemotions
→ "Emotional themes in my visual memories:
   - PEACEFUL: 5 moments
   - WARM: 8 moments
   - PLAYFUL: 3 moments
   - INSPIRED: 6 moments"
```

## ⚙️ System Requirements

### Python Packages
- `numpy` - for similarity calculations
- `aiosqlite` - already installed
- `discord.py` - already installed
- `requests` - already installed

### Ollama Models
Ensure you have Qwen 3.5 running:
```bash
ollama run qwen3.5
```

The bot will use Qwen 3.5 for:
- All chat responses (`ollama_chat`)
- All image analysis (`ask_ollama_vision`)
- Embedding generation for clustering (`embed_text`)

## 📊 Database Structure

### visual_moments.json Format
```json
{
  "timestamp": 1234567890,
  "timestamp_readable": "2026-03-04 12:34:56",
  "image_filename": "image.jpg",
  "image_path": "lavender_images/image.jpg",
  "user_id": 638910328020795434,
  "description": "A short description",
  "detailed_description": "A poetic, longer description",
  "tags": ["tag1", "tag2"],
  "emotion": "peaceful",
  "emotional_intensity": 0.8,
  "emotional_content": "The soft lighting conveys peace",
  "visual_themes": ["cozy", "warm", "natural"],
  "color_palette": ["golden", "cream", "brown"],
  "subject": "autumn scene",
  "is_archived": false,
  "memory_key": null,
  "cluster_id": null
}
```

## 🔧 Configuration

Model settings are in bot.py:
```python
def ollama_chat(prompt: str):
    # Uses "qwen3.5" model

# In tools/vision.py:
VISION_MODEL = "qwen3.5"

# In moments.py:
def embed_text(text):
    # Uses "qwen3.5" for embeddings
```

Change model names if needed, but Qwen 3.5 is recommended for full multimodal support.

## 🐛 Troubleshooting

### Images not clustering
- Ensure Qwen 3.5 is running: `ollama run qwen3.5`
- Check that `lavender_memory/` directory exists
- Try `!vcluster` again - embeddings are computed on-demand

### Emotional analysis missing
- Rerun `!vcluster` to trigger theme extraction
- Check console for embedding errors
- Ensure Qwen 3.5 can process images (verify with `ollama list`)

### Memory promotion failing
- Check `lavender_memory/lavender_memory.db` exists
- Ensure correct image index from `!vmoments`
- Verify memory_key doesn't already exist

## 📝 Version History

**v3.0 (3/4/2026)** - Qwen 3.5 Upgrade ✨
- Full multimodal vision integration
- Image clustering & theme analysis
- Visual memory system
- Emotional content understanding

**v2.3 (3/3/2026)**
- Added cluster functionality
- Optimized moment & memory integration

---

**Ready to chat with Qwen! Use `!guji` to see all available commands.** 🌸
