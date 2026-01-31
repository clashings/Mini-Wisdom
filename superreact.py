import json
import time
import threading
import concurrent.futures
import random
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

    def encode_emoji(self, emoji):
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
        return encoded_emoji

    def send_super_reaction(self, channel_id, message_id, emoji):
        try:
            encoded_emoji = self.encode_emoji(emoji)
            
            headers = self.api.header_spoofer.get_headers()
            headers.update({
                "referer": f"https://discord.com/channels/@me/{channel_id}",
                "x-context-properties": "eyJsb2NhdGlvbiI6Ik1lc3NhZ2UgUmVhY3Rpb24gUGlja2VyIiwidHlwZSI6MX0="
            })
            
            params = {
                "location": "Message Reaction Picker",
                "type": "1",
                "burst": "1"
            }
            
            response = self.api.request("PUT", 
                f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
                params=params,
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
