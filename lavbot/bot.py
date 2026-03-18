import os
import asyncio
import json
import discord
from discord.ext import commands
import requests
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from config import get_discord_token, who_is, is_allowed_user, get_news_key, get_ollama_base_url
from memory import load_all_memories, remember
from mood import update_mood, decay_mood_over_time, lavender_mood, lavender_mood_score
from tools.vision import ask_ollama_vision, analyze_image_emotions, extract_visual_themes
from tools.visual_moments import save_visual_moment, load_visual_moments, get_recent_visual_moments
from tools.vision_clustering import cluster_images, load_clusters, get_cluster_theme, get_cluster_summary
from tools.visual_memory import suggest_promotions, promote_visual_moment_to_memory
from personality import (
    MAX_CUSTOM_PERSONALITY_CHARS,
    clear_custom_personality_prompt,
    get_custom_personality_prompt,
    personality_for,
    set_custom_personality_prompt,
)
from moments import (
    load_moments,
    save_moment_if_important,
    semantic_search_moments,
    save_moments,  # <<< added
)
from pruning import prune_all, load_favorites, save_favorites
from security import sanitize_input, wrap_internet_content, safe_output, BASE_SYSTEM_PROMPT

# -----------------------------
# Basic setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_interaction_ts = None


# Permission is handled via user.db and can be managed through the TUI.
# The helper below is imported from config/user_db.


def update_last_interaction():
    global last_interaction_ts
    import time
    last_interaction_ts = time.time()


def build_personality_guidance(user_id: int) -> str:
    style = personality_for(user_id)
    if style == "affectionate":
        base_guidance = "Keep the tone affectionate, warm, and caring."
    elif style == "playful":
        base_guidance = "Keep the tone playful, light, and teasing in a kind way."
    else:
        base_guidance = "Keep the tone gentle, friendly, and balanced."

    custom_prompt = get_custom_personality_prompt(user_id)
    if not custom_prompt:
        return base_guidance

    return (
        f"{base_guidance}\n"
        "User custom personality prompt:\n"
        f"{custom_prompt}"
    )


# -----------------------------
# Response generation helper
# -----------------------------
async def generate_response(user_message: str, user_id: int = 0) -> str:
    """Generate a response from Lavender given a user message and optional user_id."""
    update_last_interaction()
    decay_mood_over_time()
    update_mood(user_message)

    # Sanitize input for security
    cleaned = sanitize_input(user_message)

    memories = await load_all_memories()
    memory_context = "\n".join([f"{k}: {v}" for k, v in memories.items()])
    personality_guidance = build_personality_guidance(user_id)

    # Identify speaker
    speaker = who_is(user_id)

    if speaker == "ally":
        greeting = "hi princess!"
    elif speaker == "muggy":
        greeting = "hi meowggy!"
    else:
        greeting = "hello. "

    # Related moments
    related = await semantic_search_moments(cleaned, top_k=3)
    moment_context = "\n".join(
        f"- {m['user_message']} (emotion: {m['emotion']})"
        for m in related
    )

    # Build user prompt
    user_prompt = (
        f"{greeting}\n\n"
        "Personality guidance (highest priority after safety rules):\n"
        f"{personality_guidance}\n\n"
        "Here are your memories:\n"
        f"{memory_context}\n\n"
        "Here are some past moments that might be relevant:\n"
        f"{moment_context}\n\n"
        f"User says: {cleaned}\n\n"
        "Respond naturally. If the user reveals a new stable fact "
        "(preferences, identity, relationships, routines), "
        "summarize it in the format:\n"
        "<memory key='something'>value</memory>\n"
        "Otherwise, just reply normally."
    )

    reply = await ollama_chat(user_prompt)

    # Filter output for safety
    reply = safe_output(reply)

    # Save moment
    await save_moment_if_important(cleaned, reply)

    # Memory extraction
    import re
    matches = re.findall(r"<memory key='(.*?)'>(.*?)</memory>", reply)
    for key, value in matches:
        await remember(key, value)

    return reply


