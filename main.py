import sys
import time
import random
import threading
import json
import re
import io
import os
import aiohttp
import base64
import asyncio
from bot import DiscordBot
from config import Config
from voice import SimpleVoice
from backup import BackupManager
from moderation import ModerationManager
from webpanel import WebPanel
from error_handler import error_guard
from data_engine import data_core
from notification import alert_system
from analytics import insight_tracker
from host import host_manager
from afk_system import afk_system
from anti_gc_trap import AntiGCTrap
from GitHub import GitHubUpdater
from superreact import SuperReact

if os.environ.get('HOSTED_TOKEN') == 'true':
    HOSTED_MODE = True
else:
    HOSTED_MODE = False

def protected_main():
    error_guard.safe_execute(main)

def delete_after_delay(api, channel_id, message_id, delay=20):
    def delete():
        time.sleep(delay)
        api.delete_message(channel_id, message_id)
    threading.Thread(target=delete, daemon=True).start()

def delete_command_message(api, channel_id, message_id):
    try:
        api.delete_message(channel_id, message_id)
    except:
        pass

def upload_image_to_discord(api, image_url):
    try:
        discord_cdn_pattern = r"https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)/attachments/(\d+)/(\d+)/(.+)"
        match = re.search(discord_cdn_pattern, image_url)
        if match:
            channel_id, attachment_id, filename = match.groups()
            return f"mp:attachments/{channel_id}/{attachment_id}/{filename}"
        
        dm = api.create_dm(api.user_id)
        if not dm or "id" not in dm:
            return None
        
        response = api.session.get(image_url, timeout=10)
        if response.status_code != 200:
            return None
        
        image_bytes = response.content
        filename = image_url.split('/')[-1].split('?')[0]
        if '.' not in filename or len(filename) > 50:
            filename = "asset.png"
        
        files = {"file": (filename, image_bytes)}
        headers = api.header_spoofer.get_headers()
        
        upload_response = api.session.post(
            f"https://discord.com/api/v9/channels/{dm['id']}/messages",
            headers=headers,
            files=files
        )
        
        if upload_response.status_code == 200:
            message_data = upload_response.json()
            if "attachments" in message_data and message_data["attachments"]:
                attachment_url = message_data["attachments"][0]["url"]
                match = re.search(discord_cdn_pattern, attachment_url)
                if match:
                    channel_id, attachment_id, filename = match.groups()
                    return f"mp:attachments/{channel_id}/{attachment_id}/{filename}"
        
        return None
    except Exception as e:
        print(f"Image upload error: {e}")
        return None

async def upload_n_get_asset_key(bot, image_url):
    discord_cdn_pattern = r"https?://(?:cdn\.discordapp\.com|media\.discordapp\.net)/attachments/(\d+)/(\d+)/(.+)"
    match = re.search(discord_cdn_pattern, image_url)
    if match:
        channel_id, attachment_id, filename = match.groups()
        return f"mp:attachments/{channel_id}/{attachment_id}/{filename}"
    return upload_image_to_discord(bot.api, image_url)

async def send_spotify_with_spoofing(bot, song_name, artist, album, duration_minutes=3.5, current_position_minutes=0, image_url=None):
    current_ms = int(current_position_minutes * 60 * 1000)
    total_ms = int(duration_minutes * 60 * 1000)
    start_time = int(time.time() * 1000) - current_ms
    end_time = start_time + (total_ms - current_ms)
    
    spotify_track_id = "0VjIjW4GlUZAMYd2vXMi3b"
    album_id = "4yP0hdKOZPNshxUOjY0cZj"
    artist_id = "1Xyo4u8uXC1ZmMpatF05PJ"
    
    activity = {
        "type": 2,
        "name": "Spotify",
        "details": song_name,
        "state": artist,
        "timestamps": {"start": start_time, "end": end_time},
        "application_id": "3201606009684",
        "sync_id": spotify_track_id,
        "session_id": f"spotify:{spotify_track_id}",
        "party": {
            "id": f"spotify:{spotify_track_id}",
            "size": [1, 1]
        },
        "secrets": {
            "join": f"spotify:{spotify_track_id}",
            "spectate": f"spotify:{spotify_track_id}",
            "match": f"spotify:{spotify_track_id}"
        },
        "instance": True,
        "flags": 48,
        "metadata": {
            "context_uri": f"spotify:album:{album_id}",
            "album_id": album_id,
            "artist_ids": [artist_id],
            "track_id": spotify_track_id,
        }
    }

    if image_url:
        asset_key = await upload_n_get_asset_key(bot, image_url)
        if asset_key:
            activity["assets"] = {
                "large_image": asset_key,
                "large_text": f"{album} on Spotify"
            }
        else:
            activity["assets"] = {
                "large_image": "spotify",
                "large_text": f"{album} on Spotify"
            }
    else:
        activity["assets"] = {
            "large_image": "spotify",
            "large_text": f"{album} on Spotify"
        }

    bot.set_activity(activity)

async def send_listening_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 2,
        "name": "Spotify",
        "application_id": "3201606009684",
        "flags": 0
    }
    
    if details:
        activity["details"] = details
    else:
        activity["details"] = name
    
    if state:
        activity["state"] = state

    if image_url:
        asset_key = await upload_n_get_asset_key(bot, image_url)
        if asset_key:
            activity["assets"] = {
                "large_image": asset_key,
                "large_text": name
            }
        else:
            activity["assets"] = {
                "large_image": "spotify",
                "large_text": name
            }
    else:
        activity["assets"] = {
            "large_image": "spotify",
            "large_text": name
        }

    if button_label and button_url:
        activity["buttons"] = [button_label]
        activity["metadata"] = {
            "button_urls": [button_url]
        }

    bot.set_activity(activity)

async def send_streaming_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 1,
        "name": "Streaming",
        "url": "https://twitch.tv/kaicenat",
        "application_id": "111299001912"
    }
    
    if details:
        activity["details"] = details
    else:
        activity["details"] = name
    
    if state:
        activity["state"] = state

    if image_url:
        asset_key = await upload_n_get_asset_key(bot, image_url)
        if asset_key:
            activity["assets"] = {
                "large_image": asset_key,
                "large_text": name
            }
        else:
            activity["assets"] = {
                "large_image": "youtube",
                "large_text": name
            }
    else:
        activity["assets"] = {
            "large_image": "youtube",
            "large_text": name
        }

    if button_label and button_url:
        activity["buttons"] = [button_label]
        activity["metadata"] = {
            "button_urls": [button_url]
        }

    bot.set_activity(activity)

async def send_playing_activity(bot, name, button_label=None, button_url=None, image_url=None, state=None, details=None):
    activity = {
        "type": 0,
        "name": name,
        "application_id": "367827983903490050"
    }
    
    if details:
        activity["details"] = details
    
    if state:
        activity["state"] = state

    if image_url:
        asset_key = await upload_n_get_asset_key(bot, image_url)
        if asset_key:
            activity["assets"] = {
                "large_image": asset_key,
                "large_text": name
            }
        else:
            activity["assets"] = {
                "large_image": "game",
                "large_text": name
            }
    else:
        activity["assets"] = {
            "large_image": "game",
            "large_text": name
        }

    if button_label and button_url:
        activity["buttons"] = [button_label]
        activity["metadata"] = {
            "button_urls": [button_url]
        }

    bot.set_activity(activity)

async def send_timer_activity(bot, name, start_time=None, end_time=None, details=None, state=None, image_url=None):
    activity = {
        "type": 0,
        "name": name,
        "application_id": "367827983903490050"
    }
    
    if start_time and end_time:
        activity["timestamps"] = {"start": int(start_time * 1000), "end": int(end_time * 1000)}
    
    if details:
        activity["details"] = details
    
    if state:
        activity["state"] = state

    if image_url:
        asset_key = await upload_n_get_asset_key(bot, image_url)
        if asset_key:
            activity["assets"] = {
                "large_image": asset_key,
                "large_text": name
            }
        else:
            activity["assets"] = {
                "large_image": "game",
                "large_text": name
            }
    else:
        activity["assets"] = {
            "large_image": "game",
            "large_text": name
        }

    bot.set_activity(activity)

LAST_SERVER_COPY = None

