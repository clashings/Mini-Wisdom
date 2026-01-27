import json
import time
import threading

class BoostManager:
    def __init__(self, api_client):
        self.api = api_client
        self.boosted_servers = {}
        self.available_boosts = 2
        self.last_check = 0
        self.boost_thread = None
        self.running = False
        
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
            data = {"user_premium_guild_subscription_slot_ids": ["1"]}  # Use first slot
            
            response = self.api.session.put(
                f"https://discord.com/api/v9/guilds/{server_id}/premium/subscriptions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response and response.status_code == 200:
                self.boosted_servers[server_id] = time.time()
                self.available_boosts -= 1
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
                    return True, f"Transferred boost from {from_server_id} to {to_server_id}"
        except Exception as e:
            return False, f"Transfer error: {str(e)[:50]}"
        
        return False, "Transfer failed"