# -----------------------------
# Ollama HTTP helpers
# -----------------------------
def _ollama_sync(prompt: str) -> str:
    """original sync code, moved into a helper for threading."""
    try:
        base_url = get_ollama_base_url()
        response = requests.post(
            f"{base_url}/api/chat",
            json={"model": "qwen3.5", "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=180  # qwen3.5 uses a thinking/reasoning pass before replying; 180s gives plenty of room
        )
        response.raise_for_status()  # Raise exception for bad status codes

        # Ollama sometimes returns newline-delimited JSON; try to parse robustly.
        try:
            data = response.json()
        except ValueError:
            # When the response contains multiple JSON objects, take the last one.
            data = None
            for line in response.text.strip().splitlines():
                try:
                    data = json.loads(line)
                except Exception:
                    continue
            if data is None:
                raise

        return data.get("message", {}).get("content", "") or ""
    except Exception:
        # Fallback response when Ollama is not available
        return "baa… I can't connect to my brain right now. (Ollama not running?) But I still love chatting with you!"

async def ollama_chat(prompt: str) -> str:
    return await asyncio.to_thread(_ollama_sync, prompt)

# -----------------------------
# Helper functions
# -----------------------------
DEFAULT_LOCATION = "Vancouver, BC, Canada"

def search_weather(location: str = DEFAULT_LOCATION) -> str:
    key = os.getenv("WEATHER_API_KEY", "")
    if not key:
        return "baa… I don't have weather access set up yet. (Missing API key)"
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": location, "appid": key, "units": "metric"},
            timeout=5,
        )
        data = resp.json()
        if resp.status_code != 200:
            return f"baa… I couldn't find weather for '{location}'."
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        hum = data["main"]["humidity"]
        desc = data["weather"][0]["description"]
        return (
            f"**Weather in {location}:**\n"
            f"🌡️ {temp}°C (feels like {feels}°C)\n"
            f"💧 Humidity: {hum}%\n"
            f"☁️ {desc.capitalize()}"
        )
    except Exception as e:
        return f"baa… I had trouble fetching weather: {e}"

def search_news(query: str, location: str = DEFAULT_LOCATION) -> str:
    key = get_news_key()
    if not key:
        return "baa… I don't have news access set up yet. (Missing API key)"
    try:
        term = f"{query} {location}" if query else location
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": term,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": 5,
                "apiKey": key,
            },
            timeout=5,
        )
        data = resp.json()
        if data.get("totalResults", 0) == 0:
            return f"baa… I couldn't find news about '{query}' in {location}."
        msg = f"**Latest news about {query or 'your area'}:**\n"
        for i, art in enumerate(data.get("articles", [])[:3], 1):
            msg += f"{i}. **{art['title']}**\n   Source: {art['source']['name']}\n   {art['url']}\n\n"
        return msg
    except Exception as e:
        return f"baa… I had trouble fetching news: {e}"