def main():
    config = Config()
    token = config.get("token")
    
    if not token or token == "token here":
        print("Error: No token found in config.json")
        print("Edit config.json and add your token")
        with open("config.json", 'w') as f:
            json.dump({"token": "token here", "prefix": "+"}, f, indent=4)
            print("Created config.json - edit it with your token")
        return
    
    bot = DiscordBot(token, config.get("prefix", "+"))
    voice_manager = SimpleVoice(bot.api, token)
    backup_manager = BackupManager(bot.api)
    mod_manager = ModerationManager(bot.api)
    web_panel = WebPanel(bot.api, bot, host='127.0.0.1', port=8080)
    web_panel.start()
    afk_system.load_state()
    anti_gc_trap = AntiGCTrap(bot.api)
    github_updater = GitHubUpdater(bot.api, bot)
    super_react = SuperReact(bot)
    

    @bot.command(name="nitro")
    def nitro_cmd(ctx, args):
        if not args:
            status = "ON" if ctx["bot"].nitro_sniper.enabled else "OFF"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Nitro Sniper ]\n> Status: {status}\n> Codes checked: {len(ctx['bot'].nitro_sniper.used_codes)}\n\n> +nitro on/off\n> +nitro clear\n> +nitro stats```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0] == "on":
            ctx["bot"].nitro_sniper.toggle(True)
            msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n+ Nitro sniper enabled```")
        
        elif args[0] == "off":
            ctx["bot"].nitro_sniper.toggle(False)
            msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n- Nitro sniper disabled```")
        
        elif args[0] == "clear":
            count = ctx["bot"].nitro_sniper.clear_codes()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Nitro ]\n> Cleared {count} codes```")
        
        elif args[0] == "stats":
            stats = ctx["bot"].nitro_sniper.get_stats()
            status = "ON" if stats["enabled"] else "OFF"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Nitro Stats ]\n> Status: {status}\n> Codes checked: {stats['used_codes']}```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="agct", aliases=["antigctrap"])
    def agct_cmd(ctx, args):
        agct = ctx["bot"].anti_gc_trap
        
        if not args:
            status = "ON" if agct.enabled else "OFF"
            block = "ON" if agct.block_creators else "OFF"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> Status: {status}\n> Block Creators: {block}\n> Whitelisted: {len(agct.whitelist)}\n\n> +agct on/off\n> +agct block on/off\n> +agct msg <text>\n> +agct name <name>\n> +agct icon <url>\n> +agct webhook <url>\n> +agct wl add <user_id>\n> +agct wl remove <user_id>\n> +agct wl list```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0] == "on":
            agct.enabled = True
            print(f"[AGCT] Enabled: {agct.enabled}")
            msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n+ Anti-GC Trap enabled```")
        
        elif args[0] == "off":
            agct.enabled = False
            print(f"[AGCT] Enabled: {agct.enabled}")
            msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n- Anti-GC Trap disabled```")
        
        elif args[0] == "block":
            if len(args) >= 2:
                if args[1] == "on":
                    agct.block_creators = True
                    msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n+ Block creators enabled```")
                elif args[1] == "off":
                    agct.block_creators = False
                    msg = ctx["api"].send_message(ctx["channel_id"], "```diff\n- Block creators disabled```")
        
        elif args[0] == "msg" and len(args) >= 2:
            message = " ".join(args[1:])
            agct.leave_message = message
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> Leave message set: {message[:50]}...```")
        
        elif args[0] == "name" and len(args) >= 2:
            name = " ".join(args[1:])
            agct.gc_name = name
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> GC name set: {name}```")
        
        elif args[0] == "icon" and len(args) >= 2:
            url = args[1]
            agct.gc_icon_url = url
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> GC icon URL set```")
        
        elif args[0] == "webhook" and len(args) >= 2:
            url = args[1]
            agct.webhook_url = url
            agct.save_whitelist()
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Anti-GC Trap ]\n> Webhook set```")
        
        elif args[0] == "wl":
            if len(args) >= 3:
                if args[1] == "add":
                    user_id = args[2]
                    success = agct.add_to_whitelist(user_id)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> Added {user_id} to whitelist```")
                
                elif args[1] == "remove":
                    user_id = args[2]
                    success = agct.remove_from_whitelist(user_id)
                    msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Anti-GC Trap ]\n> Removed {user_id} from whitelist```")
                
                elif args[1] == "list":
                    whitelist = agct.get_whitelist()
                    if whitelist:
                        wl_list = "\n".join([f"• {uid}" for uid in whitelist[:10]])
                        if len(whitelist) > 10:
                            wl_list += f"\n• ... and {len(whitelist) - 10} more"
                        msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Whitelist ]\n{wl_list}```")
                    else:
                        msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Anti-GC Trap ]\n> Whitelist empty```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="ms", aliases=["ping"])
    def ms(ctx, args):
        start = time.time()
        msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n> Testing latency...```")
        if msg:
            elapsed = (time.time() - start) * 1000
            ctx["api"].edit_message(ctx["channel_id"], msg.get("id"), f"```asciidoc\n[ Latency Test ]\n> {elapsed:.2f}ms```")
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="afk")
    def afk_cmd(ctx, args):
        reason = " ".join(args) if args else "AFK"
        success = afk_system.set_afk(ctx["author_id"], reason)
        
        if success:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ AFK ]\n> Set AFK: {reason}```")
            afk_system.save_state()
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ AFK ]\n> Failed to set AFK```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="unafk", aliases=["back"])
    def unafk_cmd(ctx, args):
        success = afk_system.remove_afk(ctx["author_id"])
        
        if success:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ AFK ]\n> AFK status removed```")
            afk_system.save_state()
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ AFK ]\n> You weren't AFK```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="afkwebhook")
    def afk_webhook_cmd(ctx, args):
        if not args:
            current = afk_system.webhook_url or "None"
            display = current if len(current) < 50 else current[:47] + "..."
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ AFK Webhook ]\n> Usage: +afkwebhook <webhook_url>\n> Current: {display}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        webhook_url = args[0]
        
        success = afk_system.set_webhook(webhook_url)
        afk_system.save_state()
        
        if success:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ AFK Webhook ]\n> Webhook set successfully```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ AFK Webhook ]\n> Failed to set webhook```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="afkstatus")
    def afk_status_cmd(ctx, args):
        target_id = args[0] if args else ctx["author_id"]
        
        if afk_system.is_afk(target_id):
            afk_data = afk_system.get_afk_info(target_id)
            afk_since = int(time.time() - afk_data["since"])
            
            hours = afk_since // 3600
            minutes = (afk_since % 3600) // 60
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}h "
            if minutes > 0 or hours == 0:
                time_str += f"{minutes}m"
            
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ AFK Status ]\n> User: {target_id}\n> Status: AFK\n> Reason: {afk_data['reason']}\n> Duration: {time_str}```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ AFK Status ]\n> User: {target_id}\n> Status: Online```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="spam")
    def spam(ctx, args):
        if len(args) >= 2:
            try:
                count = int(args[0])
                text = " ".join(args[1:])
                status = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Spam Started ]\n> Sending {count} messages...```")
                for i in range(count):
                    ctx["api"].send_message(ctx["channel_id"], f"{text} {i+1}")
                    time.sleep(0.5)
                if status:
                    delete_after_delay(ctx["api"], ctx["channel_id"], status.get("id"))
            except:
                pass
    
    @bot.command(name="purge")
    def purge(ctx, args):
        amount = int(args[0]) if args else 100
        status = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Purging ]\n> Deleting {amount} messages...```")
        messages = ctx["api"].get_messages(ctx["channel_id"], amount)
        deleted = 0
        for msg in messages:
            if msg["author"]["id"] == bot.user_id:
                ctx["api"].delete_message(ctx["channel_id"], msg["id"])
                deleted += 1
                time.sleep(0.3)
        if status:
            ctx["api"].edit_message(ctx["channel_id"], status.get("id"), f"```asciidoc\n[ Purge Complete ]\n> Deleted {deleted} messages```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status.get("id"))
    
    @bot.command(name="massdm")
    def mass_dm(ctx, args):
        if len(args) >= 2:
            try:
                option = int(args[0])
                message = " ".join(args[1:])
                
                option_names = {1: "DM History", 2: "Friends", 3: "Both"}
                if option not in [1, 2, 3]:
                    msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ DM Sender ]\n> Invalid option. Use 1, 2, or 3```")
                    if msg:
                        delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                    return
                
                status_msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ DM Sender ]\n> Mode: {option_names[option]}\n> Message: {message[:30]}...\n> Fetching targets...```")
                
                dms_response = ctx["api"].request("GET", "/users/@me/channels")
                if not dms_response or dms_response.status_code != 200:
                    ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ DM Sender ]\n> Failed to fetch DMs```")
                    delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
                    return
                
                dm_data = dms_response.json()
                targets = []
                target_names = []
                
                for dm in dm_data:
                    if dm.get("type") == 1 and dm.get("recipients"):
                        recipient = dm["recipients"][0] if dm["recipients"] else {}
                        user_id = recipient.get("id")
                        username = recipient.get("username", "Unknown")
                        if user_id:
                            targets.append((dm["id"], user_id, username))
                            target_names.append(username)
                
                if option == 2 or option == 3:
                    friends_response = ctx["api"].request("GET", "/users/@me/relationships")
                    if friends_response and friends_response.status_code == 200:
                        friends_data = friends_response.json()
                        for friend in friends_data:
                            if friend.get("type") == 1:
                                user = friend.get("user", {})
                                user_id = user.get("id")
                                username = user.get("username", "Unknown")
                                dm_found = False
                                for target in targets:
                                    if target[1] == user_id:
                                        dm_found = True
                                        break
                                if not dm_found:
                                    dm_channel = ctx["api"].create_dm(user_id)
                                    if dm_channel and "id" in dm_channel:
                                        targets.append((dm_channel["id"], user_id, username))
                                        target_names.append(username)
                
                if not targets:
                    ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ DM Sender ]\n> No targets found```")
                    delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
                    return
                
                sent = 0
                total = len(targets)
                failed = 0
                current_target = ""
                
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ DM Sender ]\n> Mode: {option_names[option]}\n> Targets: {total}\n> Status: Starting...\n> Sent: 0/{total}\n> Failed: 0```")
                
                for i, (channel_id, user_id, username) in enumerate(targets):
                    current_target = username
                    result = ctx["api"].send_message(channel_id, message)
                    if result:
                        sent += 1
                    else:
                        failed += 1
                    
                    if (i + 1) % 3 == 0 or i == total - 1:
                        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ DM Sender ]\n> Mode: {option_names[option]}\n> Targets: {total}\n> Status: Sending...\n> Sent: {sent}/{total}\n> Failed: {failed}\n> Current: {username}```")
                    
                    time.sleep(random.uniform(2.5, 4.0))
                
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ DM Sender ]\n> Mode: {option_names[option]}\n> Status: Complete\n> Sent: {sent}/{total}\n> Failed: {failed}\n> Time: {time.strftime('%H:%M:%S')}```")
                delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
                
            except Exception as e:
                print(f"Mass DM error: {e}")
                help_text = """```asciidoc
[ DM Sender Options ]
1 :: Mass DM all your DM history
2 :: Mass DM all your friends (with existing DMs)
3 :: Both (DM history + friends with existing DMs)

