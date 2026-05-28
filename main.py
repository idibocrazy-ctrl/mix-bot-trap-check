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

    try:

        synced = await bot.tree.sync()

        print(f"Synced {len(synced)} commands")

    except Exception as e:

        print(e)
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

    api_url = f"http://raw.thug4ff.xyz/check_ban/{uid}/great"

    timeout = aiohttp.ClientTimeout(total=20)

    try:

        connector = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        ) as session:

            async with session.get(api_url) as response:

                print("STATUS:", response.status)
                print("URL:", api_url)

                # Get raw text first
                raw_text = await response.text()

                print("RAW RESPONSE:", raw_text)

                # Check HTTP status
                if response.status != 200:
                    return {
                        "error": f"HTTP {response.status}"
                    }

                # Convert to JSON safely
                try:
                    response_data = await response.json()

                except Exception:
                    return {
                        "error": "Invalid JSON response"
                    }

                print("JSON:", response_data)

                # API success check
                if response_data.get("status") == 200:

                    data = response_data.get("data")

                    if not data:
                        return {
                            "error": "No data found"
                        }

                    from datetime import datetime

                    timestamp = data.get("last_login", 0)

                    if (
                        str(timestamp).isdigit()
                        and int(timestamp) > 0
                    ):

                        last_login = datetime.fromtimestamp(
                            int(timestamp)
                        ).strftime("%d %b %Y %I:%M %p")

                    else:

                        last_login = "Unknown"

                    return {
                        "is_banned": data.get("is_banned", 0),
                        "nickname": data.get("nickname", "N/A"),
                        "period": data.get("period", "N/A"),
                        "region": data.get("region", "N/A"),
                        "last_login": last_login
                    }

                return {
                    "error": response_data.get(
                        "message",
                        "Unknown API error"
                    )
                }

    except asyncio.TimeoutError:

        return {
            "error": "Request timeout"
        }

    except aiohttp.ClientError as e:

        return {
            "error": f"Client error: {str(e)}"
        }

    except Exception as e:

        return {
            "error": str(e)
        }
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

        if not ban_status:
            await ctx.send(
                f"{ctx.author.mention} ❌ Could not get information."
            )
            return

        is_banned = int(ban_status.get("is_banned", 0))
        nickname = ban_status.get("nickname", "N/A")
        period = ban_status.get("period", "Unknown")
        region = ban_status.get("region", "Unknown")
        last_login = ban_status.get("last_login", "Unknown")
        
        # Ban type converter
        ban_types = {
            "1": "1 Day",
            "3": "Permanent",
            "7": "7 Days",
            "30": "30 Days"
        }

        ban_type = ban_types.get(
            str(period),
            str(period)
         )
        embed = discord.Embed(
            color=0xFF0000 if is_banned else 0x00FF00
        )

        # Thumbnail top-right
        embed.set_thumbnail(
            url=ctx.author.display_avatar.url
        )

        # ===============================
        # BANNED ACCOUNT
        # ===============================

        if is_banned:

            embed.title = "🔴 Banned  !"

            embed.description = (
                f"┃ **Reason:** "
                f"This account was confirmed for using cheats.\n"

                f"┃ **Nickname:** `{nickname}`\n"

                f"┃ **Player UID:** `{uid}`\n"

                f"┃ **Ban Type:** {ban_type}\n"

                f"┃ **Region:** 🌐 {region}"
            )

            file = discord.File(
                "assets/banned.gif",
                filename="banned.gif"
            )

            embed.set_image(
                url="attachment://banned.gif"
            )

        # ===============================
        # CLEAN ACCOUNT
        # ===============================

        else:

            embed.title = "🟢 Clean Account"

            embed.description = (
                f"┃ **Status:** No cheat detected\n"

                f"┃ **Nickname:** `{nickname}`\n"

                f"┃ **Player UID:** `{uid}`\n"

                f"┃ **Last Login:** {last_login}\n"

                f"┃ **Region:** 🌐 {region}"
            )

            file = discord.File(
                "assets/notbanned.gif",
                filename="notbanned.gif"
            )

            embed.set_image(
                url="attachment://notbanned.gif"
            )

        embed.set_footer(
            text="DEVELOPED BY DIBOXE LEGIT"
        )

        await ctx.send(
            ctx.author.mention,
            embed=embed,
            file=file
        )
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

@bot.hybrid_command(name="settrap")
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

@bot.hybrid_command(name="removetrap")
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