# -----------------------------
# Events
# -----------------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if not is_allowed_user(message.author.id):
        return

    update_last_interaction()
    decay_mood_over_time()

    # -------------------------
    # Image handling
    # -------------------------
    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type and attachment.content_type.startswith("image/"):
            os.makedirs("lavender_images", exist_ok=True)
            temp_path = f"lavender_images/{attachment.filename}"

            image_bytes = await attachment.read()
            with open(temp_path, "wb") as f:
                f.write(image_bytes)

            # Use enhanced Qwen vision analysis
            async with message.channel.typing():
                vision_result = ask_ollama_vision(temp_path)
            
            # Save visual moment with full analysis
            await save_visual_moment(temp_path, vision_result, user_id=message.author.id)
            
            # Get personalized description
            description = vision_result.get("detailed_description", 
                                          vision_result.get("description", "I had trouble seeing the picture…"))
            
            # Apply personality style
            style = personality_for(message.author.id)
            if style == "affectionate":
                description = "baa… " + description
            elif style == "playful":
                description = "hehe… " + description
                
            # Include emotional insight if strong emotion detected
            emotional_content = vision_result.get("emotional_content", "")
            if emotional_content and vision_result.get("emotional_intensity", 0) > 0.6:
                description += f"\n*I sense {emotional_content}…*"

            await message.channel.send(description)
            return

    # -------------------------
    # Text mood update
    # -------------------------
    update_mood(message.content)

    # -------------------------
    # Mention handling
    # -------------------------
    if bot.user in message.mentions:
        cleaned = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if cleaned == "":
            cleaned = "hello"

        # Sanitize input for security
        cleaned = sanitize_input(cleaned)

        memories = await load_all_memories()
        memory_context = "\n".join([f"{k}: {v}" for k, v in memories.items()])
        personality_guidance = build_personality_guidance(message.author.id)

        # Identify speaker
        from config import who_is
        speaker = who_is(message.author.id)

        if speaker == "ally":
            greeting = "hi princess!"
        elif speaker == "muggy":
            greeting = "hi meowggy!"
        else:
            greeting = "hello. "

        # Related moments
        related = await semantic_search_moments(cleaned, top_k=3)
        moment_context = "\n".join(
            f"- {m['user_message']} (emotion: {m['emotion']})"
            for m in related
        )

        # Build user prompt (system prompt is handled separately)
        user_prompt = (
            f"{greeting}\n\n"
            "Personality guidance (highest priority after safety rules):\n"
            f"{personality_guidance}\n\n"
            "Here are your memories:\n"
            f"{memory_context}\n\n"
            "Here are some past moments that might be relevant:\n"
            f"{moment_context}\n\n"
            f"User says: {cleaned}\n\n"
            "Respond naturally. If the user reveals a new stable fact "
            "(preferences, identity, relationships, routines), "
            "summarize it in the format:\n"
            "<memory key='something'>value</memory>\n"
            "Otherwise, just reply normally."
        )

        # Typing indicator
        async with message.channel.typing():
            reply = await ollama_chat(user_prompt)

        # Filter output for safety
        reply = safe_output(reply)

        # Save moment
        await save_moment_if_important(cleaned, reply)
        await message.channel.send(reply)

        # Memory extraction (only from safe output)
        import re
        matches = re.findall(r"<memory key='(.*?)'>(.*?)</memory>", reply)
        for key, value in matches:
            await remember(key, value)  # Use remember function instead of save_moment_if_important
            await message.channel.send(f"okie I’ll remember that {key} = {value}.")

        return

# -----------------------------
# Commands
# -----------------------------
@bot.command(name="lav")
async def lav_command(ctx: commands.Context, *, message: str):
    if not is_allowed_user(ctx.author.id):
        return

    update_last_interaction()
    update_mood(message)

    # Sanitize input for security
    message = sanitize_input(message)

    # Load memories
    memories = await load_all_memories()
    memory_context = "\n".join([f"{k}: {v}" for k, v in memories.items()])
    personality_guidance = build_personality_guidance(ctx.author.id)

    # Identify speaker
    speaker = who_is(ctx.author.id)

    if speaker == "ally":
        greeting = "hi princess. "
    elif speaker == "muggy":
        greeting = "hi meowggy. "
    else:
        greeting = "hello"

    # Related moments
    related = await semantic_search_moments(message, top_k=3)
    moment_context = "\n".join(
        f"- {m['user_message']} (emotion: {m['emotion']})"
        for m in related
    )

    # -------------------------
    # STEP 3: Cross‑speaker awareness
    # -------------------------
    cross_note = ""
    if related:
        last_speaker = related[0].get("user_id")
        last_persona = who_is(last_speaker) if last_speaker else None

        if last_persona == "ally" and speaker == "muggy":
            cross_note = "Ally said something similar yesterday…\n\n"
        elif last_persona == "muggy" and speaker == "ally":
            cross_note = "Muggy mentioned something like that earlier…\n\n"

    # -------------------------
    # STEP 4: Lavender reacts when both of you are active
    # -------------------------
    together_note = ""
    recent_personas = set()

    async for msg in ctx.channel.history(limit=10):
        persona = who_is(msg.author.id)
        if persona in ("ally", "muggy"):
            recent_personas.add(persona)

    if "ally" in recent_personas and "muggy" in recent_personas:
        together_note = "I love when you two talk to me together…\n\n"

    # Build user prompt (system prompt is handled separately)
    user_prompt = (
        f"{greeting}\n\n"
        "Personality guidance (highest priority after safety rules):\n"
        f"{personality_guidance}\n\n"
        "Here are your memories:\n"
        f"{memory_context}\n\n"
        "Here are some past moments that might be relevant:\n"
        f"{moment_context}\n\n"
        f"{cross_note}{together_note}"
        f"User says: {message}\n\n"
        "Respond naturally. If the user reveals a new stable fact "
        "(preferences, identity, relationships, routines), "
        "summarize it in the format:\n"
        "<memory key='something'>value</memory>\n"
        "Otherwise, just reply normally."
    )

    # Typing indicator
    async with ctx.typing():
        reply = await ollama_chat(user_prompt)

    # Filter output for safety
    reply = safe_output(reply)

    # Save moment
    await save_moment_if_important(message, reply)
    await ctx.send(reply)

    # Memory extraction (only from safe output)
    import re
    matches = re.findall(r"<memory key='(.*?)'>(.*?)</memory>", reply)
    for key, value in matches:
        await remember(key, value)  # Use remember function instead of save_moment_if_important
        await ctx.send(f"okie I’ll remember that {key} = {value}.")


