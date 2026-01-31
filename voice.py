import json
import asyncio
import websockets
import time
import threading

class VoiceClient:
    def __init__(self, api_client, token):
        self.api = api_client
        self.token = token
        self.voice_ws = None
        self.gateway_ws = None
        self.voice_thread = None
        self.gateway_thread = None
        self.running = False
        self.gateway_running = False
        self.voice_gateway_url = None
        self.session_id = None
        self.token_v = None
        self.endpoint = None
        self.guild_id = None
        self.channel_id = None
        self.user_id = None
        self.sequence = 0
        self.heartbeat_interval = None
        self.ssrc = None
        self.secret_key = None
        self.speaking = False
        self.is_dm_call = False
        self.call_channel_id = None
        self.voice_data_received = False
    
    def connect_to_voice(self, target_id):
        self.channel_id = target_id
        
        try:
            channel_info = self.api.request("GET", f"/channels/{target_id}")
            if channel_info and channel_info.status_code == 200:
                data = channel_info.json()
                channel_type = data.get('type', 0)
                
                print(f"DEBUG: Checking channel {target_id}")
                print(f"DEBUG: Channel type = {channel_type}")
                print(f"DEBUG: Channel name = {data.get('name')}")
                
                if channel_type == 2:
                    self.is_dm_call = False
                    self.guild_id = data.get('guild_id')
                    print(f"Voice channel: {data.get('name')}")
                    return self._connect_to_guild_voice(target_id)
                elif channel_type in [1, 3]:
                    self.is_dm_call = True
                    self.guild_id = None
                    self.call_channel_id = target_id
                    print(f"DM/Group channel")
                    return self._connect_to_dm_voice(target_id)
                else:
                    print(f"ERROR: Channel {target_id} is type {channel_type}, not voice")
                    print(f"0=text, 2=voice, 1=DM, 3=group")
                    print(f"Name: {data.get('name')}")
                    return False
            else:
                print(f"Could not fetch channel {target_id}")
                return False
        except Exception as e:
            print(f"Channel detection error: {e}")
            return False
    
    def _connect_to_guild_voice(self, channel_id):
        if not self.guild_id:
            self.guild_id = self._find_guild_for_channel(channel_id)
            if not self.guild_id:
                print(f"Could not find guild for channel {channel_id}")
                return False
        
        print(f"Joining voice channel {channel_id} in guild {self.guild_id}")
        
        if hasattr(self.api, 'user_id'):
            self.user_id = self.api.user_id
        
        try:
            response = self.api.request("PATCH", f"/guilds/{self.guild_id}/voice-states/@me", data={
                "channel_id": str(channel_id),
                "self_mute": False,
                "self_deaf": False
            })
            
            if response and response.status_code == 200:
                print(f"Voice state updated successfully")
                
                response_data = response.json()
                self.session_id = response_data.get('session_id')
                self.token_v = response_data.get('token')
                
                self.voice_thread = threading.Thread(target=self._voice_connect_thread, daemon=True)
                self.voice_thread.start()
                
                for i in range(15):
                    if self.endpoint:
                        break
                    time.sleep(1)
                
                if self.endpoint:
                    print(f"Voice gateway endpoint received")
                    return True
                else:
                    print(f"No endpoint received after waiting")
                    return False
            else:
                print(f"Voice state update failed: {response.status_code if response else 'No response'}")
                if response:
                    try:
                        error_data = response.json()
                        print(f"Error: {error_data}")
                    except:
                        print(f"Raw error: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"Voice join error: {e}")
            return False
    
    def _connect_to_dm_voice(self, channel_id):
        self.call_channel_id = channel_id
        self.is_dm_call = True
        self.guild_id = None
        
        print(f"Starting DM call in channel {channel_id}")
        
        self.gateway_thread = threading.Thread(target=self._gateway_connect_thread, daemon=True)
        self.gateway_thread.start()
        
        time.sleep(2)
        return True
    
    def _find_guild_for_channel(self, channel_id):
        try:
            channel_info = self.api.request("GET", f"/channels/{channel_id}")
            if channel_info and channel_info.status_code == 200:
                data = channel_info.json()
                return data.get('guild_id')
        except:
            pass
        return None
    
    def _voice_connect_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_voice_gateway())
    
    def _gateway_connect_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect_main_gateway())
    
    async def _connect_main_gateway(self):
        self.gateway_running = True
        
        try:
            ws_url = "wss://gateway.discord.gg/?v=10&encoding=json"
            
            ws = await websockets.connect(
                ws_url,
                max_size=None,
                ping_interval=30,
                ping_timeout=30
            )
            
            self.gateway_ws = ws
            
            await self._identify_gateway(ws)
            
            async for message in ws:
                await self._handle_gateway_message(ws, message)
                
        except Exception as e:
            print(f"Gateway error: {e}")
        finally:
            self.gateway_running = False
            if self.gateway_ws:
                await self.gateway_ws.close()
    
    async def _identify_gateway(self, ws):
        identify = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": "windows",
                    "$browser": "Chrome",
                    "$device": "desktop"
                },
                "presence": {
                    "status": "online",
                    "activities": [],
                    "afk": False
                },
                "compress": False,
                "large_threshold": 250,
                "intents": 32509
            }
        }
        await ws.send(json.dumps(identify))
    
    async def _start_call(self, ws):
        if not self.call_channel_id:
            return
        
        call_data = {
            "op": 4,
            "d": {
                "guild_id": None,
                "channel_id": str(self.call_channel_id),
                "self_mute": False,
                "self_deaf": False,
                "self_video": False
            }
        }
        await ws.send(json.dumps(call_data))
    
    async def _handle_gateway_message(self, ws, message):
        try:
            data = json.loads(message)
            op = data.get("op")
            t = data.get("t")
            
            if op == 10:
                self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000
                asyncio.create_task(self._gateway_heartbeat(ws))
            
            elif op == 0:
                if t == "READY":
                    if self.is_dm_call:
                        await self._start_call(ws)
                
                elif t == "VOICE_STATE_UPDATE":
                    voice_data = data["d"]
                    if voice_data.get("user_id") == str(self.user_id):
                        self.session_id = voice_data.get("session_id")
                        self.token_v = voice_data.get("token")
                        print(f"DEBUG: Got session_id from gateway")
                
                elif t == "VOICE_SERVER_UPDATE":
                    server_data = data["d"]
                    guild_id_match = str(server_data.get("guild_id")) == str(self.guild_id)
                    
                    if guild_id_match or self.is_dm_call:
                        self.endpoint = server_data.get("endpoint")
                        self.token_v = server_data.get("token")
                        if self.endpoint:
                            self.endpoint = self.endpoint.replace(':443', '')
                            print(f"DEBUG: Got endpoint: {self.endpoint}")
                            self.voice_data_received = True
            
        except Exception as e:
            print(f"Gateway message error: {e}")
    
    async def _gateway_heartbeat(self, ws):
        while self.gateway_running:
            try:
                heartbeat_msg = {"op": 1, "d": self.sequence}
                await ws.send(json.dumps(heartbeat_msg))
                self.sequence += 1
                await asyncio.sleep(self.heartbeat_interval)
            except:
                break
    
    async def _connect_voice_gateway(self):
        for i in range(20):
            if self.endpoint and self.token_v and self.session_id:
                break
            time.sleep(1)
        
        if not self.endpoint or not self.token_v or not self.session_id:
            print(f"DEBUG: Missing voice data - endpoint:{self.endpoint}, token:{self.token_v}, session:{self.session_id}")
            return
        
        print(f"Connecting to voice gateway: {self.endpoint}")
        
        try:
            ws = await websockets.connect(
                f"wss://{self.endpoint}/?v=4",
                max_size=None,
                ping_interval=30,
                ping_timeout=30
            )
            self.voice_ws = ws
            self.running = True
            
            await self._voice_identify(ws)
            
            async for message in ws:
                await self._handle_voice_message(ws, message)
                
        except Exception as e:
            print(f"Voice gateway error: {e}")
        finally:
            self.running = False
            if self.voice_ws:
                await self.voice_ws.close()
    
    async def _voice_identify(self, ws):
        server_id = str(self.guild_id) if self.guild_id else None
        identify = {
            "op": 0,
            "d": {
                "server_id": server_id,
                "user_id": str(self.user_id),
                "session_id": self.session_id,
                "token": self.token_v
            }
        }
        await ws.send(json.dumps(identify))
        print(f"DEBUG: Sent voice identify")
    
    async def _handle_voice_message(self, ws, message):
        try:
            data = json.loads(message)
            op = data.get('op')
            
            if op == 2:
                self.ssrc = data['d']['ssrc']
                self.secret_key = data['d']['secret_key']
                self.heartbeat_interval = data['d']['heartbeat_interval'] / 1000
                
                print(f"VOICE CONNECTED SUCCESSFULLY!")
                print(f"SSRC: {self.ssrc}")
                asyncio.create_task(self._voice_heartbeat(ws))
                await self._select_protocol(ws)
                
            elif op == 4:
                await self._speaking(ws, True)
                
            elif op == 8:
                self.heartbeat_interval = data['d']['heartbeat_interval'] / 1000
                
        except Exception as e:
            print(f"Voice message error: {e}")
    
    async def _voice_heartbeat(self, ws):
        while self.running:
            try:
                heartbeat_msg = {"op": 3, "d": None}
                await ws.send(json.dumps(heartbeat_msg))
                await asyncio.sleep(self.heartbeat_interval)
            except:
                break
    
    async def _select_protocol(self, ws):
        select_protocol = {
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": "127.0.0.1",
                    "port": 0,
                    "mode": "xsalsa20_poly1305"
                }
            }
        }
        await ws.send(json.dumps(select_protocol))
    
    async def _speaking(self, ws, speaking):
        speaking_msg = {
            "op": 5,
            "d": {
                "speaking": 1 if speaking else 0,
                "delay": 0,
                "ssrc": self.ssrc
            }
        }
        await ws.send(json.dumps(speaking_msg))
        self.speaking = speaking
    
    def disconnect(self):
        self.running = False
        self.gateway_running = False
        
        if self.guild_id and not self.is_dm_call:
            try:
                self.api.request("PATCH", f"/guilds/{self.guild_id}/voice-states/@me", data={
                    "channel_id": None
                })
                print(f"Left voice channel")
            except:
                pass

