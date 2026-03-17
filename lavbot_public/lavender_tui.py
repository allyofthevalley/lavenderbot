from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, RichLog, Input
import asyncio
import subprocess
import os

from bot import generate_response
from user_db import (
    add_user,
    get_user,
    list_settings,
    list_users,
    remove_user,
    set_setting,
    get_setting,
)


class LavenderTUI(App):
    CSS_PATH = "lavender.css"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_id: int | None = None
        self.bot_process = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="chat", highlight=True)
        yield Input(placeholder="Talk to Lavender...", id="input")
        yield Footer()

    async def on_mount(self):
        chat = self.query_one("#chat", RichLog)
        chat.write("Welcome to Lavender TUI!")
        chat.write("Type /lav for commands.")
        chat.write("You can set up users, tokens, and models via the TUI.")

    async def on_input_submitted(self, message: Input.Submitted):
        chat = self.query_one("#chat", RichLog)
        user_text = message.value.strip()
        message.input.value = ""

        if not user_text:
            return

        if user_text.startswith("/"):
            await self.handle_command(chat, user_text)
            return

        chat.write(f"You: {user_text}")

        lavender_reply = await generate_response(user_text, user_id=self.current_user_id or 0)
        chat.write(f"Lavender: {lavender_reply}")

    async def handle_command(self, chat: RichLog, command: str):
        parts = command.strip().split(maxsplit=3)  # Allow spaces in values
        cmd = parts[0].lower()

        if cmd == "/lav":
            chat.write("Commands:")
            chat.write("Chat & Config:")
            chat.write("/lav — show this message")
            chat.write("/users — list authorized users")
            chat.write("/user select <id> — select a user for chat context")
            chat.write("/user add <id> <name> [persona] — add or update a user")
            chat.write("/user remove <id> — remove a user")
            chat.write("")
            chat.write("Tokens & Security:")
            chat.write("/token set <value> — set Discord token")
            chat.write("/token show — display current Discord token")
            chat.write("/weather set <key> — set OpenWeather API key")
            chat.write("/weather show — display current OpenWeather key")
            chat.write("/news set <key> — set News API key")
            chat.write("/news show — display current News API key")
            chat.write("")
            chat.write("System:")
            chat.write("/models — show current AI models")
            chat.write("/models set <type> <model> — change AI model")
            chat.write("/versions — show version history & credits")
            chat.write("/discordhelp — list Discord bot commands")
            chat.write("/bot start — start the Discord bot")
            chat.write("/bot stop — stop the Discord bot")
            chat.write("/bot status — check bot status")
            chat.write("/clear — clear chat log")
            return

        if cmd == "/clear":
            chat.clear()
            return

        if cmd == "/versions":
            await self.show_versions(chat)
            return

        if cmd == "/discordhelp":
            await self.show_discord_help(chat)
            return

        if cmd == "/models":
            if len(parts) >= 2 and parts[1].lower() == "set" and len(parts) >= 4:
                model_type = parts[2].lower()
                model_name = parts[3]
                self.set_model(chat, model_type, model_name)
            else:
                self.show_models(chat)
            return

        if cmd == "/bot":
            if len(parts) >= 2:
                sub = parts[1].lower()
                if sub == "start":
                    await self.start_bot(chat)
                elif sub == "stop":
                    await self.stop_bot(chat)
                elif sub == "status":
                    self.check_bot_status(chat)
            return

        if cmd == "/users":
            users = list_users()
            if not users:
                chat.write("No users configured yet. Use /user add to create one.")
                return

            chat.write("[bold]Configured users:[/bold]")
            for u in users:
                selected = " (selected)" if u["id"] == self.current_user_id else ""
                chat.write(f"- {u['id']} — {u.get('name') or 'unnamed'} (persona: {u.get('persona') or 'none'}){selected}")
            return

        if cmd == "/user" and len(parts) >= 2:
            sub = parts[1].lower()
            if sub == "select" and len(parts) >= 3:
                try:
                    uid = int(parts[2])
                except ValueError:
                    chat.write("User ID must be an integer.")
                    return

                user = get_user(uid)
                if not user:
                    chat.write(f"No user found with ID {uid}.")
                    return

                self.current_user_id = uid
                chat.write(f"Selected user {uid} ({user.get('name') or 'unknown'}).")
                return

            if sub == "add" and len(parts) >= 4:
                try:
                    uid = int(parts[2])
                except ValueError:
                    chat.write("User ID must be an integer.")
                    return

                name = parts[3]
                persona = parts[4] if len(parts) >= 5 else None
                add_user(uid, name=name, persona=persona)
                chat.write(f"Added/updated user {uid} ({name}) persona={persona}.")
                return

            if sub == "remove" and len(parts) >= 3:
                try:
                    uid = int(parts[2])
                except ValueError:
                    chat.write("User ID must be an integer.")
                    return

                if remove_user(uid):
                    chat.write(f"Removed user {uid}.")
                    if self.current_user_id == uid:
                        self.current_user_id = None
                        chat.write("Current user selection cleared.")
                else:
                    chat.write(f"No user found with ID {uid}.")
                return

        if cmd == "/token":
            if len(parts) >= 2 and parts[1].lower() == "set" and len(parts) >= 3:
                value = parts[2]
                set_setting("DiscordToken", value)
                chat.write("Discord token saved.")
                return

            if len(parts) >= 2 and parts[1].lower() == "show":
                token = get_setting("DiscordToken")
                if token is None:
                    chat.write("No Discord token set.")
                else:
                    masked = token[:5] + "*" * (len(token) - 10) + token[-5:] if len(token) > 10 else "***"
                    chat.write(f"DiscordToken = {masked}")
                return

        if cmd == "/weather":
            if len(parts) >= 2 and parts[1].lower() == "set" and len(parts) >= 3:
                value = parts[2]
                set_setting("OPENWEATHER_KEY", value)
                chat.write("OpenWeather API key saved.")
                return

            if len(parts) >= 2 and parts[1].lower() == "show":
                key = get_setting("OPENWEATHER_KEY")
                if key is None:
                    chat.write("No OpenWeather API key set.")
                else:
                    masked = key[:5] + "*" * (len(key) - 10) + key[-5:] if len(key) > 10 else "***"
                    chat.write(f"OPENWEATHER_KEY = {masked}")
                return

        if cmd == "/news":
            if len(parts) >= 2 and parts[1].lower() == "set" and len(parts) >= 3:
                value = parts[2]
                set_setting("NEWS_API_KEY", value)
                chat.write("News API key saved.")
                return

            if len(parts) >= 2 and parts[1].lower() == "show":
                key = get_setting("NEWS_API_KEY")
                if key is None:
                    chat.write("No News API key set.")
                else:
                    masked = key[:5] + "*" * (len(key) - 10) + key[-5:] if len(key) > 10 else "***"
                    chat.write(f"NEWS_API_KEY = {masked}")
                return

        chat.write("Unknown command. Type /lav for available commands.")

    def show_models(self, chat: RichLog):
        """Display current AI model settings."""
        chat.write("Current AI Models:")
        
        chat_model = get_setting("CHAT_MODEL") or "qwen3.5"
        vision_model = get_setting("VISION_MODEL") or "qwen3.5"
        
        chat.write(f"- Chat Model: {chat_model}")
        chat.write(f"- Vision Model: {vision_model}")
        chat.write("")
        chat.write("Use: /models set <type> <model>")
        chat.write("Example: /models set chat llama3.1")

    def set_model(self, chat: RichLog, model_type: str, model_name: str):
        """Set an AI model."""
        if model_type == "chat":
            set_setting("CHAT_MODEL", model_name)
            chat.write(f"Chat model set to {model_name}.")
        elif model_type == "vision":
            set_setting("VISION_MODEL", model_name)
            chat.write(f"Vision model set to {model_name}.")
        else:
            chat.write("Unknown model type. Use 'chat' or 'vision'.")

    async def show_versions(self, chat: RichLog):
        """Show version history and credits."""
        chat.write("Lavbot Version History")
        chat.write("")
        chat.write("Credits:")
        chat.write("GitHub: https://github.com/allyofthevalley")
        chat.write("")
        chat.write("RISK WARNING:")
        chat.write("This is a personal AI companion project in development.")
        chat.write("Potential risks:")
        chat.write("- May generate inaccurate or harmful content if prompted")
        chat.write("- Stores personal data locally (memories, moments, images)")
        chat.write("- Requires Discord bot token and API keys")
        chat.write("- No guarantees on model behavior or responses")
        chat.write("Use at your own risk and review generated content.")
        chat.write("")
        chat.write("Version Timeline:")
        chat.write("")
        
        versions = [
            ("3/17/2026", "v3.3", "TEXTUAL TUI UPDATE 💻", [
                "Textual TUI interface for terminal-based chat",
                "Clean, modern interface with RichLog for chat display",
                "Direct integration with Lavender's personality and memory",
                "Fallback responses when Ollama is unavailable",
                "Custom CSS styling for lavender theme"
            ]),
            ("3/11/2026", "v3.2", "MEMORY & INTERNET UPDATE ✨", [
                "All memories, moments and visual moments now timestamped",
                "Images stored as Discord links + AI descriptions",
                "Weather search (!weather), news search (!news)",
                "Default location for internet: Vancouver, BC, Canada",
                "Picture listing uses saved descriptions"
            ]),
            ("3/6/2026", "v3.1", "SECURITY UPDATE 🛡️", [
                "Comprehensive prompt injection defenses",
                "Input sanitization blocks malicious phrases",
                "Role-locking with fixed system prompt",
                "Content-origin tagging for internet content",
                "Output filtering and memory protection"
            ]),
            ("3/4/2026", "v3.0", "QWEN 3.5 UPGRADE ✨", [
                "Switched from Llama 3.1 to Qwen 3.5",
                "Full visual moment system with image analysis",
                "Image clustering by visual similarity",
                "Emotional content analysis in images",
                "Visual memory promotion to long-term memory"
            ]),
            ("3/3/2026", "v2.3", "2.x Final Release", [
                "Added cluster functionality",
                "Optimized moment and memory integration"
            ]),
            ("3/3/2026", "v2.2", "Memory & Picture Commands", [
                "Added !listmem (20 per page), !delmem",
                "Added !listpics (20 per page), !favnum, !unfavnum",
                "Removed !album from help menu"
            ]),
            ("2/11/2026", "v2.1", "Image & Memory Release", [
                "Added image, memory and moment functions",
                "Added !prune command for cleanup",
                "Added mood system with time decay"
            ]),
            ("2/10/2026", "v1.0", "Lavbot Born! 🎉", [
                "Initial release"
            ]),
        ]
        
        for date, version, title, features in versions:
            chat.write(f"{date} — {version} — {title}")
            for feat in features:
                chat.write(f"  • {feat}")
            chat.write("")

    def show_discord_help(self, chat: RichLog):
        """Show Discord bot commands."""
        chat.write("Discord Bot Commands")
        chat.write("")
        chat.write("Chat:")
        chat.write("!lav <message> — Talk to Lavender")
        chat.write("@Lavender <message> — Mention to chat")
        chat.write("")
        chat.write("Memories & Moments:")
        chat.write("!moments — Show recent meaningful moments")
        chat.write("!momentsearch <query> — Search moments")
        chat.write("!scan_history [limit] — Scan messages for moments")
        chat.write("!prune — Cleanup old/duplicate moments")
        chat.write("!listmem [page] — List memories (20 per page)")
        chat.write("!delmem <number> — Delete memory")
        chat.write("")
        chat.write("Visual Moments:")
        chat.write("Send image — Lavender describes it")
        chat.write("!vmoments [limit] — Show recent visual moments")
        chat.write("!visearch <query> — Search images by description")
        chat.write("!vcluster — Cluster similar images")
        chat.write("!vtheme [cluster#] — Show cluster themes")
        chat.write("!vemotions — Show emotional timeline")
        chat.write("!vpromote <idx> <key> — Promote image to memory")
        chat.write("!vsuggestions — What to remember from images")
        chat.write("")
        chat.write("Pictures:")
        chat.write("!listpics [page] — List saved images")
        chat.write("!favnum <number> — Favorite an image")
        chat.write("!unfavnum <number> — Unfavorite an image")
        chat.write("!listfav — List favorite images")
        chat.write("")
        chat.write("Internet:")
        chat.write("!weather [location] — Get weather forecast")
        chat.write("!news [query] — Search the news")
        chat.write("")
        chat.write("System:")
        chat.write("!ping — Check if bot is awake")
        chat.write("!mood — See Lavender's mood")
        chat.write("!guji — Show full help menu")
        chat.write("!ver — Version changes")

    async def start_bot(self, chat: RichLog):
        """Start the Discord bot."""
        token = get_setting("DiscordToken")
        if not token:
            chat.write("Error: Discord token not configured.")
            chat.write("Use: /token set <your_token>")
            return

        if self.bot_process is not None:
            chat.write("Bot is already running.")
            return

        try:
            chat.write("Starting Discord bot...")
            self.bot_process = subprocess.Popen(
                [
                    "C:/Users/ilove/AppData/Local/Python/pythoncore-3.14-64/python.exe",
                    "bot.py",
                ],
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            chat.write("Bot started!")
        except Exception as e:
            chat.write(f"Error starting bot: {e}")

    async def stop_bot(self, chat: RichLog):
        """Stop the Discord bot."""
        if self.bot_process is None:
            chat.write("Bot is not running.")
            return

        try:
            self.bot_process.terminate()
            self.bot_process.wait(timeout=5)
            self.bot_process = None
            chat.write("Bot stopped!")
        except Exception as e:
            try:
                self.bot_process.kill()
                self.bot_process = None
                chat.write("Bot killed!")
            except Exception as e2:
                chat.write(f"Error stopping bot: {e2}")

    def check_bot_status(self, chat: RichLog):
        """Check if bot is running."""
        if self.bot_process is None:
            chat.write("Bot is not running")
        else:
            if self.bot_process.poll() is None:
                chat.write("Bot is running")
            else:
                self.bot_process = None
                chat.write("Bot has crashed or stopped")


if __name__ == "__main__":
    LavenderTUI().run()