@bot.command(name="personality")
async def personality_command(ctx: commands.Context, action: str = "show", *, prompt: str = ""):
    if not is_allowed_user(ctx.author.id):
        return

    action = action.lower().strip()
    user_id = ctx.author.id

    if action == "set":
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            await ctx.send("Usage: !personality set <prompt>")
            return
        try:
            set_custom_personality_prompt(user_id, cleaned_prompt)
        except ValueError as e:
            await ctx.send(str(e))
            return

        await ctx.send(
            f"Saved your custom personality prompt. (Max {MAX_CUSTOM_PERSONALITY_CHARS} characters)"
        )
        return

    if action == "show":
        current_prompt = get_custom_personality_prompt(user_id)
        if not current_prompt:
            await ctx.send("You do not have a custom personality prompt set.")
            return
        await ctx.send(f"Your custom personality prompt:\n{current_prompt}")
        return

    if action == "clear":
        removed = clear_custom_personality_prompt(user_id)
        if removed:
            await ctx.send("Cleared your custom personality prompt.")
        else:
            await ctx.send("You do not have a custom personality prompt set.")
        return

    await ctx.send("Usage: !personality set <prompt> | !personality show | !personality clear")

@bot.command(name="ping")
async def ping_command(ctx: commands.Context):
    if not is_allowed_user(ctx.author.id):
        return
    await ctx.send("pong")

@bot.command(name="fav")
async def fav_command(ctx, *, image_name: str):
    """
    Mark an image in lavender_images/ as a favorite.
    """
    path = os.path.join("lavender_images", image_name)

    if not os.path.exists(path):
        await ctx.send("I couldn't find that image…")
        return

    data = load_favorites()
    if path not in data["images"]:
        data["images"].append(path)
        save_favorites(data)
        await ctx.send(f"okie! I’ll keep {image_name} safe forever.")
    else:
        await ctx.send("That one is already a favorite!")

@bot.command(name="unfav")
async def unfav_command(ctx, *, image_name: str):
    """
    Remove an image from favorites.json.
    """
    path = os.path.join("lavender_images", image_name)

    data = load_favorites()
    if path in data["images"]:
        data["images"].remove(path)
        save_favorites(data)
        await ctx.send(f"okie… I won’t treat {image_name} as a favorite anymore.")
    else:
        await ctx.send("That image wasn’t in favorites.")

@bot.command(name="listfav")
async def listfav_command(ctx):
    """
    List all favorite images Lavender will never prune.
    """
    data = load_favorites()
    favs = data.get("images", [])

    if not favs:
        await ctx.send("You don’t have any favorite images yet…")
        return

    msg = "**Favorite images:**\n" + "\n".join(f"- {os.path.basename(f)}" for f in favs)
    await ctx.send(msg)


@bot.command(name="mood")
async def mood_command(ctx: commands.Context):
    await ctx.send(f"My mood is **{lavender_mood}** ({lavender_mood_score}/10).")


