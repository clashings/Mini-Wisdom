import json
import time

def setup_boost_commands(bot, api_client, delete_after_delay_func):
    from boost_manager import BoostManager
    boost_manager = BoostManager(api_client)
      
    
    @bot.command(name="boost")
    def boost_cmd(ctx, args):
        if not args:
            help_text = """```asciidoc
[ Boost Commands ]
boost <server_id> :: Boost a server
boost transfer <from_id> <to_id> :: Transfer boost
boost auto <server1,server2,...> :: Auto-boost from list
boost rotate <server1,server2,...> [hours] :: Auto-rotation
boost stop :: Stop rotation
boost status :: Check boost status
boost list :: List boosted servers```"""
            msg = ctx["api"].send_message(ctx["channel_id"], help_text)
            if msg:
                delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
            return
        
        if args[0] == "status":
            available = boost_manager.check_boost_status()
            boosted = len(boost_manager.boosted_servers)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost Status ]\n> Available: {available}\n> Boosted servers: {boosted}```")
        
        elif args[0] == "transfer" and len(args) >= 3:
            from_id = args[1]
            to_id = args[2]
            success, message = boost_manager.transfer_boost(from_id, to_id)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost ]\n> {message}```")
        
        elif args[0] == "auto" and len(args) >= 2:
            server_list = args[1].split(",")
            success, message = boost_manager.auto_boost_servers(server_list)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost ]\n> {message}```")
        
        elif args[0] == "rotate" and len(args) >= 2:
            server_list = args[1].split(",")
            hours = int(args[2]) if len(args) >= 3 else 24
            success, message = boost_manager.start_rotation(server_list, hours)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost ]\n> {message}```")
        
        elif args[0] == "stop":
            success, message = boost_manager.stop_rotation()
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost ]\n> {message}```")
        
        elif args[0] == "list":
            boosted = list(boost_manager.boosted_servers.keys())
            if boosted:
                boosted_list = "\n".join([f"• {server_id}" for server_id in boosted[:10]])
                if len(boosted) > 10:
                    boosted_list += f"\n• ... and {len(boosted) - 10} more"
                msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boosted Servers ]\n{boosted_list}```")
            else:
                msg = ctx["api"].send_message(ctx["channel_id"], "```asciidoc\n[ Boost ]\n> No boosted servers```")
        
        else:
            server_id = args[0]
            success, message = boost_manager.boost_server(server_id)
            msg = ctx["api"].send_message(ctx["channel_id"], f"```asciidoc\n[ Boost ]\n> {message}```")
        
          
        if msg:
            delete_after_delay_func(ctx["api"], ctx["channel_id"], msg.get("id"))
    
    original_stop = bot.stop
    def new_stop():
          
        original_stop()
    bot.stop = new_stop

