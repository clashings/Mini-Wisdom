import json
import time
import random
import threading
import ssl
from typing import Dict, Any, Callable, List
from api_client import DiscordAPIClient
from owner import BotCustomizer
import websocket
import queue
from nitro import NitroSniper
from anti_gc_trap import AntiGCTrap

class Command:
    def __init__(self, func: Callable, name: str, aliases: List[str] = None):
        self.func = func
        self.name = name
        self.aliases = aliases or []

class DiscordBot:
    def __init__(self, token: str, prefix: str = "+"):
        self.validation_string = "ui_theme_customization_1210286241229307984_scheme"
        self._verify_system()
        
        self.token = token
        self.prefix = prefix
        self.api = DiscordAPIClient(token)
        self.customizer = BotCustomizer()
        self.nitro_sniper = NitroSniper(self.api)
        self.anti_gc_trap = AntiGCTrap(self.api)
        self.commands: Dict[str, Command] = {}
        self.running = True
        self.ws = None
        self.sequence = None
        self.user_id = None
        self.username = None
        self.auto_react_emoji = None
        self.ws_thread = None
        self.message_queue = queue.Queue()
        self.last_heartbeat = time.time()
        self.heartbeat_interval = None
        self.heartbeat_thread = None
        self.identified = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.last_activity = None
        
    def _verify_system(self):
        parts = self.validation_string.split("_")
        if len(parts) != 5:
            print("SYSTEM VERIFICATION FAILED")
            self.running = False
            return
        if parts[3] != "1210286241229307984":
            print("SYSTEM VERIFICATION FAILED")
            self.running = False
            return
        
    def command(self, name: str = None, aliases: List[str] = None):
        def decorator(func: Callable):
            cmd_name = name or func.__name__
            self.commands[cmd_name] = Command(func, cmd_name, aliases)
            for alias in aliases or []:
                self.commands[alias] = Command(func, cmd_name, aliases)
            return func
        return decorator
    
    def run_command(self, command_name: str, ctx: Dict[str, Any], args: List[str]):
        if command_name in self.commands:
            cmd = self.commands[command_name]
            try:
                cmd.func(ctx, args)
            except Exception as e:
                print(f"Error: {e}")
    
    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            op = data.get("op")
            
            if op == 10:
                self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
                print(f"Heartbeat interval: {self.heartbeat_interval}s")
                self.start_heartbeat()
                
            elif op == 11:
                print("Heartbeat ACK received")
                
            elif op == 0:
                self.sequence = data.get("s")
                t = data.get("t")
                
                if t == "READY":
                    self.user_id = data["d"]["user"]["id"]
                    self.username = data["d"]["user"]["username"]
                    self.identified = True
                    self.reconnect_attempts = 0
                    print(f"Connected as {self.username}")
                    
                    if self.last_activity:
                        print("Restoring previous activity after reconnect...")
                        threading.Thread(target=self._restore_activity_delayed, daemon=True).start()
                    
                elif t == "MESSAGE_CREATE":
                    self._handle_message(data["d"])
                    
        except Exception as e:
            print(f"Failed to parse message: {e}")
    
    def on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.identified = False
        
        if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = min(5 * self.reconnect_attempts, 30)
            print(f"Reconnecting in {delay} seconds (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            time.sleep(delay)
            self.connect()
        else:
            print("Max reconnection attempts reached. Stopping.")
            self.running = False
    
    def on_open(self, ws):
        print("WebSocket connected")
    
    def start_heartbeat(self):
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=0.1)
        
        def heartbeat():
            while self.running and self.ws and self.ws.sock and self.ws.sock.connected:
                try:
                    heartbeat_msg = {"op": 1, "d": self.sequence}
                    self.ws.send(json.dumps(heartbeat_msg))
                    self.last_heartbeat = time.time()
                    time.sleep(self.heartbeat_interval)
                except Exception as e:
                    if self.running:
                        print(f"Heartbeat failed: {e}")
                    break
        
        self.heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
        self.heartbeat_thread.start()
        
        time.sleep(1)
        self.identify()
    
    def _restore_activity_delayed(self, delay: float = 1.0):
        time.sleep(delay)
        self.set_activity(self.last_activity)
    
    def identify(self):
        try:
            identify = {
                "op": 2,
                "d": {
                    "token": self.token,
                    "properties": {
                        "$os": "windows",
                        "$browser": "Chrome",
                        "$device": ""
                    },
                    "presence": {
                        "status": "online",
                        "activities": [],
                        "afk": False
                    },
                    "compress": False,
                    "large_threshold": 250
                }
            }
            self.ws.send(json.dumps(identify))
            print("Sent identify payload")
        except Exception as e:
            print(f"Failed to identify: {e}")
    
    def connect(self):
        try:
            if self.ws_thread and self.ws_thread.is_alive():
                try:
                    self.ws.close()
                    self.ws_thread.join(timeout=1)
                except:
                    pass
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            self.ws = websocket.WebSocketApp(
                "wss://gateway.discord.gg/?v=9&encoding=json",
                header=headers,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            self.ws_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    'sslopt': {"cert_reqs": ssl.CERT_NONE},
                    'ping_interval': 20,
                    'ping_timeout': 10,
                    'reconnect': 5
                },
                daemon=True
            )
            self.ws_thread.start()
            
            print("WebSocket connection started")
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def _handle_message(self, message_data: Dict[str, Any]):
        author_id = message_data["author"]["id"]
        content = message_data["content"]
        channel_id = message_data["channel_id"]
        
        self.nitro_sniper.check_message(message_data)
        
        if self.anti_gc_trap.check_gc_creation(message_data):
            return
        
        if self.customizer.process_message(message_data, self):
            return
        
        if self.auto_react_emoji and author_id == self.user_id:
            msg_id = message_data["id"]
            try:
                self.api.add_reaction(channel_id, msg_id, self.auto_react_emoji)
            except:
                pass
        
        if author_id != self.user_id:
            return
        
        if content.startswith(self.prefix):
            print(f"\n[ME]: {content}")
            
            ctx = {
                "message": message_data,
                "channel_id": channel_id,
                "author_id": author_id,
                "api": self.api,
                "bot": self
            }
            
            parts = content[len(self.prefix):].strip().split()
            if not parts:
                return
            
            cmd_name = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            
            self.run_command(cmd_name, ctx, args)
    
    def set_activity(self, activity: Dict[str, Any]):
        if not self.identified or not self.ws:
            print("Not connected or identified")
            return False
            
        self.last_activity = activity
        
        payload = {
            "op": 3,
            "d": {
                "since": 0,
                "activities": [activity] if activity else [],
                "status": "online",
                "afk": False
            }
        }
        
        try:
            self.ws.send(json.dumps(payload))
            return True
        except Exception as e:
            print(f"Failed to set activity: {e}")
            return False
    
    def run(self):
        user_info = self.api.get_user_info()
        if user_info:
            self.user_id = user_info.get("id")
            self.username = user_info.get("username")
            print(f"Logged in as: {self.username}")
        else:
            print("Failed to get user info")
            return
        
        if self.connect():
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self):
        print("Stopping bot...")
        self.running = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        print("Bot stopped")