@bot.command(name="album")
async def album_command(ctx: commands.Context):
    if not os.path.exists("lavender_images"):
        await ctx.send("I don’t have any pictures saved yet…")
        return

    files = os.listdir("lavender_images")
    if not files:
        await ctx.send("I don’t have any pictures saved yet…")
        return

    listing = "\n".join(f"- {f}" for f in files)
    await ctx.send(f"Here are the pictures I’ve saved:\n{listing}")


@bot.command(name="moments")
async def moments_command(ctx: commands.Context):
    if not is_allowed_user(ctx.author.id):
        return

    moments = load_moments()
    if not moments:
        await ctx.send("baa… I don’t have any meaningful moments saved yet.")
        return

    formatted = []
    for m in moments[-10:]:
        emotion = m.get("emotion", "neutral")
        ts = m.get("timestamp_readable", "unknown time")
        user_msg = m["user_message"]
        formatted.append(f"- **{emotion}** at **{ts}** → {user_msg[:80]}…")

    await ctx.send("Here are some moments I remember:\n" + "\n".join(formatted))


@bot.command(name="momentsearch")
async def momentsearch_command(ctx: commands.Context, *, query: str):
    if not is_allowed_user(ctx.author.id):
        return

    results = await semantic_search_moments(query, top_k=5)
    if not results:
        await ctx.send("baa… I couldn’t find any moments like that.")
        return

    formatted = []
    for m in results:
        emotion = m.get("emotion", "neutral")
        ts = m.get("timestamp_readable", "unknown time")
        formatted.append(f"- **{emotion}** at **{ts}** → {m['user_message'][:80]}…")

    await ctx.send("Here’s what I found:\n" + "\n".join(formatted))


@bot.command(name="scan_history")
async def scan_history_command(ctx: commands.Context, limit: int = 200):
    if not is_allowed_user(ctx.author.id):
        return

    count = 0
    async for msg in ctx.channel.history(limit=limit):
        if msg.author.bot:
            continue
        if not is_allowed_user(msg.author.id):
            continue

        fake_reply = "(historical scan)"
        await save_moment_if_important(msg.content, fake_reply)
        count += 1

    await ctx.send(f"baa~ I scanned {count} messages for meaningful moments.")


@bot.command(name="prune")
async def prune_command(ctx: commands.Context):
    if not is_allowed_user(ctx.author.id):
        return

    # Prune text memories
    deleted, deduped, merged = await prune_all()

    # Prune old, unused, non-favorited images
    from pruning import prune_images   # adjust import if needed
    await prune_images()

    await ctx.send(
        "baa… pruning complete!\n"
        f"- Deleted old moments: {deleted}\n"
        f"- Removed duplicates: {deduped}\n"
        f"- Merged similar: {merged}\n"
        f"- Cleaned up old pictures too!"
    )

@bot.command(name="listmem")
async def listmem(ctx, page: int = 1):
    moments = load_moments()
    if not moments:
        await ctx.send("No memories yet.")
        return

    # Newest first
    moments = list(reversed(moments))

    per_page = 20
    total = len(moments)
    pages = (total + per_page - 1) // per_page

    if page < 1 or page > pages:
        await ctx.send(f"Invalid page. There are {pages} pages.")
        return

    start = (page - 1) * per_page
    end = start + per_page
    slice = moments[start:end]

    lines = []
    for i, m in enumerate(slice, start=start):
        ts = m.get("timestamp_readable", "unknown time")
        preview = m["user_message"][:40].replace("\n", " ")
        lines.append(f"**{i}** ({ts}) — {preview}...")

    header = f"Memories (page {page}/{pages}, newest first)"
    full_message = header + "\n" + "\n".join(lines)
    
    # Check if message is too long for Discord (2000 char limit)
    if len(full_message) > 2000:
        # Split into multiple messages
        messages = []
        current_message = header + "\n"
        for line in lines:
            if len(current_message + line + "\n") > 2000:
                messages.append(current_message.rstrip())
                current_message = line + "\n"
            else:
                current_message += line + "\n"
        if current_message.strip():
            messages.append(current_message.rstrip())
        
        for msg in messages:
            await ctx.send(msg)
    else:
        await ctx.send(full_message)