Usage: +massdm <1|2|3> <message>
Example: +massdm 1 Hello everyone!```"""
                msg = ctx["api"].send_message(ctx["channel_id"], help_text)
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="block")
    def block_user(ctx, args):
        if args:
            status = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Block User ]\n> Blocking {args[0]}...```")
            result = ctx["api"].block_user(args[0])
            if status:
                if result:
                    ctx["api"].edit_message(ctx["channel_id"], status.get("id"), "```asciidoc\n[ Block User ]\n> Successfully blocked```")
                else:
                    ctx["api"].edit_message(ctx["channel_id"], status.get("id"), "```asciidoc\n[ Block User ]\n> Failed to block```")
                delete_after_delay(ctx["api"], ctx["channel_id"], status.get("id"))

    @bot.command(name="setpfp")
    def setpfp(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set PFP ]\n> Please provide an image URL```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        image_url = args[0]
        
        try:
            response = ctx["api"].session.get(image_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set PFP ]\n> Failed to download image```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            content_type = response.headers.get('Content-Type', '')
            
            if 'gif' in content_type:
                image_format = 'gif'
            else:
                image_format = 'png'
            
            import base64
            image_b64 = base64.b64encode(image_bytes).decode()
            
            data = {
                "avatar": f"data:image/{image_format};base64,{image_b64}"
            }
            
            headers = ctx["api"].header_spoofer.get_headers()
            headers["Content-Type"] = "application/json"
            
            result = ctx["api"].session.patch(
                "https://discord.com/api/v9/users/@me",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Successfully updated profile picture\n> URL: {image_url}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Failed to update PFP: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="superreact", aliases=["sr"])
    def superreact_cmd(ctx, args):
        if len(args) >= 2:
            target_arg, emoji = args[0], args[1]
            target_id = super_react.parse_target_id(target_arg)
            if target_id:
                super_react.targets[target_id] = emoji
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ SuperReact ]\n✓ Enabled for user\nTarget: <@{target_id}>\nEmoji: {emoji}```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="superreactstop", aliases=["srstop"])
    def superreact_stop_cmd(ctx, args):
        if args:
            target_id = super_react.parse_target_id(args[0])
            if target_id in super_react.targets:
                emoji = super_react.targets[target_id]
                del super_react.targets[target_id]
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ SuperReact ]\n✗ Disabled for user\nTarget: <@{target_id}>\nEmoji: {emoji}```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="superreactlist", aliases=["srlist"])
    def superreact_list_cmd(ctx, args):
        if not super_react.targets and not super_react.msr_targets and not super_react.ssr_targets:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ SuperReact ]\nNo active super-reactions```")
        else:
            response = "```asciidoc\n[ SuperReact Status ]\n"
            if super_react.targets:
                response += "\nSingle SuperReactions:\n"
                for target, emoji in super_react.targets.items():
                    response += f"• <@{target}> → {emoji}\n"
            
            if super_react.msr_targets:
                response += "\nCycle SuperReactions:\n"
                for target, (emojis, idx) in super_react.msr_targets.items():
                    response += f"• <@{target}> → {', '.join(emojis)} (current: {emojis[idx]})\n"
            
            if super_react.ssr_targets:
                response += "\nMulti SuperReactions:\n"
                for target, emojis in super_react.ssr_targets.items():
                    response += f"• <@{target}> → {', '.join(emojis)}\n"
            
            response += "```"
            msg = ctx["api"].send_message(ctx["channel_id"], response)
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="superreactrandom", aliases=["srrandom"])
    def superreact_random_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ SuperReact Random ]\nUsage: +srrandom <message_id>```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        target_msg_id = args[0].strip()
        if not target_msg_id.isdigit():
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ SuperReact Random ]\nError: Invalid message ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ SuperReact Random ]\nAdding super-reactions to message {target_msg_id}...```")
        
        added_emojis = []
        available_emojis = super_react.emojis.copy()
        while len(added_emojis) < 10 and available_emojis:
            emoji = random.choice(available_emojis)
            available_emojis.remove(emoji)
            try:
                super_react.send_super_reaction(ctx["channel_id"], target_msg_id, emoji)
                added_emojis.append(emoji)
                time.sleep(0.7)
            except Exception as e:
                print(f"[ERROR]: Failed to add {emoji} to {target_msg_id}: {e}")
                break
        
        msg2 = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ SuperReact Random ]\nComplete!\nMessage: {target_msg_id}\nAdded: {', '.join(added_emojis)}\nTotal: {len(added_emojis)}```")
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        if msg2:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg2.get("id"))
    
    @bot.command(name="guilds")
    def list_guilds(ctx, args):
        guilds = ctx["api"].get_guilds()
        count = len(guilds)
        msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Guilds ]\n> You're in {count} guilds```")
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="customize", aliases=["theme", "ui"])
    def customize_cmd(ctx, args):
        if not args:
            help_text = """```yaml
Customization Commands:
  Theme Settings:
    debug_color    - Set debug message color
    theme          - Set UI theme (dark/light)
    font_style     - Set font family
    cursor_style   - Set cursor appearance
    
  Terminal Settings:
    terminal_mode  - Set terminal emulation
    prompt_style   - Set prompt appearance
    time_format    - Set time display (12h/24h)
    
  UI Settings:
    ui_animation   - Toggle animations
    sound_effects  - Toggle sounds
    auto_save      - Toggle auto-save
    
  Color Palette:
    $customize color background #1e1e1e
    $customize color accent #00ff00
    $customize color warning #ff9900

Usage:
  $customize set theme dark
  $customize toggle ui_animation
  $customize list
  $customize reset all```"""
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "palette":
            palette_info = """```yaml
Color Palette Elements:
  background  - Main background color
  foreground  - Text color
  accent      - Primary accent color
  warning     - Warning/alert color
  error       - Error message color
  success     - Success message color
  info        - Information color

Example:
  $customize color accent #ff00ff
  $customize color background #000000```"""
            msg = ctx["api"].send_message(ctx["channel_id"], palette_info)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "terminal":
            terminal_info = """```ansi
\u001b[36mTerminal Modes Available:\u001b[0m
  • unix     - Unix/Linux style
  • windows  - Windows CMD style
  • powershell - PowerShell style
  • retro    - Retro terminal style
  • modern   - Modern terminal style

\u001b[36mPrompt Styles:\u001b[0m
  • arrow    - > 
  • dollar   - $ 
  • hash     - # 
  • custom   - Custom text

Example:
  $customize set terminal_mode retro
  $customize set prompt_style dollar```"""
            msg = ctx["api"].send_message(ctx["channel_id"], terminal_info)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return

    @bot.command(name="terminal", aliases=["term", "shell"])
    def terminal_cmd(ctx, args):
        term_active = bot.customizer.terminal_emulation
        if not args:
            status = "✓ Active" if term_active else "✗ Inactive"
            term_info = f"""```ansi
\u001b[33mTerminal Emulation Status:\u001b[0m
  Mode: {status}
  Style: {bot.customizer.get_setting('terminal_mode')}
  Prompt: {bot.customizer.get_setting('prompt_style')}
  Time Format: {bot.customizer.get_setting('time_format')}

\u001b[33mCommands:\u001b[0m
  +terminal toggle  - Toggle terminal mode
  +terminal style   - Show current style
  +terminal time    - Show formatted time```"""
            msg = ctx["api"].send_message(ctx["channel_id"], term_info)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "toggle":
            new_state = bot.customizer.toggle_terminal_mode()
            status = "✓ Enabled" if new_state else "✗ Disabled"
            msg = ctx["api"].send_message(ctx["channel_id"], f"```yaml\nTerminal Emulation:\n  Status: {status}\n  Mode: {bot.customizer.get_setting('terminal_mode')}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "style":
            import datetime
            now = datetime.datetime.now()
            if bot.customizer.get_setting('time_format') == '12h':
                time_str = now.strftime("%I:%M %p")
            else:
                time_str = now.strftime("%H:%M")
            
            style_demo = f"""```ansi
\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ echo "Terminal Style Demo"
Terminal Style Demo

\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ date
{now.strftime('%A, %B %d, %Y')} {time_str}

\u001b[32m{bot.customizer.get_setting('prompt_style')}\u001b[0m \u001b[36muser@bot\u001b[0m:\u001b[34m~\u001b[0m$ ```"""
            msg = ctx["api"].send_message(ctx["channel_id"], style_demo)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "time":
            import datetime
            now = datetime.datetime.now()
            
            if bot.customizer.get_setting('time_format') == '12h':
                time_display = now.strftime("%I:%M:%S %p")
            else:
                time_display = now.strftime("%H:%M:%S")
            
            date_display = now.strftime(bot.customizer.get_setting('date_format').replace('dd', '%d').replace('mm', '%m').replace('yyyy', '%Y'))
            
            msg = ctx["api"].send_message(ctx["channel_id"], f"```ansi\n\u001b[35m{date_display} \u001b[33m{time_display}\u001b[0m\nTerminal Mode: {bot.customizer.get_setting('terminal_mode')}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return

    @bot.command(name="ui", aliases=["interface", "settings"])
    def ui_cmd(ctx, args):
        if not args:
            settings = bot.customizer.config
            active = bot.customizer.get_active_customizations()
            
            ui_info = """```yaml
UI Configuration:
  Theme: {theme}
  Terminal Mode: {terminal_mode}
  Font: {font_style}
  Cursor: {cursor_style}
  Animations: {ui_animation}
  Sounds: {sound_effects}
  Auto-save: {auto_save}
  Time Format: {time_format}
  Date Format: {date_format}

Active Customizations: {active_count}
  {active_list}
  
Commands:
  +ui colors    - Show color palette
  +ui reset <setting> - Reset setting
  +ui save      - Save configuration```""".format(
                theme=settings['theme'],
                terminal_mode=settings['terminal_mode'],
                font_style=settings['font_style'],
                cursor_style=settings['cursor_style'],
                ui_animation='✓ On' if settings['ui_animation'] else '✗ Off',
                sound_effects='✓ On' if settings['sound_effects'] else '✗ Off',
                auto_save='✓ On' if settings['auto_save'] else '✗ Off',
                time_format=settings['time_format'],
                date_format=settings['date_format'],
                active_count=len(active),
                active_list='\n  '.join([f"• {item}" for item in active]) if active else "None"
            )
            
            msg = ctx["api"].send_message(ctx["channel_id"], ui_info)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "colors":
            palette = bot.customizer.color_palette
            colors_display = """```yaml
Color Palette:
  Background:  {background}
  Foreground:  {foreground}
  Accent:      {accent}
  Warning:     {warning}
  Error:       {error}
  Success:     {success}
  Info:        {info}

Example Usage:
  $customize color accent #ff00ff
  $customize color background #000000```""".format(**palette)
            
            msg = ctx["api"].send_message(ctx["channel_id"], colors_display)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "reset" and len(args) > 1:
            setting = args[1]
            if bot.customizer.reset_customization(setting):
                msg = ctx["api"].send_message(ctx["channel_id"], f"```yaml\nReset Complete:\n  Setting: {setting}\n  Status: ✓ Restored to default```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```yaml\nReset Failed:\n  Setting: {setting}\n  Status: ✗ Setting not found```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0].lower() == "save":
            try:
                import json
                with open("ui_config.json", "w") as f:
                    json.dump(bot.customizer.config, f, indent=2)
                msg = ctx["api"].send_message(ctx["channel_id"], "```yaml\nConfiguration Saved:\n  File: ui_config.json\n  Status: ✓ Success```")
            except:
                msg = ctx["api"].send_message(ctx["channel_id"], "```yaml\nSave Failed:\n  Status: ✗ Error writing file```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
    
    @bot.command(name="autoreact")
    def set_autoreact(ctx, args):
        if args:
            bot.auto_react_emoji = args[0]
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Auto-React ]\n> Set to: {args[0]}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            bot.auto_react_emoji = None
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Auto-React ]\n> Disabled```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="mutualinfo")
    def mutualinfo(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]
        
        user_info = ctx["api"].request("GET", f"/users/{target_id}")
        if not user_info or user_info.status_code != 200:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Mutual Info ]\n> Could not find user with ID {target_id}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_data = user_info.json()
        username = user_data.get("username", "Unknown")
        discriminator = user_data.get("discriminator", "0000")
        
        guilds_response = ctx["api"].request("GET", f"/users/{target_id}/guilds")
        mutual_guilds = []
        
        if guilds_response and guilds_response.status_code == 200:
            target_guilds = guilds_response.json()
            my_guilds = ctx["api"].get_guilds()
            my_guild_ids = [g["id"] for g in my_guilds]
            
            for guild in target_guilds:
                if guild["id"] in my_guild_ids:
                    mutual_guilds.append(guild["name"])
        
        if mutual_guilds:
            guilds_text = "\n- ".join(mutual_guilds[:10])
            if len(mutual_guilds) > 10:
                guilds_text += f"\n- ... and {len(mutual_guilds) - 10} more"
            
            msg_text = f"```asciidoc\n[ Mutual Info ]\n> User: {username}#{discriminator}\n> Mutual Servers ({len(mutual_guilds)}):\n- {guilds_text}```"
        else:
            msg_text = f"```asciidoc\n[ Mutual Info ]\n> User: {username}#{discriminator}\n> No mutual servers found```"
        
        msg = ctx["api"].send_message(ctx["channel_id"], msg_text)
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="closedms")
    def closedms(ctx, args):
        status_msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Close DMs ]\n> Fetching DM channels...```")
        
        dms_response = ctx["api"].request("GET", "/users/@me/channels")
        if not dms_response or dms_response.status_code != 200:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ Close DMs ]\n> Failed to fetch DMs```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
            return
        
        dm_data = dms_response.json()
        dm_channels = []
        
        for dm in dm_data:
            if dm.get("type") == 1:
                dm_channels.append(dm)
        
        if not dm_channels:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ Close DMs ]\n> No DM channels to close```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
            return
        
        closed_count = 0
        total = len(dm_channels)
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ Close DMs ]\n> Closing {total} DM channels...\n> Closed: 0/{total}```")
        
        for i, dm in enumerate(dm_channels):
            try:
                result = ctx["api"].request("DELETE", f"/channels/{dm['id']}")
                if result and result.status_code in [200, 204]:
                    closed_count += 1
                
                if (i + 1) % 5 == 0 or i == total - 1:
                    ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ Close DMs ]\n> Closing {total} DM channels...\n> Closed: {closed_count}/{total}```")
                
                time.sleep(0.5)
            except:
                pass
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ Close DMs ]\n> Successfully closed {closed_count}/{total} DM channels```")
        delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
    
    @bot.command(name="setpfp")
    def setpfp(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set PFP ]\n> Please provide an image URL```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        image_url = args[0]
        
        try:
            response = ctx["api"].session.get(image_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set PFP ]\n> Failed to download image```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            content_type = response.headers.get('Content-Type', '')
            
            if 'gif' in content_type:
                image_format = 'gif'
            else:
                image_format = 'png'
            
            image_b64 = base64.b64encode(image_bytes).decode()
            
            data = {
                "avatar": f"data:image/{image_format};base64,{image_b64}"
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Successfully updated profile picture```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Failed to update PFP: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set PFP ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="servercopy")
    def servercopy(ctx, args):
        global LAST_SERVER_COPY
        
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server Copy ]\n> Please provide a server ID to copy```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        server_id = args[0]
        
        status_msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Server Copy ]\n> Fetching server data for {server_id}...```")
        
        guild_response = ctx["api"].request("GET", f"/guilds/{server_id}")
        if not guild_response or guild_response.status_code != 200:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ Server Copy ]\n> Could not find server or no access```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
            return
        
        guild_data = guild_response.json()
        
        copy_data = {
            "name": guild_data.get("name", "Copied Server"),
            "icon": guild_data.get("icon", None),
            "roles": [],
            "channels": [],
            "categories": [],
            "emojis": []
        }
        
        roles_response = ctx["api"].request("GET", f"/guilds/{server_id}/roles")
        if roles_response and roles_response.status_code == 200:
            roles_data = roles_response.json()
            for role in roles_data:
                if not role.get("managed", False) and role.get("name") != "@everyone":
                    copy_data["roles"].append({
                        "name": role.get("name"),
                        "color": role.get("color", 0),
                        "permissions": role.get("permissions", 0),
                        "hoist": role.get("hoist", False),
                        "mentionable": role.get("mentionable", False),
                        "position": role.get("position", 0)
                    })
        
        channels_response = ctx["api"].request("GET", f"/guilds/{server_id}/channels")
        if channels_response and channels_response.status_code == 200:
            channels_data = channels_response.json()
            for channel in channels_data:
                channel_type = channel.get("type", 0)
                if channel_type == 4:
                    copy_data["categories"].append({
                        "name": channel.get("name"),
                        "position": channel.get("position", 0),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
                elif channel_type == 0:
                    copy_data["channels"].append({
                        "type": "text",
                        "name": channel.get("name"),
                        "topic": channel.get("topic", ""),
                        "nsfw": channel.get("nsfw", False),
                        "position": channel.get("position", 0),
                        "parent_id": channel.get("parent_id"),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
                elif channel_type == 2:
                    copy_data["channels"].append({
                        "type": "voice",
                        "name": channel.get("name"),
                        "bitrate": channel.get("bitrate", 64000),
                        "user_limit": channel.get("user_limit", 0),
                        "position": channel.get("position", 0),
                        "parent_id": channel.get("parent_id"),
                        "overwrites": channel.get("permission_overwrites", [])
                    })
        
        emojis_response = ctx["api"].request("GET", f"/guilds/{server_id}/emojis")
        if emojis_response and emojis_response.status_code == 200:
            emojis_data = emojis_response.json()
            for emoji in emojis_data:
                if emoji.get("available", True):
                    copy_data["emojis"].append({
                        "name": emoji.get("name"),
                        "animated": emoji.get("animated", False),
                        "url": f"https://cdn.discordapp.com/emojis/{emoji['id']}.{'gif' if emoji.get('animated', False) else 'png'}"
                    })
        
        LAST_SERVER_COPY = copy_data
        
        ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ Server Copy ]\n> Successfully copied server: {guild_data.get('name', 'Unknown')}\n> Use +serverload <target_id> to apply```")
        delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
    
    @bot.command(name="serverload")
    def serverload(ctx, args):
        global LAST_SERVER_COPY
        
        if not LAST_SERVER_COPY:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server Load ]\n> No server data to load. Use +servercopy first```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server Load ]\n> Please provide a target server ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        target_id = args[0]
        
        status_msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Server Load ]\n> Loading template into server {target_id}...```")
        
        try:
            if LAST_SERVER_COPY.get("icon"):
                icon_response = ctx["api"].session.get(f"https://cdn.discordapp.com/icons/{target_id}/{LAST_SERVER_COPY['icon']}.png", timeout=10)
                if icon_response.status_code == 200:
                    icon_bytes = icon_response.content
                    icon_b64 = base64.b64encode(icon_bytes).decode()
                    icon_data = f"data:image/png;base64,{icon_b64}"
                    
                    update_data = {
                        "name": LAST_SERVER_COPY["name"],
                        "icon": icon_data
                    }
                else:
                    update_data = {"name": LAST_SERVER_COPY["name"]}
            else:
                update_data = {"name": LAST_SERVER_COPY["name"]}
            
            guild_update = ctx["api"].request("PATCH", f"/guilds/{target_id}", data=update_data)
            if not guild_update or guild_update.status_code != 200:
                ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ Server Load ]\n> Failed to update server name/icon```")
                delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
                return
            
            existing_channels = ctx["api"].request("GET", f"/guilds/{target_id}/channels")
            if existing_channels and existing_channels.status_code == 200:
                for channel in existing_channels.json():
                    try:
                        ctx["api"].request("DELETE", f"/channels/{channel['id']}")
                        time.sleep(0.5)
                    except:
                        pass
            
            existing_roles = ctx["api"].request("GET", f"/guilds/{target_id}/roles")
            if existing_roles and existing_roles.status_code == 200:
                for role in existing_roles.json():
                    if not role.get("managed", False) and role.get("name") != "@everyone":
                        try:
                            ctx["api"].request("DELETE", f"/guilds/{target_id}/roles/{role['id']}")
                            time.sleep(0.5)
                        except:
                            pass
            
            role_map = {}
            for role_data in LAST_SERVER_COPY["roles"]:
                try:
                    role_create = {
                        "name": role_data["name"],
                        "color": role_data["color"],
                        "permissions": str(role_data["permissions"]),
                        "hoist": role_data["hoist"],
                        "mentionable": role_data["mentionable"]
                    }
                    
                    role_response = ctx["api"].request("POST", f"/guilds/{target_id}/roles", data=role_create)
                    if role_response and role_response.status_code == 200:
                        role_map[role_data["name"]] = role_response.json()["id"]
                    
                    time.sleep(0.5)
                except:
                    pass
            
            category_map = {}
            for category_data in LAST_SERVER_COPY["categories"]:
                try:
                    category_create = {
                        "name": category_data["name"],
                        "type": 4,
                        "position": category_data["position"]
                    }
                    
                    cat_response = ctx["api"].request("POST", f"/guilds/{target_id}/channels", data=category_create)
                    if cat_response and cat_response.status_code == 200:
                        category_map[category_data["name"]] = cat_response.json()["id"]
                    
                    time.sleep(0.5)
                except:
                    pass
            
            for channel_data in LAST_SERVER_COPY["channels"]:
                try:
                    channel_create = {
                        "name": channel_data["name"],
                        "type": 0 if channel_data["type"] == "text" else 2,
                        "position": channel_data["position"],
                        "parent_id": category_map.get(channel_data.get("parent_id")) if channel_data.get("parent_id") else None
                    }
                    
                    if channel_data["type"] == "text":
                        channel_create["topic"] = channel_data.get("topic", "")
                        channel_create["nsfw"] = channel_data.get("nsfw", False)
                    elif channel_data["type"] == "voice":
                        channel_create["bitrate"] = channel_data.get("bitrate", 64000)
                        channel_create["user_limit"] = channel_data.get("user_limit", 0)
                    
                    chan_response = ctx["api"].request("POST", f"/guilds/{target_id}/channels", data=channel_create)
                    
                    time.sleep(1)
                except:
                    pass
            
            for emoji_data in LAST_SERVER_COPY["emojis"]:
                try:
                    emoji_response = ctx["api"].session.get(emoji_data["url"], timeout=10)
                    if emoji_response.status_code == 200:
                        emoji_bytes = emoji_response.content
                        emoji_b64 = base64.b64encode(emoji_bytes).decode()
                        
                        emoji_create = {
                            "name": emoji_data["name"],
                            "image": f"data:image/{'gif' if emoji_data.get('animated', False) else 'png'};base64,{emoji_b64}"
                        }
                        
                        ctx["api"].request("POST", f"/guilds/{target_id}/emojis", data=emoji_create)
                        
                        time.sleep(0.5)
                except:
                    pass
            
            LAST_SERVER_COPY = None
            
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), "```asciidoc\n[ Server Load ]\n> Successfully loaded server template!```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
            
        except Exception as e:
            ctx["api"].edit_message(ctx["channel_id"], status_msg.get("id"), f"```asciidoc\n[ Server Load ]\n> Error: {str(e)}```")
            delete_after_delay(ctx["api"], ctx["channel_id"], status_msg.get("id"))
    
    @bot.command(name="rpc", aliases=["rich_presence"])
    def rich_presence(ctx, args):
        if not args:
            help_text = """```asciidoc
[ RPC Commands ]
spotify "Song | Artist | Album | Duration [| image_url]"
listening "Details | State | Name [| image_url] [>> Button Label >> Button URL]"
streaming "Details | State | Name [| image_url] [>> Button Label >> Button URL]"
playing "Details | State | Name [| image_url] [>> Button Label >> Button URL]"
timer "Details | State | Name | Start | End [| image_url]"

Examples:
+rpc spotify "Song Name | Artist Name | Album Name | 3.5 | https://image.url"
+rpc listening "Playing my playlist | 15 tracks | Spotify | https://image.url >> Listen Now >> https://spotify.com"
+rpc streaming "Playing GTA V | In session | Twitch | https://image.url >> Watch Live >> https://twitch.tv"
+rpc playing "Level 85 | Questing | World of Warcraft | https://image.url"
+rpc timer "Workout session | 45 min left | Gym | 1700000000 | 1700003600 | https://image.url"```"""
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        parts = args[0].lower()
        remaining = " ".join(args[1:]) if len(args) > 1 else ""
        
        if parts == "stop":
            bot.set_activity(None)
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ RPC ]\n> Cleared all activities```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if not remaining:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ RPC ]\n> Missing arguments```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        image_url = None
        button_label = None
        button_url = None
        details = None
        state = None
        name = None
        
        main_text = remaining
        
        if ' >> ' in main_text:
            btn_split = main_text.split(' >> ')
            if len(btn_split) >= 3:
                main_text = btn_split[0].strip()
                button_label = btn_split[1].strip()
                button_url = btn_split[2].strip()
            elif len(btn_split) == 2:
                main_text = btn_split[0].strip()
                button_label = btn_split[1].strip()
                button_url = "https://discord.com"
        
        if ' | ' in main_text:
            pipe_parts = [part.strip() for part in main_text.split('|')]
            
            if parts == "spotify":
                if len(pipe_parts) >= 4:
                    song = pipe_parts[0]
                    artist = pipe_parts[1]
                    album = pipe_parts[2]
                    duration = pipe_parts[3]
                    
                    if len(pipe_parts) >= 5:
                        image_url = pipe_parts[4]
                    if len(pipe_parts) >= 6:
                        current_pos = pipe_parts[5]
                    
                    details = song
                    state = artist
                    name = "Spotify"
            
            elif parts in ["listening", "streaming", "playing"]:
                if len(pipe_parts) >= 3:
                    details = pipe_parts[0]
                    state = pipe_parts[1]
                    name = pipe_parts[2]
                    
                    if len(pipe_parts) >= 4:
                        image_url = pipe_parts[3]
            
            elif parts == "timer":
                if len(pipe_parts) >= 5:
                    details = pipe_parts[0]
                    state = pipe_parts[1]
                    name = pipe_parts[2]
                    start_time = pipe_parts[3]
                    end_time = pipe_parts[4]
                    
                    if len(pipe_parts) >= 6:
                        image_url = pipe_parts[5]
        
        async def run_async():
            if parts == "spotify":
                try:
                    if details and state and name:
                        duration_val = float(duration) if duration else 3.5
                        current_pos_val = float(current_pos) if 'current_pos' in locals() else 0
                        
                        await send_spotify_with_spoofing(bot, details, state, name, duration_val, current_pos_val, image_url)
                        msg_text = f"```asciidoc\n[ Spotify RPC ]\n> Song: {details}\n> Artist: {state}\n> Album: {name}\n> Duration: {duration_val}min```"
                        if current_pos_val > 0:
                            msg_text = msg_text.replace("```", f"\n> Position: {current_pos_val}min```")
                        if image_url:
                            msg_text = msg_text.replace("```", f"\n> Image: Yes```")
                    else:
                        msg_text = "```asciidoc\n[ Spotify RPC ]\n> Format: Song | Artist | Album | Duration [| image_url] [| position]\n> Example: +rpc spotify \"Song Name | Artist Name | Album Name | 3.5 | https://image.url | 1.5\"```"
                except Exception as e:
                    msg_text = f"```asciidoc\n[ Spotify RPC ]\n> Error: {str(e)}```"
            
            elif parts == "listening":
                try:
                    if name:
                        await send_listening_activity(bot, name, button_label, button_url, image_url, state, details)
                        msg_text = f"```asciidoc\n[ Listening RPC ]\n> Name: {name}```"
                        if details:
                            msg_text = msg_text.replace("```", f"\n> Details: {details}```")
                        if state:
                            msg_text = msg_text.replace("```", f"\n> State: {state}```")
                        if button_label:
                            msg_text = msg_text.replace("```", f"\n> Button: {button_label}```")
                        if image_url:
                            msg_text = msg_text.replace("```", f"\n> Image: Yes```")
                    else:
                        msg_text = "```asciidoc\n[ Listening RPC ]\n> Format: Details | State | Name [| image_url] [>> Button >> URL]\n> Example: +rpc listening \"Playing playlist | 15 tracks | Spotify | https://image.url >> Listen Now >> https://spotify.com\"```"
                except Exception as e:
                    msg_text = f"```asciidoc\n[ Listening RPC ]\n> Error: {str(e)}```"
            
            elif parts == "streaming":
                try:
                    if name:
                        await send_streaming_activity(bot, name, button_label, button_url, image_url, state, details)
                        msg_text = f"```asciidoc\n[ Streaming RPC ]\n> Name: {name}```"
                        if details:
                            msg_text = msg_text.replace("```", f"\n> Details: {details}```")
                        if state:
                            msg_text = msg_text.replace("```", f"\n> State: {state}```")
                        if button_label:
                            msg_text = msg_text.replace("```", f"\n> Button: {button_label}```")
                        if image_url:
                            msg_text = msg_text.replace("```", f"\n> Image: Yes```")
                    else:
                        msg_text = "```asciidoc\n[ Streaming RPC ]\n> Format: Details | State | Name [| image_url] [>> Button >> URL]\n> Example: +rpc streaming \"Playing GTA V | In session | Twitch | https://image.url >> Watch Live >> https://twitch.tv\"```"
                except Exception as e:
                    msg_text = f"```asciidoc\n[ Streaming RPC ]\n> Error: {str(e)}```"
            
            elif parts == "playing":
                try:
                    if name:
                        await send_playing_activity(bot, name, button_label, button_url, image_url, state, details)
                        msg_text = f"```asciidoc\n[ Playing RPC ]\n> Game: {name}```"
                        if details:
                            msg_text = msg_text.replace("```", f"\n> Details: {details}```")
                        if state:
                            msg_text = msg_text.replace("```", f"\n> State: {state}```")
                        if button_label:
                            msg_text = msg_text.replace("```", f"\n> Button: {button_label}```")
                        if image_url:
                            msg_text = msg_text.replace("```", f"\n> Image: Yes```")
                    else:
                        msg_text = "```asciidoc\n[ Playing RPC ]\n> Format: Details | State | Name [| image_url] [>> Button >> URL]\n> Example: +rpc playing \"Level 85 | Questing | World of Warcraft | https://image.url\"```"
                except Exception as e:
                    msg_text = f"```asciidoc\n[ Playing RPC ]\n> Error: {str(e)}```"
            
            elif parts == "timer":
                try:
                    if name and 'start_time' in locals() and 'end_time' in locals():
                        start_val = float(start_time) if start_time else time.time()
                        end_val = float(end_time) if end_time else time.time() + 3600
                        
                        await send_timer_activity(bot, name, start_val, end_val, details, state, image_url)
                        duration_min = int((end_val - start_val) / 60)
                        msg_text = f"```asciidoc\n[ Timer RPC ]\n> Activity: {name}\n> Duration: {duration_min}min```"
                        if details:
                            msg_text = msg_text.replace("```", f"\n> Details: {details}```")
                        if state:
                            msg_text = msg_text.replace("```", f"\n> State: {state}```")
                        if image_url:
                            msg_text = msg_text.replace("```", f"\n> Image: Yes```")
                    else:
                        msg_text = "```asciidoc\n[ Timer RPC ]\n> Format: Details | State | Name | Start | End [| image_url]\n> Example: +rpc timer \"Workout session | 45 min left | Gym | 1700000000 | 1700003600 | https://image.url\"```"
                except Exception as e:
                    msg_text = f"```asciidoc\n[ Timer RPC ]\n> Error: {str(e)}```"
            
            else:
                msg_text = "```asciidoc\n[ RPC ]\n> Invalid type. Use: spotify, listening, streaming, playing, timer```"
            
            msg = ctx["api"].send_message(ctx["channel_id"], msg_text)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        
        asyncio.run(run_async())

    @bot.command(name="setserverpfp", aliases=["serverspfp", "guildpfp"])
    def setserverpfp(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server PFP ]\n> Please provide an image URL```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        image_url = args[0]
        
        try:
            response = ctx["api"].session.get(image_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server PFP ]\n> Failed to download image```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            content_type = response.headers.get('Content-Type', '')
            
            if 'gif' in content_type:
                image_format = 'gif'
            else:
                image_format = 'png'
            
            image_b64 = base64.b64encode(image_bytes).decode()
            
            guild_id = ctx["message"].get("guild_id")
            if not guild_id:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Server PFP ]\n> This command only works in servers```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            data = {
                "avatar": f"data:image/{image_format};base64,{image_b64}"
            }
            
            result = ctx["api"].request("PATCH", f"/guilds/{guild_id}/members/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Server PFP ]\n> Successfully updated server profile picture```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Server PFP ]\n> Failed to update server PFP: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Server PFP ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="stealpfp", aliases=["copypfp", "takepfp"])
    def stealpfp(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal PFP ]\n> Please provide a user ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0]
        
        try:
            user_response = ctx["api"].request("GET", f"/users/{user_id}")
            if not user_response or user_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal PFP ]\n> Could not find user```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            user_data = user_response.json()
            avatar_hash = user_data.get("avatar")
            
            if not avatar_hash:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal PFP ]\n> User has no profile picture```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            avatar_format = "gif" if avatar_hash.startswith("a_") else "png"
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{avatar_format}?size=1024"
            
            response = ctx["api"].session.get(avatar_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal PFP ]\n> Failed to download avatar```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            image_b64 = base64.b64encode(image_bytes).decode()
            
            data = {
                "avatar": f"data:image/{avatar_format};base64,{image_b64}"
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal PFP ]\n> Successfully stole profile picture from user ID: {user_id}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal PFP ]\n> Failed to update PFP: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal PFP ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="setbanner", aliases=["banner"])
    def setbanner(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Banner ]\n> Please provide an image URL```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        image_url = args[0]
        
        try:
            response = ctx["api"].session.get(image_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Banner ]\n> Failed to download image```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            content_type = response.headers.get('Content-Type', '')
            
            if 'gif' in content_type:
                image_format = 'gif'
            else:
                image_format = 'png'
            
            image_b64 = base64.b64encode(image_bytes).decode()
            
            data = {
                "banner": f"data:image/{image_format};base64,{image_b64}"
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Banner ]\n> Successfully updated banner```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Banner ]\n> Failed to update banner: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Banner ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="stealbanner", aliases=["copybanner", "takebanner"])
    def stealbanner(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Banner ]\n> Please provide a user ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0]
        
        try:
            profile_response = ctx["api"].request("GET", f"/users/{user_id}/profile")
            if not profile_response or profile_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Banner ]\n> Could not fetch user profile```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            profile_data = profile_response.json()
            banner_hash = profile_data.get("user", {}).get("banner")
            
            if not banner_hash:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Banner ]\n> User has no banner```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            banner_format = "gif" if banner_hash.startswith("a_") else "png"
            banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{banner_format}?size=1024"
            
            response = ctx["api"].session.get(banner_url, timeout=10)
            if response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Banner ]\n> Failed to download banner```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            image_bytes = response.content
            image_b64 = base64.b64encode(image_bytes).decode()
            
            data = {
                "banner": f"data:image/{banner_format};base64,{image_b64}"
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Banner ]\n> Successfully stole banner from user ID: {user_id}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Banner ]\n> Failed to update banner: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Banner ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="pronouns")
    def pronouns(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]
        
        try:
            profile_response = ctx["api"].request("GET", f"/users/{target_id}/profile")
            if not profile_response or profile_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Pronouns ]\n> Could not fetch user profile```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            profile_data = profile_response.json()
            pronouns = profile_data.get("user_profile", {}).get("pronouns", "")
            
            user_response = ctx["api"].request("GET", f"/users/{target_id}")
            if user_response and user_response.status_code == 200:
                user_data = user_response.json()
                username = user_data.get("username", "Unknown")
            else:
                username = "Unknown"
            
            if pronouns:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Pronouns ]\n> User: {username}\n> Pronouns: {pronouns}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Pronouns ]\n> User: {username}\n> No pronouns set```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Pronouns ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="setpronouns", aliases=["setpronoun"])
    def setpronouns(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Pronouns ]\n> Please provide pronouns to set```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        pronouns = " ".join(args)
        
        try:
            data = {
                "pronouns": pronouns
            }
            
            result = ctx["api"].request("PATCH", "/users/@me/profile", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Pronouns ]\n> Successfully set pronouns to: {pronouns}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Pronouns ]\n> Failed to set pronouns: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Pronouns ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="bio")
    def bio(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]
        
        try:
            profile_response = ctx["api"].request("GET", f"/users/{target_id}/profile")
            if not profile_response or profile_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Bio ]\n> Could not fetch user profile```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            profile_data = profile_response.json()
            bio_text = profile_data.get("user_profile", {}).get("bio", "")
            
            user_response = ctx["api"].request("GET", f"/users/{target_id}")
            if user_response and user_response.status_code == 200:
                user_data = user_response.json()
                username = user_data.get("username", "Unknown")
            else:
                username = "Unknown"
            
            if bio_text:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Bio ]\n> User: {username}\n> Bio:\n{bio_text}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Bio ]\n> User: {username}\n> No bio set```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Bio ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="setbio", aliases=["setaboutme"])
    def setbio(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Bio ]\n> Please provide a bio to set```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        bio_text = " ".join(args)
        
        try:
            data = {
                "bio": bio_text
            }
            
            result = ctx["api"].request("PATCH", "/users/@me/profile", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Bio ]\n> Successfully set bio```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Bio ]\n> Failed to set bio: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Bio ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="displayname", aliases=["globalname"])
    def displayname(ctx, args):
        if not args:
            target_id = ctx["author_id"]
        else:
            target_id = args[0]
        
        try:
            user_response = ctx["api"].request("GET", f"/users/{target_id}")
            if not user_response or user_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Display Name ]\n> Could not find user```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            user_data = user_response.json()
            username = user_data.get("username", "Unknown")
            global_name = user_data.get("global_name", "")
            
            if global_name:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Display Name ]\n> User: {username}\n> Display Name: {global_name}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Display Name ]\n> User: {username}\n> No display name set```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Display Name ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="setdisplayname", aliases=["setglobalname"])
    def setdisplayname(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Display Name ]\n> Please provide a display name```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        display_name = " ".join(args)
        
        try:
            data = {
                "global_name": display_name
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Display Name ]\n> Successfully set display name to: {display_name}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Display Name ]\n> Failed to set display name: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Display Name ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="stealname", aliases=["copyname"])
    def stealname(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Name ]\n> Please provide a user ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0]
        
        try:
            user_response = ctx["api"].request("GET", f"/users/{user_id}")
            if not user_response or user_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Name ]\n> Could not find user```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            user_data = user_response.json()
            global_name = user_data.get("global_name", "")
            
            if not global_name:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Name ]\n> User has no display name```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            data = {
                "global_name": global_name
            }
            
            result = ctx["api"].request("PATCH", "/users/@me", data=data)
            
            if result and result.status_code == 200:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Name ]\n> Successfully stole display name: {global_name}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Name ]\n> Failed to set display name: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Name ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        
    @bot.command(name="stop", aliases=["exit", "quit"])
    def stop_bot(ctx, args):
        msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ System ]\n> Stopping bot...```")
        bot.stop()
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="setstatus", aliases=["customstatus"])
    def setstatus(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Status ]\n> Please provide a status\n> Format: +setstatus [emoji,] status text\n> Example: +setstatus 🎮 Gaming now\n> Example: +setstatus <:pepe:123456789>, Custom status```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        import re
        
        full_text = " ".join(args)
        emoji_name = None
        emoji_id = None
        message = full_text.strip()
        
        if ',' in message:
            parts = message.split(',', 1)
            emoji_part = parts[0].strip()
            text_part = parts[1].strip() if len(parts) > 1 else ""
            
            if not text_part:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Status ]\n> Please provide status text after comma```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            custom_emoji_pattern = r"<:([a-zA-Z0-9_]+):([0-9]+)>"
            custom_emoji_match = re.match(custom_emoji_pattern, emoji_part)
            
            if custom_emoji_match:
                emoji_name = custom_emoji_match.group(1)
                emoji_id = custom_emoji_match.group(2)
            
            elif len(emoji_part) == 1 or (len(emoji_part) > 1 and any(ord(c) > 127 for c in emoji_part)):
                emoji_name = emoji_part
            
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Status ]\n> Invalid emoji format\n> Use standard emoji or <:name:id>```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            message = text_part
        
        if not message:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Set Status ]\n> Please provide status text```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        data = {
            "custom_status": {
                "text": message,
                "emoji_name": emoji_name,
                "emoji_id": emoji_id
            }
        }
        
        try:
            result = ctx["api"].request("PATCH", "/users/@me/settings", data=data)
            
            if result and result.status_code == 200:
                emoji_display = f"{emoji_name} " if emoji_name else ""
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Status ]\n> Successfully set status\n> Status: {emoji_display}{message}```")
            elif result and result.status_code == 429:
                retry_after = int(result.headers.get("Retry-After", 1))
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Status ]\n> Rate limited\n> Try again in {retry_after} seconds```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Status ]\n> Failed to set status\n> Code: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Set Status ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="stealstatus", aliases=["copystatus"])
    def stealstatus(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Status ]\n> Please provide a user ID```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        user_id = args[0]
        
        try:
            import re
            
            profile_response = ctx["api"].request("GET", f"/users/{user_id}/profile")
            if not profile_response or profile_response.status_code != 200:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Steal Status ]\n> Could not fetch user profile```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            profile_data = profile_response.json()
            user_profile = profile_data.get("user_profile", {})
            
            custom_status = user_profile.get("bio", "")
            if not custom_status:
                user_response = ctx["api"].request("GET", f"/users/{user_id}")
                if user_response and user_response.status_code == 200:
                    user_data = user_response.json()
                    username = user_data.get("username", "Unknown")
                else:
                    username = "Unknown"
                
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Status ]\n> User: {username}\n> No custom status found```")
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                return
            
            message = custom_status
            emoji_name = None
            emoji_id = None
            
            user_response = ctx["api"].request("GET", f"/users/{user_id}")
            if user_response and user_response.status_code == 200:
                user_data = user_response.json()
                username = user_data.get("username", "Unknown")
            else:
                username = "Unknown"
            
            data = {
                "custom_status": {
                    "text": message,
                    "emoji_name": emoji_name,
                    "emoji_id": emoji_id
                }
            }
            
            result = ctx["api"].request("PATCH", "/users/@me/settings", data=data)
            
            if result and result.status_code == 200:
                emoji_display = f"{emoji_name} " if emoji_name else ""
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Status ]\n> Successfully stole status\n> From: {username}\n> Status: {emoji_display}{message}```")
            elif result and result.status_code == 429:
                retry_after = int(result.headers.get("Retry-After", 1))
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Status ]\n> Rate limited\n> Try again in {retry_after} seconds```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Status ]\n> Failed to steal status\n> Code: {result.status_code if result else 'No response'}```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Steal Status ]\n> Error: {str(e)}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="help", aliases=["h", "commands"])
    def show_help(ctx, args):
        help_pages = {
            "utility": """```asciidoc
[ Utility Commands ]
ms :: Test bot latency
purge [amount] :: Delete your messages
guilds :: Count guilds
mutualinfo [user_id] :: Show mutual servers
autoreact [emoji] :: Auto-react to your messages
customize :: UI/terminal customization
terminal :: Terminal settings
ui :: Interface settings
stop :: Stop bot
web :: Open web control panel
restart :: Restart bot```""", 
            
            "messaging": """```asciidoc
[ Messaging Commands ]
spam <count> <text> :: Spam messages
massdm <option> <msg> :: Mass DM (1=DM history, 2=friends, 3=both)
closedms :: Close all DM channels```""",
            
            "profile": """```asciidoc
[ Profile Commands ]
setpfp <url> :: Set profile picture
stealpfp <user_id> :: Steal user's PFP
setbanner <url> :: Set banner
stealbanner <user_id> :: Steal user's banner
setpronouns <text> :: Set pronouns
setbio <text> :: Set bio
setdisplayname <text> :: Set display name
stealname <user_id> :: Steal display name
setstatus [emoji,] text :: Set custom status
stealstatus <user_id> :: Steal user's status
pronouns [user_id] :: View pronouns
bio [user_id] :: View bio
displayname [user_id] :: View display name```""",
            
            "server": """```asciidoc
[ Server Commands ]
servercopy <server_id> :: Copy server structure
serverload <target_id> :: Load copied server
setserverpfp <url> :: Set server profile picture```""",
            
            "voice": """```asciidoc
[ Voice Commands ]
vc [channel_id] :: Join voice/call
vce :: Leave voice/call```""",
            
            "social": """```asciidoc
[ Social Commands ]
block <user_id> :: Block user
rpc <type> <args> :: Set rich presence```""",
            
            "backup": """```asciidoc
[ Backup Commands ]
backup user :: Backup user data, friends, guilds
backup messages <channel_id> [limit] :: Backup channel messages
backup full :: Create complete backup (zipped)
backup list :: List all backups
backup restore <filename> :: Restore from backup```""",
            
            "moderation": """```asciidoc
[ Moderation Commands ]
mod kick <user_ids> :: Kick multiple users
mod ban <user_ids> [delete_days] :: Ban users
mod filter add <words> :: Add word filter
mod filter check <text> :: Check text against filters
mod cleanup channels :: Delete all channels
mod cleanup roles :: Delete all roles
mod members [limit] :: List server members
mod channels :: List all channels
mod roles :: List all roles```""",
            
            "hosting": """```asciidoc
[ Hosting Commands ]
host <token> :: Host a token (owner only)
stophost :: Stop hosting your token
listhosted :: List hosted tokens (owner only)```""",
            
            "afk": """```asciidoc
[ AFK Commands ]
afk [reason] :: Set AFK status
unafk, back :: Remove AFK status
afkstatus [user_id] :: Check AFK status
afkwebhook <url> :: Set notification webhook```""",
            
            "nitro": """```asciidoc
[ Nitro Commands ]
nitro on/off :: Toggle nitro sniper
nitro clear :: Clear used codes
nitro stats :: Show stats
nitro :: Show current status```""",
            
            "agct": """```asciidoc
[ Anti-GC Trap Commands ]
agct on/off :: Toggle anti-GC trap
agct block on/off :: Toggle blocking creators
agct msg <text> :: Set leave message
agct name <name> :: Set GC name
agct icon <url> :: Set GC icon
agct webhook <url> :: Set alert webhook
agct wl add <user_id> :: Add to whitelist
agct wl remove <user_id> :: Remove from whitelist
agct wl list :: Show whitelist```""",
            "raw": """```asciidoc
[ Raw Commands ]
cmdwall :: Display all commands in raw format```""",
            
            "all": """```asciidoc
[ All Commands - Page 1/3 ]
ms :: Test latency
spam <count> <text> :: Spam
purge [amount] :: Delete messages
massdm <option> <msg> :: Mass DM
block <user_id> :: Block user
guilds :: Count guilds
autoreact [emoji] :: Auto-react
mutualinfo [user_id] :: Mutual servers
closedms :: Close DMs
setpfp <url> :: Set PFP
stealpfp <user_id> :: Steal PFP
setbanner <url> :: Set banner
stealbanner <user_id> :: Steal banner
setpronouns <text> :: Set pronouns
host <token> :: Host token (owner)
afk [reason] :: Set AFK status
unafk :: Remove AFK
afkstatus [id] :: Check AFK
nitro on/off :: Nitro sniper
nitro clear :: Clear codes

[ All Commands - Page 2/3 ]
stophost :: Stop hosting
listhosted :: List hosted (owner)
setbio <text> :: Set bio
setdisplayname <text> :: Set display name
stealname <user_id> :: Steal name
setstatus [emoji,] text :: Set status
stealstatus <user_id> :: Steal status
pronouns [user_id] :: View pronouns
bio [user_id] :: View bio
displayname [user_id] :: View display
servercopy <server_id> :: Copy server
serverload <target_id> :: Load server
setserverpfp <url> :: Set server PFP
vc [channel_id] :: Join voice/call
vce :: Leave voice/call
rpc <type> <args> :: Rich presence
customize :: UI customization
terminal :: Terminal settings
ui :: Interface settings
agct on/off :: Anti-GC trap
agct block on/off :: Block creators
agct msg <text> :: Leave message
agct name <name> :: GC name
agct icon <url> :: GC icon

[ All Commands - Page 3/3 ]
agct webhook <url> :: Webhook
agct wl add/remove <id> :: Whitelist
backup user :: User backup
backup messages <ch> :: Message backup
backup full :: Full backup
backup list :: List backups
backup restore <file> :: Restore
mod kick <ids> :: Kick users
mod ban <ids> :: Ban users
mod filter :: Word filter
mod cleanup :: Clean channels/roles
mod members :: List members
mod channels :: List channels
mod roles :: List roles
web :: Web control panel
stop :: Stop bot
restart :: Restart bot
help [page] :: This help
cmdwall :: Show raw commands```"""
        }
        
        if not args:
            page_list = """```asciidoc
[ Help Pages Available ]
utility :: Basic utility commands
messaging :: Message & DM commands
profile :: Profile customization
server :: Server management
voice :: Voice/call commands
social :: Social & presence commands
backup :: Backup & restore tools
moderation :: Server moderation tools
hosting :: Token hosting commands
afk :: AFK system
nitro :: Nitro sniper
agct :: Anti-GC trap
raw :: Raw command display
all :: Show all commands (3 pages)

Usage: +help <page>
Example: +help profile
Example: +help all```"""
            
            if len(page_list) > 2000:
                part1 = page_list[:1997] + "```"
                part2 = "```asciidoc\n...continued```"
                msg1 = ctx["api"].send_message(ctx["channel_id"], part1)
                if msg1:
                    time.sleep(0.5)
                    msg2 = ctx["api"].send_message(ctx["channel_id"], part2)
                    if msg2:
                        delete_after_delay(ctx["api"], ctx["channel_id"], msg2.get("id"))
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg1.get("id"))
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], page_list)
                if msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        page = args[0].lower()
        if page in help_pages:
            content = help_pages[page]
            
            if len(content) > 2000:
                parts = []
                current = ""
                lines = content.split('\n')
                
                for line in lines:
                    if len(current + line + '\n') > 1990:
                        parts.append(current + "```")
                        current = "```asciidoc\n" + line + '\n'
                    else:
                        current += line + '\n'
                
                if current:
                    parts.append(current)
                
                for i, part in enumerate(parts):
                    msg = ctx["api"].send_message(ctx["channel_id"], part)
                    if msg and i < len(parts) - 1:
                        time.sleep(0.5)
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], content)
            
            if 'msg' in locals() and msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            page_options = "Available pages: utility, messaging, profile, server, voice, social, backup, moderation, hosting, afk, nitro, agct, raw, all"
            error_msg = f"```asciidoc\n[ Help ]\n> Invalid page\n> {page_options}```"
            
            msg = ctx["api"].send_message(ctx["channel_id"], error_msg)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="cmdwall", aliases=["commandsraw", "allcmds"])
    def cmdwall(ctx, args):
        all_commands = """```python
@bot.command(name="ms", aliases=["ping"])
@bot.command(name="spam")
@bot.command(name="purge")
@bot.command(name="massdm")
@bot.command(name="block")
@bot.command(name="guilds")
@bot.command(name="autoreact")
@bot.command(name="mutualinfo")
@bot.command(name="closedms")
@bot.command(name="setpfp")
@bot.command(name="stealpfp")
@bot.command(name="setserverpfp", aliases=["serverspfp", "guildpfp"])
@bot.command(name="setbanner", aliases=["banner"])
@bot.command(name="stealbanner", aliases=["copybanner", "takebanner"])
@bot.command(name="setpronouns", aliases=["setpronoun"])
@bot.command(name="pronouns")
@bot.command(name="setbio", aliases=["setaboutme"])
@bot.command(name="bio")
@bot.command(name="setdisplayname", aliases=["setglobalname"])
@bot.command(name="displayname", aliases=["globalname"])
@bot.command(name="stealname", aliases=["copyname"])
@bot.command(name="setstatus", aliases=["customstatus"])
@bot.command(name="stealstatus", aliases=["copystatus"])
@bot.command(name="servercopy")
@bot.command(name="serverload")
@bot.command(name="vc", aliases=["voice", "joinvc"])
@bot.command(name="vce", aliases=["leavevc", "disconnect"])
@bot.command(name="rpc", aliases=["rich_presence"])
@bot.command(name="nitro")
@bot.command(name="afk")
@bot.command(name="unafk", aliases=["back"])
@bot.command(name="afkwebhook")
@bot.command(name="afkstatus")
@bot.command(name="agct", aliases=["antigctrap"])
@bot.command(name="backup", aliases=["save"])
@bot.command(name="mod", aliases=["moderation"])
@bot.command(name="web", aliases=["panel"])
@bot.command(name="host")
@bot.command(name="stophost")
@bot.command(name="listhosted")
@bot.command(name="customize", aliases=["theme", "ui"])
@bot.command(name="terminal", aliases=["term", "shell"])
@bot.command(name="ui", aliases=["interface", "settings"])
@bot.command(name="help", aliases=["h", "commands"])
@bot.command(name="cmdwall", aliases=["commandsraw", "allcmds"])
@bot.command(name="stop", aliases=["exit", "quit"])
@bot.command(name="restart")
```"""
        
        if len(all_commands) > 2000:
            parts = []
            current = ""
            lines = all_commands.split('\n')
            
            for line in lines:
                if len(current + line + '\n') > 1990:
                    parts.append(current + "```")
                    current = "```python\n" + line + '\n'
                else:
                    current += line + '\n'
            
            if current:
                parts.append(current)
            
            for i, part in enumerate(parts):
                msg = ctx["api"].send_message(ctx["channel_id"], part)
                if msg and i < len(parts) - 1:
                    time.sleep(0.5)
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"), 3)
                elif msg:
                    delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], all_commands)
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="restart")
    def restart_cmd(ctx, args):
        msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ System ]\n> Restarting bot in 3 seconds...```")
        
        def restart_sequence():
            time.sleep(1)
            ctx["api"].edit_message(ctx["channel_id"], msg.get("id"), "```asciidoc\n[ System ]\n> Restarting bot in 2 seconds...```")
            time.sleep(1)
            ctx["api"].edit_message(ctx["channel_id"], msg.get("id"), "```asciidoc\n[ System ]\n> Restarting bot in 1 second...```")
            time.sleep(1)
            
            ctx["api"].send_message(ctx["channel_id"], "```diff\n+ Bot restarting...\n```")
            
            import subprocess
            import sys
            
            time.sleep(0.5)
            
            python = sys.executable
            subprocess.Popen([python, "main.py"])
            
            time.sleep(1)
            bot.stop()
        
        threading.Thread(target=restart_sequence, daemon=True).start()
        
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"), 5)

    @bot.command(name="vc", aliases=["voice", "joinvc"])
    def vc(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Voice ]\n> Usage: +vc <channel_id>\n> For servers: +vc 1234567890\n> For DMs/GCs: +vc <dm_channel_id>```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        channel_id = args[0]
        
        try:
            success = voice_manager.join_vc(channel_id)
            
            if success:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Voice ]\n> Connected to voice\n> ID: {channel_id}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Voice ]\n> Failed to connect\n> Check if ID is correct (must be VOICE channel)```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Voice ]\n> Error: {str(e)[:50]}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="vce", aliases=["leavevc", "disconnect"])
    def vce(ctx, args):
        try:
            if args:
                success = voice_manager.leave_vc(args[0])
            else:
                success = voice_manager.leave_vc()
            
            if success:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Voice ]\n> Disconnected from voice```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Voice ]\n> Not in a voice channel```")
            
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
                
        except Exception as e:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Voice ]\n> Error: {str(e)[:50]}```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="host")
    def host_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Host ]\n> +host <token>```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        token_input = " ".join(args)
        success, message = host_manager.host_token(ctx["author_id"], token_input)
        
        msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Host ]\n> {message}```")
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="stophost")
    def stophost_cmd(ctx, args):
        success, message = host_manager.stop_hosting(ctx["author_id"])
        msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Host ]\n> {message}```")
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="listhosted")
    def listhosted_cmd(ctx, args):
        hosted = host_manager.list_hosted(ctx["author_id"])
        if hosted:
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Host ]\n> Hosting {len(hosted)} tokens```")
        else:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Host ]\n> No tokens```")
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="backup", aliases=["save"])
    def backup_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], """```asciidoc
