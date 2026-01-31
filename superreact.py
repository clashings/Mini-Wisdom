import json
import time
import threading
import concurrent.futures
import random
import asyncio
import re
from urllib.parse import quote as url_quote

class SuperReact:
    def __init__(self, bot):
        self.bot = bot
        self.token = bot.token
        self.api = bot.api
        self.USER_ID = bot.user_id
        self.targets = {}
        self.msr_targets = {}
        self.ssr_targets = {}
        self.emojis = ['👍', '👎', '😂', '❤️', '😍', '🔥', '😭', '🤔', '😎', '🥰', '🤯', '😢', '🙌', '👏', '💯', '⭐', '🎉', '🚀', '💥', '🌟']
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="SuperReact")
        print(f"[SUCCESS]: SuperReact initialized.")

    def send_super_reaction(self, channel_id, message_id, emoji):
        try:
            if emoji.startswith("<a:") or emoji.startswith("<:"):
                emoji_cleaned = emoji.replace('<', '').replace('>', '')
                parts = emoji_cleaned.split(':')
                if len(parts) >= 2:
                    emoji_name = parts[1]
                    emoji_id = parts[2] if len(parts) > 2 else parts[1]
                    encoded_emoji = f"{emoji_name}:{emoji_id}"
                else:
                    encoded_emoji = url_quote(emoji)
            else:
                encoded_emoji = url_quote(emoji)
            
            headers = self.api.header_spoofer.get_headers()
            headers.update({
                "referer": f"https://discord.com/channels/@me/{channel_id}",
                "x-context-properties": "eyJsb2NhdGlvbiI6Ik1lc3NhZ2UgUmVhY3Rpb24gUGlja2VyIiwidHlwZSI6MX0="
            })
            
            response = self.api.request("PUT", 
                f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
                params={"location": "Message Reaction Picker", "type": 1},
                headers=headers
            )
            
            if response and response.status_code == 204:
                return True
            return False
        except Exception as e:
            print(f"[ERROR]: Failed to send super reaction: {e}")
            return False

    def _react_single(self, guild_id, channel_id, msg_id, emoji):
        try:
            self.send_super_reaction(channel_id, msg_id, emoji)
        except Exception as e:
            print(f"[ERROR]: Failed to react to msg {msg_id}: {e}")

    def parse_target_id(self, target_arg):
        if target_arg == "@me":
            return self.USER_ID
        cleaned = target_arg.strip('<@!>').replace('&', '')
        return cleaned if cleaned.isdigit() else None

    def handle_message(self, message_data):
        author_id = message_data.get("author", {}).get("id")
        content = message_data.get("content", "")
        guild_id = message_data.get("guild_id")
        channel_id = message_data.get("channel_id")
        msg_id = message_data.get("id")
        
        if not author_id or not content:
            return
        
        if author_id == self.USER_ID:
            if content.startswith("+superreact ") or content.startswith("+sr "):
                parts = content.split(" ", 2)
                if len(parts) < 3:
                    return
                target_arg, emoji = parts[1], parts[2]
                target_id = self.parse_target_id(target_arg)
                if target_id:
                    self.targets[target_id] = emoji
                    self.api.send_message(channel_id, f"```asciidoc\n= Enabled Super-Reaction =\nUser: <@{target_id}>\nEmoji: {emoji}```")
            
            elif content.startswith("+superreactstop ") or content.startswith("+srstop "):
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    return
                target_id = self.parse_target_id(parts[1])
                if target_id in self.targets:
                    emoji = self.targets[target_id]
                    del self.targets[target_id]
                    self.api.send_message(channel_id, f"```asciidoc\n= Stopped Super-Reaction =\nUser: <@{target_id}>\nEmoji: {emoji}```")
            
            elif content.startswith("+cyclesuperreact ") or content.startswith("+csr "):
                parts = content.split(" ", 2)
                if len(parts) < 3:
                    return
                target_id = self.parse_target_id(parts[1])
                emojis = [e.strip() for e in parts[2].split(",") if e.strip()]
                if target_id and emojis:
                    self.msr_targets[target_id] = (emojis, 0)
                    self.api.send_message(channel_id, f"```asciidoc\n= Enabled Cycle-SuperReaction =\nUser: <@{target_id}>\nEmojis: {', '.join(emojis)}```")
            
            elif content.startswith("+cyclesuperreactstop ") or content.startswith("+csrstop "):
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    return
                target_id = self.parse_target_id(parts[1])
                if target_id in self.msr_targets:
                    emojis, _ = self.msr_targets[target_id]
                    del self.msr_targets[target_id]
                    self.api.send_message(channel_id, f"```asciidoc\n= Stopped Cycle-SuperReaction =\nUser: <@{target_id}>\nEmojis: {', '.join(emojis)}```")
            
            elif content.startswith("+multisuperreact ") or content.startswith("+msr "):
                parts = content.split(" ", 2)
                if len(parts) < 3:
                    return
                target_id = self.parse_target_id(parts[1])
                emojis = [e.strip() for e in parts[2].split(",") if e.strip()]
                if target_id and emojis:
                    self.ssr_targets[target_id] = emojis
                    self.api.send_message(channel_id, f"```asciidoc\n= Enabled Multi-SuperReaction =\nUser: <@{target_id}>\nEmojis: {', '.join(emojis)}```")
            
            elif content.startswith("+multisuperreactstop ") or content.startswith("+msrstop "):
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    return
                target_id = self.parse_target_id(parts[1])
                if target_id in self.ssr_targets:
                    emojis = self.ssr_targets[target_id]
                    del self.ssr_targets[target_id]
                    self.api.send_message(channel_id, f"```asciidoc\n= Stopped Multi-SuperReaction =\nUser: <@{target_id}>\nEmojis: {', '.join(emojis)}```")
            
            elif content.startswith("+random "):
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    self.api.send_message(channel_id, f"```asciidoc\n[Error]\nUsage: +random <message_id>```")
                    return
                target_msg_id = parts[1].strip()
                if not target_msg_id.isdigit():
                    self.api.send_message(channel_id, f"```asciidoc\n[Error]\nInvalid message ID```")
                    return
                self.api.send_message(channel_id, f"```asciidoc\n[SuperReact]\nAdding random super-reactions to message {target_msg_id}...```")
                added_emojis = []
                available_emojis = self.emojis.copy()
                while len(added_emojis) < 20 and available_emojis:
                    emoji = random.choice(available_emojis)
                    available_emojis.remove(emoji)
                    try:
                        self.send_super_reaction(channel_id, target_msg_id, emoji)
                        added_emojis.append(emoji)
                        time.sleep(0.5)
                    except Exception as e:
                        print(f"[ERROR]: Failed to add {emoji} to {target_msg_id}: {e}")
                        break
                self.api.send_message(channel_id, f"```asciidoc\n[SuperReact Complete]\nMessage: {target_msg_id}\nAdded: {', '.join(added_emojis)}\nTotal: {len(added_emojis)}```")
        
        if author_id in self.targets:
            self.executor.submit(self._react_single, guild_id, channel_id, msg_id, self.targets[author_id])
        
        if author_id in self.msr_targets:
            emojis, idx = self.msr_targets[author_id]
            emoji = emojis[idx]
            self.executor.submit(self._react_single, guild_id, channel_id, msg_id, emoji)
            self.msr_targets[author_id] = (emojis, (idx + 1) % len(emojis))
        
        if author_id in self.ssr_targets:
            for emoji in self.ssr_targets[author_id]:
                self.executor.submit(self._react_single, guild_id, channel_id, msg_id, emoji)