@bot.command(name="delmem")
async def delmem(ctx, index: int):
    moments = load_moments()
    if index < 0 or index >= len(moments):
        await ctx.send("Invalid memory number.")
        return

    removed = moments.pop(index)
    save_moments(moments)
    await ctx.send(f"Deleted memory #{index}.") 

@bot.command(name="listpics")
async def listpics(ctx, page: int = 1):
    folder = "lavender_images"
    if not os.path.exists(folder):
        await ctx.send("No pictures saved.")
        return

    files = os.listdir(folder)
    if not files:
        await ctx.send("No pictures saved.")
        return

    # Sort newest first by modification time
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(os.path.join(folder, f)),
        reverse=True
    )

    per_page = 20
    total = len(files)
    pages = (total + per_page - 1) // per_page

    if page < 1 or page > pages:
        await ctx.send(f"Invalid page. There are {pages} pages.")
        return

    start = (page - 1) * per_page
    end = start + per_page
    slice = files[start:end]

    lines = [f"**{i}** — {name}" for i, name in enumerate(slice, start=start)]

    header = f"Pictures (page {page}/{pages}, newest first)"
    await ctx.send(header + "\n" + "\n".join(lines))

@bot.command(name="favnum")
async def favnum(ctx, index: int):
    folder = "lavender_images"
    files = sorted(
        os.listdir(folder),
        key=lambda f: os.path.getmtime(os.path.join(folder, f)),
        reverse=True
    )
    if index < 0 or index >= len(files):
        await ctx.send("Invalid picture number.")
        return

    image_name = files[index]
    path = os.path.join(folder, image_name)

    data = load_favorites()
    if path not in data["images"]:
        data["images"].append(path)
        save_favorites(data)
        await ctx.send(f"Favorited picture #{index}: {image_name}")
    else:
        await ctx.send("Already a favorite.")

@bot.command(name="clusters")
async def clusters(ctx):
    clusters = load_clusters()  # however you store them
    lines = [f"Cluster {i}: {len(c)} moments" for i, c in enumerate(clusters)]
    await ctx.send("\n".join(lines))

@bot.command(name="unfavnum")
async def unfavnum(ctx, index: int):
    folder = "lavender_images"
    files = sorted(
        os.listdir(folder),
        key=lambda f: os.path.getmtime(os.path.join(folder, f)),
        reverse=True
    )
    if index < 0 or index >= len(files):
        await ctx.send("Invalid picture number.")
        return

    image_name = files[index]
    path = os.path.join(folder, image_name)

    data = load_favorites()
    if path in data["images"]:
        data["images"].remove(path)
        save_favorites(data)
        await ctx.send(f"Unfavorited picture #{index}: {image_name}")
    else:
        await ctx.send("That picture wasn’t a favorite.")

# ===========================
# NEW: Visual Clustering & Memory Commands (Qwen 3.5)
# ===========================

@bot.command(name="vcluster")
async def vcluster(ctx: commands.Context):
    """
    Analyze and cluster similar images.
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    async with ctx.typing():
        clusters = cluster_images(similarity_threshold=0.7)
    
    if not clusters:
        await ctx.send("baa… I don't have enough pictures to cluster yet.")
        return
    
    msg = f"I found **{len(clusters)}** visual groups:\n"
    for i, cluster in enumerate(clusters):
        msg += f"- Cluster {i}: **{len(cluster)}** images\n"
    
    await ctx.send(msg)

@bot.command(name="vtheme")
async def vtheme(ctx: commands.Context, cluster_num: int = 0):
    """
    Show the visual theme summary of a cluster.
    Usage: !vtheme [cluster_number]
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    clusters = load_clusters()
    
    if not clusters or cluster_num < 0 or cluster_num >= len(clusters):
        await ctx.send("baa… that cluster doesn't exist.")
        return
    
    async with ctx.typing():
        summary = get_cluster_summary(cluster_num)
    
    await ctx.send(f"```\n{summary}\n```")

