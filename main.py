# Combined Discord Bot (Trap Channel + Free Fire Ban Check)

## main.py

```python
import discord
import os
import json
import asyncio
import aiohttp
from flask import Flask
import threading
from dotenv import load_dotenv
from discord.ext import commands
from datetime import timedelta, datetime, timezone

# =========================
# LOAD ENV
# =========================

load_dotenv()
TOKEN = os.getenv("TOKEN")

# =========================
# FLASK KEEP ALIVE
# =========================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"


def run_flask():
    app.run(host='0.0.0.0', port=10000)


threading.Thread(target=run_flask).start()

# =========================
# DISCORD BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# CONFIG
# =========================

CONFIG_FILE = "trap_channels.json"

DEFAULT_LANG = "en"
user_languages = {}

# =========================
# LOAD / SAVE CONFIG
# =========================


def load_config():

    default_config = {
        "servers": {}
    }

    if os.path.exists(CONFIG_FILE):

        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)

        except json.JSONDecodeError:
            return default_config

    return default_config


config = load_config()



def save_config():

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

# =========================
# LANGUAGE COMMAND
# =========================

@bot.command(name="lang")
async def change_language(ctx, lang_code: str):

    lang_code = lang_code.lower()

    if lang_code not in ["en", "fr"]:

        await ctx.send(
            "❌ Invalid language. Available: `en`, `fr`"
        )

        return

    user_languages[ctx.author.id] = lang_code

    message = (
        "✅ Language set to English."
        if lang_code == 'en'
        else "✅ Langue définie sur le français."
    )

    await ctx.send(f"{ctx.author.mention} {message}")

# =========================
# BAN CHECK API FUNCTION
# =========================

async def check_ban(uid: str):

    api_url = (
        f"http://raw.thug4ff.xyz/check_ban/{uid}/great"
    )

    timeout = aiohttp.ClientTimeout(total=20)

    try:

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(api_url) as response:

                response.raise_for_status()

                response_data = await response.json()

                if response_data.get("status") == 200:

                    data = response_data.get("data")

                    if data:

                        return {
                            "is_banned": data.get("is_banned", 0),
                            "nickname": data.get("nickname", "N/A"),
                            "period": data.get("period", "N/A"),
                            "region": data.get("region", "N/A")
                        }

                return None

    except Exception as e:

        print(f"API Error: {e}")
        return None

# =========================
# CHECK COMMAND
# =========================

@bot.command(name="check")
async def check(ctx, uid: str):

    lang = user_languages.get(ctx.author.id, "en")

    if not uid.isdigit():

        await ctx.send(
            f"{ctx.author.mention} ❌ Invalid UID!\n"
            f"➡️ Use: `!check 123456789`"
        )

        return

    async with ctx.typing():

        ban_status = await check_ban(uid)

        if ban_status is None:

            await ctx.send(
                f"{ctx.author.mention} ❌ Could not get information."
            )

            return

        is_banned = int(ban_status.get("is_banned", 0))
        nickname = ban_status.get("nickname", "N/A")
        period = ban_status.get("period", "N/A")
        region = ban_status.get("region", "N/A")

        embed = discord.Embed(
            color=0xFF0000 if is_banned else 0x00FF00
        )

        if is_banned:

            embed.title = "🛑 Banned Account"

            embed.description = (
                f"**Nickname:** `{nickname}`\n"
                f"**UID:** `{uid}`\n"
                f"**Region:** `{region}`\n"
                f"**Ban Period:** `{period}`"
            )

        else:

            embed.title = "✅ Clean Account"

            embed.description = (
                f"**Nickname:** `{nickname}`\n"
                f"**UID:** `{uid}`\n"
                f"**Region:** `{region}`"
            )

        embed.set_footer(text="DEVELOPED BY YOU")

        await ctx.send(embed=embed)

# =========================
# TRAP CHANNEL FUNCTIONS
# =========================


def is_trap_channel(guild_id, channel_id):

    return str(channel_id) in config[
        "servers"
    ].get(str(guild_id), {}).get(
        "trap_channels", []
    )

# =========================
# SET TRAP CHANNEL
# =========================

@bot.command(name="settrap")
@commands.has_permissions(administrator=True)
async def set_trap(ctx, channel: discord.TextChannel):

    guild_id = str(ctx.guild.id)

    if guild_id not in config["servers"]:

        config["servers"][guild_id] = {
            "trap_channels": []
        }

    if str(channel.id) not in config[
        "servers"
    ][guild_id]["trap_channels"]:

        config[
            "servers"
        ][guild_id]["trap_channels"].append(
            str(channel.id)
        )

        save_config()

        await ctx.send(
            f"✅ {channel.mention} set as trap channel"
        )

    else:

        await ctx.send(
            "⚠️ Channel already configured"
        )

# =========================
# REMOVE TRAP CHANNEL
# =========================

@bot.command(name="removetrap")
@commands.has_permissions(administrator=True)
async def remove_trap(ctx, channel: discord.TextChannel):

    guild_id = str(ctx.guild.id)

    if guild_id in config["servers"]:

        if str(channel.id) in config[
            "servers"
        ][guild_id]["trap_channels"]:

            config[
                "servers"
            ][guild_id]["trap_channels"].remove(
                str(channel.id)
            )

            save_config()

            await ctx.send(
                f"❌ {channel.mention} removed"
            )

            return

    await ctx.send("⚠️ Trap channel not found")

# =========================
# DELETE USER MESSAGES
# =========================

async def purge_user_messages(guild, user):

    now = datetime.now(timezone.utc)
    limit_time = now - timedelta(minutes=10)

    for channel in guild.text_channels:

        try:

            def check(msg):
                return (
                    msg.author.id == user.id
                    and msg.created_at > limit_time
                )

            await channel.purge(
                limit=500,
                check=check
            )

        except discord.Forbidden:
            continue

        except Exception as e:
            print(f"Error in {channel.name}: {e}")

# =========================
# TRAP LISTENER
# =========================

@bot.event
async def on_message(message):

    await bot.process_commands(message)

    if message.author.bot:
        return

    if not message.guild:
        return

    if message.content.startswith(("!", "/")):
        return

    if not is_trap_channel(
        message.guild.id,
        message.channel.id
    ):
        return

    try:

        user = message.author

        if user.guild_permissions.administrator:
            return

        await message.delete()

        await purge_user_messages(
            message.guild,
            user
        )

        try:

            await user.timeout(
                timedelta(hours=48),
                reason="Trap channel triggered"
            )

        except Exception as e:

            print(f"Timeout Error: {e}")

        warn_msg = await message.channel.send(
            f"🚫 {user.mention} DO NOT SEND MESSAGES HERE!"
        )

        await asyncio.sleep(8)

        await warn_msg.delete()

    except Exception as e:

        print(f"Trap Error: {e}")

# =========================
# RUN BOT
# =========================

bot.run(TOKEN)
