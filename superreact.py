import json
import time
import threading
import concurrent.futures
import tls_client
import random
import re
from urllib.parse import quote as url_quote

class SuperReact:
    def __init__(self, bot):
        self.bot = bot
        self.token = bot.token
        self.api = bot.api
        self.USER_ID = bot.user_id
        self.FINGERPRINT = None
        self.COOKIES = ""
        self.targets = {}
        self.msr_targets = {}
        self.ssr_targets = {}
        self.emojis = ['👍', '👎', '😂', '❤️', '😍', '🔥', '😭', '🤔', '😎', '🥰', '🤯', '😢', '🙌', '👏', '💯', '⭐', '🎉', '🚀', '💥', '🌟']
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix="SuperReact")
        self.init()

    def init(self):
        try:
            response = self.api.request("GET", "/experiments")
            if response and response.status_code == 200:
                self.FINGERPRINT = response.json().get("fingerprint", "")
                print(f"[SUCCESS]: Fingerprint acquired.")
                return True
        except Exception as e:
            print(f"[ERROR]: Couldnt get fingerprint, {e}.")
            return False

    def sp(self):
        p = {
            "os": "Windows", "browser": "Chrome", "device": "", "system_locale": "en-US",
            "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "browser_version": "138.0.0.0", "os_version": "10", "referrer": "", "referring_domain": "",
            "release_channel": "stable", "client_build_number": 429117, "client_event_source": None
        }
        return base64.b64encode(json.dumps(p).encode()).decode()

    def hdr(self):
        headers = self.api.header_spoofer.get_headers()
        headers.update({
            "x-context-properties": "eyJsb2NhdGlvbiI6Ik1lc3NhZ2UgUmVhY3Rpb24gUGlja2VyIiwidHlwZSI6MX0=",
            "x-super-properties": self.sp(),
            "x-fingerprint": self.FINGERPRINT if self.FINGERPRINT else ""
        })
        return headers

    def send_super_reaction_rest(self, guild_id, channel_id, message_id, emoji):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                is_custom = emoji.startswith("<a:") or emoji.startswith("<:")
                path = (f"{emoji.replace('<','').replace('>','').split(':')[1]}:{emoji.replace('<','').replace('>','').split(':')[2]}" if is_custom else url_quote(emoji))
                g_id = guild_id or "@me"
                headers = self.hdr()
                headers.update({"referer": f"https://discord.com/channels/{g_id}/{channel_id}"})
                url = f"https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}/reactions/{path}/@me"
                params = {"location": "Message Reaction Picker", "type": 1, "burst": 1}
                
                response = self.api.request("PUT", 
                    f"/channels/{channel_id}/messages/{message_id}/reactions/{path}/@me",
                    params=params,
                    headers=headers
                )
                
                if response and response.status_code == 429:
                    retry_after = float(response.headers.get('Retry-After', 1))
                    print(f"[RATE LIMIT]: Waiting {retry_after}s for reaction.")
                    time.sleep(retry_after)
                    continue
                elif response and response.status_code >= 500:
                    wait = (2 ** attempt) + (0.1 * attempt)
                    print(f"[SERVER ERROR]: Retry {attempt+1}/{max_retries} after {wait:.1f}s.")
                    time.sleep(wait)
                    continue
                
                if response and response.status_code == 204:
                    print(f"[SUCCESS]: Super reaction succeeded.")
                    return True
                
                print(f"[ERROR]: Unexpected status {response.status_code if response else 'No response'}")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                print(f"[ERROR]: Failed after retries: {e}")
        return False

    def _react_single(self, guild_id, channel_id, msg_id, emoji):
        try:
            self.send_super_reaction_rest(guild_id, channel_id, msg_id, emoji)
        except Exception as e:
            print(f"[ERROR]: Failed to react to msg {msg_id}: {e}")

    def parse_target_id(self, target_arg):
        if target_arg == "@me":
            return self.USER_ID
        cleaned = target_arg.strip('<@!>').replace('&', '')
        return cleaned if cleaned.isdigit() else None