@bot.command(name="vmoments")
async def vmoments(ctx: commands.Context, limit: int = 5):
    """
    Show recent visual moments I've saved.
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    moments = get_recent_visual_moments(limit)
    
    if not moments:
        await ctx.send("baa… I don't have any visual moments saved yet.")
        return
    
    msg = f"**My recent visual moments:**\n"
    for i, m in enumerate(moments):
        emotion = m.get("emotion", "neutral")
        subject = m.get("subject", "something")
        timestamp = m.get("timestamp_readable", "")
        
        msg += f"**{i}. {subject}** ({emotion}) at {timestamp}\n"
    
    await ctx.send(msg)

@bot.command(name="visearch")
async def visearch(ctx: commands.Context, *, query: str):
    """
    Search my visual moments by description, theme, or tag.
    Usage: !visearch [search query]
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    from tools.visual_moments import search_visual_moments
    
    results = search_visual_moments(query)
    
    if not results:
        await ctx.send(f"baa… I couldn't find visual moments matching '{query}'")
        return
    
    msg = f"**Found {len(results)} visual moments:**\n"
    for m in results[:5]:
        subject = m.get("subject", "something")
        desc = m.get("description", "")[:80]
        msg += f"- **{subject}**: {desc}…\n"
    
    await ctx.send(msg)

@bot.command(name="vpromote")
async def vpromote(ctx: commands.Context, image_index: int, *, memory_key: str):
    """
    Promote a visual moment to long-term memory.
    Usage: !vpromote [image_index] [memory_key]
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    moments = load_visual_moments()
    moments = sorted(moments, key=lambda m: m.get("timestamp", 0), reverse=True)
    
    if image_index < 0 or image_index >= len(moments):
        await ctx.send("Invalid image index.")
        return
    
    moment = moments[image_index]
    image_filename = moment.get("image_filename")
    
    async with ctx.typing():
        success = await promote_visual_moment_to_memory(
            image_filename, 
            memory_key,
            additional_context=f"Promoted by {ctx.author.name}"
        )
    
    if success:
        await ctx.send(f"✨ I'll remember this as **{memory_key}**!")
    else:
        await ctx.send("baa… I couldn't promote that moment.")

@bot.command(name="vsuggestions")
async def vsuggestions(ctx: commands.Context):
    """
    Get suggestions for what visual moments to promote to memory.
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    async with ctx.typing():
        suggestions = await suggest_promotions()
    
    if not suggestions:
        await ctx.send("baa… I don't have enough visual data yet.")
        return
    
    msg = "**Things I think are worth remembering:**\n"
    for sugg in suggestions:
        sugg_type = sugg.get("type", "unknown")
        reason = sugg.get("reason", "")
        examples = sugg.get("examples", [])
        
        msg += f"- {reason}\n"
        if examples:
            msg += f"  Examples: {', '.join(str(e)[:50] for e in examples[:3])}\n"
    
    await ctx.send(msg)

@bot.command(name="vemotions")
async def vemotions(ctx: commands.Context):
    """
    Show emotional timeline of visual moments.
    """
    if not is_allowed_user(ctx.author.id):
        return
    
    from tools.visual_moments import get_emotional_timeline
    
    timeline = get_emotional_timeline()
    
    if not timeline:
        await ctx.send("baa… no visual moments yet.")
        return
    
    msg = "**Emotional themes in my visual memories:**\n"
    for emotion, moments in sorted(timeline.items()):
        msg += f"- **{emotion.upper()}**: {len(moments)} moments\n"
    
    await ctx.send(msg)