[ Backup Commands ]
backup user :: Backup user data, friends, guilds
backup messages <channel_id> [limit] :: Backup channel messages
backup full :: Create complete backup (zipped)
backup list :: List all backups
backup restore <filename> :: Restore from backup

Examples:
+backup user
+backup messages 1234567890 500
+backup list```""")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0] == "user":
            filename = backup_manager.backup_user_data()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup ]\n✓ User backup complete\nFile: {filename}```")
        
        elif args[0] == "messages" and len(args) >= 2:
            channel_id = args[1]
            limit = int(args[2]) if len(args) >= 3 else 1000
            filename = backup_manager.backup_messages(channel_id, limit)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup ]\n✓ Message backup complete\nFile: {filename}\nMessages: {limit}```")
        
        elif args[0] == "full":
            filename = backup_manager.create_full_backup()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup ]\n✓ Full backup complete\nFile: {filename}```")
        
        elif args[0] == "list":
            backups = backup_manager.list_backups()
            if backups:
                backup_list = "\n".join([f"• {b['name']} ({b['size']//1024}KB)" for b in backups[:10]])
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup List ]\n{backup_list}\n\nTotal: {len(backups)} backups```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Backup ]\nNo backups found```")
        
        elif args[0] == "restore" and len(args) >= 2:
            backup_name = args[1]
            success = backup_manager.restore_backup(backup_name)
            if success:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup ]\n✓ Restored from {backup_name}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Backup ]\n✗ Backup not found: {backup_name}```")
        
        if 'msg' in locals() and msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    @bot.command(name="mod", aliases=["moderation"])
    def mod_cmd(ctx, args):
        if not args:
            msg = ctx["api"].send_message(ctx["channel_id"], """```asciidoc
