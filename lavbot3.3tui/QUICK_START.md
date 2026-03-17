# 🌸 Lavender Bot - Qwen 3.5 Quick Start Guide

## ✅ Pre-Flight Checklist

### 1. Ensure Qwen 3.5 is Running
```bash
ollama run qwen3.5
```
Keep this terminal open while the bot runs.

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install numpy discord.py aiosqlite requests python-dotenv textual
```

### 3. Verify Ollama is Accessible
Test that Qwen can be reached:
```bash
curl http://localhost:11434/api/tags
```
You should see `qwen3.5` in the list.

## 🚀 Starting the Bot

### Discord Bot
```bash
python bot.py
```

You should see:
```
Logged in as Lavender (ID: xxxxx)
------
```

### Textual TUI (Terminal Interface)
For a local terminal-based chat interface:
```bash
python lavender_tui.py
```
Or use the batch file:
```bash
run_tui.bat
```

The TUI provides a clean interface with:
- Header and footer
- Chat log with syntax highlighting
- Input field for messages
- Direct integration with Lavender's personality and memory

### Configuring users & tokens via the TUI
The TUI uses a `user.db` file to store:
- Discord token (DiscordToken)
- AI model settings (CHAT_MODEL, VISION_MODEL)
- Allowed user IDs + personas (ally/muggy)

**Core TUI Commands:**
- `/help` — show all available commands
- `/user add <id> <name> [persona]` — add or update a user
- `/user select <id>` — set the current user context
- `/user remove <id>` — remove a user
- `/token set <value>` — store your Discord bot token
- `/token show` — display current Discord token (masked)
- `/modals` — show current AI models
- `/modals set <type> <model>` — change AI model (chat/vision)
- `/versions` — show version history, credits, and risk warning
- `/discordhelp` — list all Discord bot commands
- `/bot start` — start the Discord bot
- `/bot stop` — stop the Discord bot
- `/bot status` — check if bot is running
- `/clear` — clear the chat log

The file `user.db` will be created automatically when you run the TUI.

## 👁️ Vision Features - Quick Demo

### Try These First

**1. Send an image**
   - Upload any image to Discord
   - Lavender responds with a poetic Qwen description

**2. Cluster your images**
   ```
   !vcluster
   ```
   Groups similar images by visual similarity

**3. See visual moments**
   ```
   !vmoments 5
   ```
   Shows 5 most recent images with full analysis

**4. Search images**
   ```
   !visearch sunset
   ```
   Find images matching a theme/description

**5. View emotional themes**
   ```
   !vemotions
   ```
   See emotional content across your images

**6. Get promotion ideas**
   ```
   !vsuggestions
   ```
   AI recommends what to save to long-term memory

## 🧠 What Qwen 3.5 Does Better Than Llama

| Task | Llama 3.1 | Qwen 3.5 |
|------|-----------|---------|
| Chat | Good | **Better** |
| Image description | Llava (vision model) | **Integrated multimodal** |
| Emotional analysis | Basic | **Deep emotional understanding** |
| Color/theme extraction | Not available | **Built-in** |
| Speed | Fast | **Similar/Faster** |
| Accuracy | Good | **Better on nuance** |

## 📊 Data Storage Locations

New files created by Qwen:
```
lavender_moments/
  visual_moments.json      (all image analysis)
  
lavender_memory/
  image_embeddings.json    (for clustering)
  image_clusters.json      (cluster definitions)
  
lavender_images/           (actual image files)
```

## 🆘 Common Issues & Fixes

### Issue: "Connection refused" when sending image
**Fix:** Make sure Ollama is running with `ollama run qwen3.5`

### Issue: !vcluster says "not enough pictures"
**Fix:** Send 3-4 images first, then try `!vcluster`

### Issue: Slow on first image
**Fix:** Qwen is processing - this is normal. Wait 5-10 seconds.

### Issue: Memory promotion fails
**Fix:** Check the image index with `!vmoments` first

### Issue: Visual moments file is empty
**Fix:** Check permissions on `lavender_moments/` directory

## 💡 Pro Tips

1. **Better Descriptions**: Qwen works better with varied images. Mix different subjects and styles.

2. **Clustering**: After 10+ images, `!vcluster` becomes more meaningful.

3. **Memory Promotion**: Use `!vpromote 0 "my_memory_name"` to save important visual trends.

4. **Searching**: Use `!visearch` with theme words like "cozy", "vibrant", "peaceful".

5. **Emotional Tracking**: `!vemotions` shows how image moods evolve over time.

## 🎯 Recommended Workflow

1. **Daily**: Send images → Lavender describes them
2. **Weekly**: Run `!vcluster` and `!vsuggestions`
3. **Monthly**: Use `!vpromote` to save important visual themes to memory
4. **Anytime**: Use `!visearch` to find past images

## 🔗 Key Commands Reference

```
# Visual Moments
!vmoments [limit]           - Show recent visual moments
!visearch <query>           - Search moments
!vemotions                  - Emotional timeline

# Clustering & Analysis
!vcluster                   - Cluster similar images
!vtheme [cluster_num]       - Theme summary of cluster
!vsuggestions               - Promotion suggestions

# Memory Integration
!vpromote <index> <key>     - Save to long-term memory

# Help
!guji                       - Full command list
!ver                        - Version & changes
```

## 📝 Expected Behavior

When you send an image:
1. Bot shows "typing..." indicator
2. Qwen analyzes: description, emotion, themes, colors, subject
3. Bot responds with poetic description
4. Analysis saved to `lavender_moments/visual_moments.json`

Example response:
> "baa… I see a serene garden with soft golden light filtering through leaves. 
> *I sense warmth and peaceful contemplation…* The colors are emerald and amber."

## 🛠️ If You Need to Reset

```bash
# Back up existing data
copy lavender_moments lavender_moments_backup
copy lavender_memory lavender_memory_backup

# Clear embeddings to force recalculate
del lavender_memory/image_embeddings.json
del lavender_memory/image_clusters.json

# Re-run clustering (will be slow first time)
# !vcluster
```

## 🎉 You're Ready!

Lavender now sees the world through Qwen's eyes. Enjoy enhanced vision and emotional understanding! 🌸

---

**Questions?** Check [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md) for detailed technical information.