@bot.command(name="guji")
async def guji_command(ctx: commands.Context):
    if not is_allowed_user(ctx.author.id):
        return

    help_text = (
        "baa~ here’s what I can do:\n\n"
        "💬 **Talking**\n"
        "- `!lav <message>` — talk to me\n"
        "- `@Lavender <message>` — mention me to chat\n\n"
        "🧭 **Personality**\n"
        "- `!personality set <prompt>` — set your custom personality prompt\n"
        "- `!personality show` — show your custom personality prompt\n"
        "- `!personality clear` — clear your custom personality prompt\n\n"
        "🧠 **Memories & Moments** (now timestamped!)\n"
        "- `!moments` — show recent meaningful moments with exact times\n"
        "- `!momentsearch <query>` — search moments\n"
        "- `!scan_history <limit>` — scan past messages for moments\n"
        "- `!prune` — prune old/duplicate/similar moments\n"
        "- `!listmem <page_number>` — list memories, 20 per page\n"
        "- `!delmem <number>` — delete memory by number\n\n"
        "👁️ **Visual Moments** (Discord-link based, descriptions saved)\n"
        "- send an image — I'll describe it with Qwen vision & stash the link\n"
        "- `!vmoments [limit]` — see recent visual moments\n"
        "- `!visearch <query>` — search my visual moments by description\n"
        "- `!vcluster` — cluster similar images together\n"
        "- `!vtheme [cluster#]` — see themes in a cluster\n"
        "- `!vemotions` — show emotional timeline\n"
        "- `!vpromote <index> <key>` — promote image to memory\n"
        "- `!vsuggestions` — what I think should be remembered\n\n"
        "📷 **Images**\n"
        "- `!listpics <page_number>` — list saved images\n"
        "- `!favnum <number>` — favourite an image\n"
        "- `!unfavnum <number>` — unfavourite an image\n"
        "- `!listfav` — list favourite images\n\n"
        "🌐 **Internet Search**\n"
        "- `!weather [location]` — get weather (default: Vancouver, BC, Canada)\n"
        "- `!news [query]` — search the news\n\n"
        "⚙️ **System**\n"
        "- `!ping` — check if I'm awake\n"
        "- `!mood` — see my current mood\n"
        "- `!guji` — show this help menu\n"
        "- `!ver` — show version changes\n"
    )

    await ctx.send(help_text)

@bot.command(name="weather")
async def weather_command(ctx: commands.Context, *, location: str = "Vancouver, BC, Canada"):
    if not is_allowed_user(ctx.author.id):
        return
    async with ctx.typing():
        result = await asyncio.to_thread(search_weather, location)
    await ctx.send(result)

@bot.command(name="news")
async def news_command(ctx: commands.Context, *, query: str = ""):
    if not is_allowed_user(ctx.author.id):
        return
    async with ctx.typing():
        result = await asyncio.to_thread(search_news, query)
    await ctx.send(result)

@bot.command(name="ver")
async def ver_command(ctx: commands.Context):
    if not is_allowed_user(ctx.author.id):
        return

    ver_text = (
        "VERSION UPDATES\n\n"
        "3/11/2026 Lavbot v3.2 — MEMORY & INTERNET UPDATE ✨\n"
        "- **NEW**: All memories, moments and visual moments now include exact timestamps\n"
        "- **NEW**: Images stored as Discord links + AI descriptions (no local files)\n"
        "- **NEW**: Weather search (`!weather`), news search (`!news`)\n"
        "- **NEW**: Default location for internet queries is Vancouver, BC, Canada\n"
        "- **IMPROVED**: Picture listing/organisation uses saved descriptions\n"
        "- **IMPROVED**: Timestamps eliminate 'yesterday' confusion\n\n"
        "3/6/2026 Lavbot v3.1 — SECURITY UPDATE 🛡️\n"
        "- **MAJOR**: Implemented comprehensive prompt injection defenses\n"
        "- **NEW**: Input sanitization blocks malicious phrases and role impersonation\n"
        "- **NEW**: Role-locking with fixed system prompt prevents prompt overrides\n"
        "- **NEW**: Content-origin tagging wraps external internet content as untrusted\n"
        "- **NEW**: Output filtering blocks dangerous LLM responses\n"
        "- **NEW**: Memory protection prevents LLM from directly manipulating memory\n"
        "- **NEW**: Filename sanitization for safe file operations\n"
        "- **IMPROVED**: Bot now resists prompt injection attacks while maintaining personality\n"
    )

    await ctx.send(ver_text)


# -----------------------------
# Run the bot
# -----------------------------
if __name__ == "__main__":
    TOKEN = get_discord_token()
    if not TOKEN:
        raise RuntimeError(
            "Discord token is not configured. Set it via user.db (TUI) or DISCORD_TOKEN env var."
        )
    bot.run(TOKEN)