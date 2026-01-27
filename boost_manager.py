import json
import time
import threading
from datetime import datetime, timedelta

class BoostManager:
    def __init__(self, api_client):
        self.api = api_client
        self.boosted_servers = {}
        self.available_boosts = 2
        self.last_check = 0
        self.boost_thread = None
        self.running = False
        self.rotation_servers = []
        self.rotation_hours = 24
        self.rotation_thread = None
        
    def load_state(self):
        try:
            with open('boost_state.json', 'r') as f:
                data = json.load(f)
                self.boosted_servers = data.get('boosted_servers', {})
                self.available_boosts = data.get('available_boosts', 2)
                self.rotation_servers = data.get('rotation_servers', [])
                self.rotation_hours = data.get('rotation_hours', 24)
        except FileNotFoundError:
            self.boosted_servers = {}
            self.available_boosts = 2
            self.rotation_servers = []
            self.rotation_hours = 24
        except Exception:
            self.boosted_servers = {}
            self.available_boosts = 2
            self.rotation_servers = []
            self.rotation_hours = 24
    
    def save_state(self):
        try:
            data = {
                'boosted_servers': self.boosted_servers,
                'available_boosts': self.available_boosts,
                'rotation_servers': self.rotation_servers,
                'rotation_hours': self.rotation_hours,
                'last_saved': time.time()
            }
            with open('boost_state.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
    
    def check_boost_status(self):
        try:
            response = self.api.request("GET", "/users/@me/guilds/premium/subscription-slots")
            if response and response.status_code == 200:
                slots = response.json()
                available = sum(1 for slot in slots if slot.get("cooldown_ends_at") is None)
                self.available_boosts = available
                return available
        except:
            pass
        return 0
    
    def can_boost(self, server_id):
        current_time = time.time()
        if current_time - self.last_check > 300:
            self.check_boost_status()
            self.last_check = current_time
        
        return self.available_boosts > 0
    
    def boost_server(self, server_id):
        if not self.can_boost(server_id):
            return False, "No boosts available"
        
        try:
            headers = self.api.header_spoofer.get_headers()
            data = {"user_premium_guild_subscription_slot_ids": ["1"]}
            
            response = self.api.session.put(
                f"https://discord.com/api/v9/guilds/{server_id}/premium/subscriptions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response and response.status_code == 200:
                self.boosted_servers[server_id] = time.time()
                self.available_boosts -= 1
                self.save_state()
                return True, f"Boosted server {server_id}"
            elif response and response.status_code == 403:
                return False, "No permission to boost"
            elif response and response.status_code == 404:
                return False, "Server not found"
            else:
                return False, f"Failed: {response.status_code if response else 'No response'}"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"
    
    def transfer_boost(self, from_server_id, to_server_id):
        try:
            headers = self.api.header_spoofer.get_headers()
            response = self.api.session.delete(
                f"https://discord.com/api/v9/guilds/{from_server_id}/premium/subscriptions",
                headers=headers,
                timeout=10
            )
            
            if response and response.status_code in [200, 204]:
                time.sleep(1)
                success, message = self.boost_server(to_server_id)
                if success:
                    if from_server_id in self.boosted_servers:
                        del self.boosted_servers[from_server_id]
                    self.save_state()
                    return True, f"Transferred boost from {from_server_id} to {to_server_id}"
        except Exception as e:
            return False, f"Transfer error: {str(e)[:50]}"
        
        return False, "Transfer failed"
    
    def auto_boost_servers(self, server_list):
        if not server_list:
            return False, "No servers provided"
        
        boosted_count = 0
        for server_id in server_list:
            if self.can_boost(server_id):
                success, message = self.boost_server(server_id)
                if success:
                    boosted_count += 1
                else:
                    return False, f"Failed to boost {server_id}: {message}"
            else:
                return False, "No boosts available"
        
        self.save_state()
        return True, f"Successfully boosted {boosted_count} server(s)"
    
    def start_rotation(self, server_list, hours=24):
        if not server_list or len(server_list) < 2:
            return False, "Need at least 2 servers for rotation"
        
        if self.rotation_thread and self.running:
            return False, "Rotation already running"
        
        self.rotation_servers = server_list
        self.rotation_hours = hours
        self.running = True
        
        self.rotation_thread = threading.Thread(target=self._rotation_worker, daemon=True)
        self.rotation_thread.start()
        
        self.save_state()
        return True, f"Started rotation for {len(server_list)} servers (every {hours} hours)"
    
    def _rotation_worker(self):
        while self.running:
            try:
                for server_id in self.rotation_servers:
                    if not self.running:
                        break
                    
                    if server_id in self.boosted_servers:
                        headers = self.api.header_spoofer.get_headers()
                        self.api.session.delete(
                            f"https://discord.com/api/v9/guilds/{server_id}/premium/subscriptions",
                            headers=headers,
                            timeout=10
                        )
                        if server_id in self.boosted_servers:
                            del self.boosted_servers[server_id]
                        time.sleep(2)
                    
                    success, _ = self.boost_server(server_id)
                    if success:
                        pass
                    
                    for _ in range(self.rotation_hours * 3600 // 10):
                        if not self.running:
                            break
                        time.sleep(10)
                    
            except Exception:
                time.sleep(60)
    
    def stop_rotation(self):
        if not self.running:
            return False, "No rotation running"
        
        self.running = False
        self.rotation_servers = []
        
        if self.rotation_thread:
            self.rotation_thread.join(timeout=5)
            self.rotation_thread = None
        
        self.save_state()
        return True, "Stopped boost rotation"
    
    def get_boosted_servers(self):
        return list(self.boosted_servers.keys())
    
    def clear_expired_boosts(self):
        current_time = time.time()
        expired = []
        
        for server_id, boost_time in list(self.boosted_servers.items()):
            if current_time - boost_time > 30 * 24 * 3600:
                expired.append(server_id)
        
        for server_id in expired:
            del self.boosted_servers[server_id]
        
        if expired:
            self.save_state()
        
        return len(expired)