class SimpleVoice:
    def __init__(self, api_client, token):
        self.api = api_client
        self.token = token
        self.active_connections = {}
    
    def join_vc(self, *args, **kwargs):
        if args and isinstance(args[0], str) and args[0].isdigit():
            channel_id = args[0]
        elif kwargs.get('channel_id'):
            channel_id = kwargs['channel_id']
        else:
            print("ERROR: No channel ID provided to join_vc()")
            return False
        
        print(f"=== JOIN_VC CALLED ===")
        print(f"Channel ID passed: {channel_id}")
        
        connection_key = f"channel_{channel_id}"
        
        if connection_key in self.active_connections:
            self.leave_vc(channel_id)
        
        print(f"Creating VoiceClient for channel {channel_id}")
        voice_client = VoiceClient(self.api, self.token)
        success = voice_client.connect_to_voice(channel_id)
        
        if success:
            self.active_connections[connection_key] = voice_client
            time.sleep(3)
            print(f"Voice connection successful for {channel_id}")
            return True
        
        print(f"Voice connection failed for {channel_id}")
        return False
    
    def leave_vc(self, *args, **kwargs):
        if args and isinstance(args[0], str) and args[0].isdigit():
            channel_id = args[0]
        elif kwargs.get('channel_id'):
            channel_id = kwargs['channel_id']
        else:
            channel_id = None
        
        if channel_id:
            connection_key = f"channel_{channel_id}"
            if connection_key in self.active_connections:
                print(f"Disconnecting from {connection_key}")
                success = self.active_connections[connection_key].disconnect()
                del self.active_connections[connection_key]
                return success
        else:
            success = True
            for key, client in list(self.active_connections.items()):
                print(f"Disconnecting from {key}")
                if not client.disconnect():
                    success = False
                del self.active_connections[key]
            return success
        return False
    
    def is_in_voice(self, *args, **kwargs):
        if args and isinstance(args[0], str) and args[0].isdigit():
            channel_id = args[0]
        elif kwargs.get('channel_id'):
            channel_id = kwargs['channel_id']
        else:
            channel_id = None
        
        if channel_id:
            connection_key = f"channel_{channel_id}"
            return connection_key in self.active_connections
        return len(self.active_connections) > 0