[ Moderation Commands ]
mod kick <user_id1,user_id2,...> :: Kick multiple users
mod ban <user_id1,user_id2,...> [delete_days] :: Ban users
mod filter add <word1,word2,...> :: Add word filter
mod filter check <text> :: Check text against filters
mod cleanup channels :: Delete all channels
mod cleanup roles :: Delete all roles
mod members [limit] :: List server members
mod channels :: List all channels
mod roles :: List all roles

Examples:
+mod kick 1111111111,2222222222
+mod ban 1111111111,2222222222 1
+mod filter add bad,word,here```""")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        guild_id = ctx["message"].get("guild_id")
        if not guild_id:
            msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Moderation ]\n✗ This command only works in servers```")
            if msg:
                delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0] == "kick" and len(args) >= 2:
            user_ids = args[1].split(',')
            count = mod_manager.mass_kick(guild_id, user_ids)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✓ Kicked {count}/{len(user_ids)} users```")
        
        elif args[0] == "ban" and len(args) >= 2:
            user_ids = args[1].split(',')
            delete_days = int(args[2]) if len(args) >= 3 else 0
            count = mod_manager.mass_ban(guild_id, user_ids, delete_days)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✓ Banned {count}/{len(user_ids)} users\nDelete days: {delete_days}```")
        
        elif args[0] == "filter":
            if len(args) >= 3 and args[1] == "add":
                words = args[2].split(',')
                count = mod_manager.create_word_filter(guild_id, words)
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✓ Added {count} words to filter```")
            elif len(args) >= 3 and args[1] == "check":
                text = " ".join(args[2:])
                match = mod_manager.check_message_filter(guild_id, text)
                if match:
                    msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✗ Filter matched: {match}```")
                else:
                    msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Moderation ]\n✓ No filter matches```")
        
        elif args[0] == "cleanup":
            if len(args) >= 2 and args[1] == "channels":
                channels = mod_manager.get_channels(guild_id)
                channel_ids = [c["id"] for c in channels]
                count = mod_manager.mass_delete_channels(guild_id, channel_ids)
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✓ Deleted {count}/{len(channel_ids)} channels```")
            elif len(args) >= 2 and args[1] == "roles":
                roles = mod_manager.get_roles(guild_id)
                role_ids = [r["id"] for r in roles if not r.get("managed", False) and r["name"] != "@everyone"]
                count = mod_manager.mass_delete_roles(guild_id, role_ids)
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\n✓ Deleted {count}/{len(role_ids)} roles```")
        
        elif args[0] == "members":
            limit = int(args[1]) if len(args) >= 2 else 100
            members = mod_manager.get_members(guild_id, limit)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\nMembers: {len(members)}/{limit}\nUse IDs for kick/ban commands```")
        
        elif args[0] == "channels":
            channels = mod_manager.get_channels(guild_id)
            channel_list = "\n".join([f"#{c['name']}: {c['id']}" for c in channels[:15]])
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\nChannels: {len(channels)}\n{channel_list}\n{'...' if len(channels) > 15 else ''}```")
        
        elif args[0] == "roles":
            roles = mod_manager.get_roles(guild_id)
            role_list = "\n".join([f"@{r['name']}: {r['id']}" for r in roles[:15]])
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Moderation ]\nRoles: {len(roles)}\n{role_list}\n{'...' if len(roles) > 15 else ''}```")
        
        if 'msg' in locals() and msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))

    @bot.command(name="web", aliases=["panel"])
    def web_cmd(ctx, args):
        msg = ctx["api"].send_message(ctx["channel_id"], """```asciidoc
[ Web Panel ]
Web interface started at:
http://127.0.0.1:8080

Features:
• Execute commands from browser
• View bot status
• Quick actions
• Command history

Note: Only accessible from your computer```""")
        if msg:
            delete_after_delay(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    original_run_command = bot.run_command
    def new_run_command(cmd_name, ctx, args):
        delete_command_message(ctx["api"], ctx["channel_id"], ctx["message"]["id"])
        original_run_command(cmd_name, ctx, args)
    
    bot.run_command = new_run_command
    
    def check_for_github_updates(message_data):
        return github_updater.check_message(message_data)
    
    original_process_message = bot._handle_message
    
    def new_process_message(message_data):
        if check_for_github_updates(message_data):
            return
        
        if anti_gc_trap.check_gc_creation(message_data):
            pass 
        
        author_id = message_data.get("author", {}).get("id")
        guild_id = message_data.get("guild_id")
        channel_id = message_data.get("channel_id")
        msg_id = message_data.get("id")
        
        if author_id in super_react.targets:
            super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, super_react.targets[author_id])
        
        if author_id in super_react.msr_targets:
            emojis, idx = super_react.msr_targets[author_id]
            emoji = emojis[idx]
            super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, emoji)
            super_react.msr_targets[author_id] = (emojis, (idx + 1) % len(emojis))
        
        if author_id in super_react.ssr_targets:
            for emoji in super_react.ssr_targets[author_id]:
                super_react.executor.submit(super_react._react_single, guild_id, channel_id, msg_id, emoji)
        
        content = message_data.get("content", "")
        prefix = bot.prefix
        
        if content.startswith(prefix):
            delete_command_message(bot.api, message_data.get("channel_id"), message_data.get("id"))
        
        if content:
            author_id = message_data.get("author", {}).get("id", "")
            
            if f"<@{bot.user_id}>" in content or f"<@!{bot.user_id}>" in content:
                if afk_system.is_afk(author_id):
                    afk_data = afk_system.get_afk_info(author_id)
                    afk_since = int(time.time() - afk_data["since"])
                    
                    hours = afk_since // 3600
                    minutes = (afk_since % 3600) // 60
                    
                    time_str = ""
                    if hours > 0:
                        time_str += f"{hours}h "
                    if minutes > 0 or hours == 0:
                        time_str += f"{minutes}m"
                    
                    channel_id = message_data.get("channel_id")
                    if channel_id:
                        bot.api.send_message(channel_id, f"```asciidoc\n[ AFK Notice ]\n> User <@{author_id}> is AFK\n> Reason: {afk_data['reason']}\n> Duration: {time_str}```")
        
        original_process_message(message_data)
    
    bot._handle_message = new_process_message
    
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
        print("\nBot stopped")

if __name__ == "__main__":

    main()






