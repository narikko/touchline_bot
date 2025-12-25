import discord
from src.database.models import User, GlobalTutorial
from src.services.gacha_service import GachaService

class TutorialService:
    def __init__(self, session):
        self.session = session
        
        # DEFINITION OF ALL TUTORIALS
        self.TUTORIALS = [
            # TUTORIAL 1: BASICS
            {
                "title": "Tutorial 1: The Basics",
                "description": "Welcome to Touchline! Let's get you started with your first player.",
                "reward_text": "1 Free Claim Ticket",
                "steps": {
                    "1_roll": "Roll for a player (`/r`)",
                    "1_claim": "Claim a player card"
                },
                "reward": {"type": "free_claim", "amount": 1}
            },
            # TUTORIAL 2: PROFILE
            {
                "title": "Tutorial 2: Your Profile",
                "description": "Learn how to manage your account settings.",
                "reward_text": "250 Coins",
                "steps": {
                    "2_profile": "View your profile (`/profile`)",
                    "2_setclub": "Set your favorite club (`/setclub`)",
                    "2_daily": "Claim your daily reward (`/daily`)"
                },
                "reward": {"type": "coins", "amount": 250}
            },
            # TUTORIAL 3: COLLECTION
            {
                "title": "Tutorial 3: Collection Management",
                "description": "Manage your growing list of players.",
                "reward_text": "+1 Max Rolls (Permanent)",
                "steps": {
                    "3_view": "View your collection (`/collection`)",
                    "3_sort": "Sort your collection (`/sort`)",
                    "3_move": "Move a player (`/move`)",
                    "3_sell": "Sell a player (`/sell`)",
                    "3_view_other": "View another user's collection"
                },
                "reward": {"type": "max_rolls", "amount": 1}
            },
            # TUTORIAL 4: SCOUTING
            {
                "title": "Tutorial 4: Scouting & Shortlist",
                "description": "Learn how to find specific players and track them.",
                "reward_text": "500 Coins",
                "steps": {
                    "4_view": "View a specific player (`/view`)",
                    "4_listclub": "List players from a club (`/listclub`)",
                    "4_shortlist": "Add a player to Shortlist (`/shortlist add`)"
                },
                "reward": {"type": "coins", "amount": 500}
            },
            # TUTORIAL 5: TEAM BUILDING
            {
                "title": "Tutorial 5: Team Building",
                "description": "Create your dream Starting XI.",
                "reward_text": "500 Coins",
                "steps": {
                    "5_view_team": "View your team (`/team view`)",
                    "5_set": "Set a player (`/team set`)",
                    "5_bench": "Bench a player (`/team bench`)",
                    "5_rewards": "View team rewards (`/team rewards`)",
                    "5_rename": "Rename your club (`/team rename`)"
                },
                "reward": {"type": "coins", "amount": 500}
            },
            # TUTORIAL 6: UPGRADES
            {
                "title": "Tutorial 6: Club Upgrades",
                "description": "Invest in your club's infrastructure.",
                "reward_text": "1 Free Claim Ticket",
                "steps": {
                    "6_info": "View upgrades info (`/upgrades info`)",
                    "6_buy": "Buy any upgrade (Stadium, Board, etc.)"
                },
                "reward": {"type": "free_claim", "amount": 1}
            },
            # TUTORIAL 7: MARKET
            {
                "title": "Tutorial 7: The Market",
                "description": "Trade and sell players for profit.",
                "reward_text": "750 Coins",
                "steps": {
                    "7_trade": "Complete a trade (`/trade`)",
                    "7_tm_add": "List a player on Transfer Market (`/tm add`)",
                    "7_tm_sold": "Successfully sell a player (Wait time)"
                },
                "reward": {"type": "coins", "amount": 750}
            },
            # TUTORIAL 8: MATCH DAY
            {
                "title": "Tutorial 8: Match Day",
                "description": "Test your team against other players to win their coins!",
                "reward_text": "1000 Coins",
                "steps": {
                    "8_match": "Play a match (`/match`)"
                },
                "reward": {"type": "coins", "amount": 1000}
            }
        ]

    def _get_user(self, discord_id, guild_id):
        # Local User (For Rewards)
        return self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()

    def get_or_create_user(self, discord_id, guild_id, username):
        user = self.session.query(User).filter_by(discord_id=discord_id, guild_id=guild_id).first()
        if not user:
            user = User(
                discord_id=discord_id,
                guild_id=guild_id,
                username=username
            )
            self.session.add(user)
            self.session.commit()
        GachaService.check_refills(self, user)
        return user

    def _get_global_tracker(self, discord_id):
        # Global Tracker (For Progress)
        tracker = self.session.query(GlobalTutorial).filter_by(discord_id=str(discord_id)).first()
        if not tracker:
            tracker = GlobalTutorial(discord_id=str(discord_id))
            self.session.add(tracker)
            self.session.commit()
        return tracker

    def get_tutorial_status(self, discord_id, guild_id, username, page=None):
        """Returns the Embed for a specific tutorial level."""
        self.get_or_create_user(discord_id, guild_id, username)
        tracker = self._get_global_tracker(discord_id)
        current_progress = tracker.tutorial_progress
        
        # 1. Determine which page to show
        if page is None:
            # Default to current progress
            target_index = current_progress
        else:
            # User requested specific page (1-based input -> 0-based index)
            target_index = page - 1

        # 2. Validation: Cannot look into the future
        if target_index > current_progress:
            return {
                "success": False, 
                "message": f"⛔ **Locked!** You must complete Tutorial {target_index} before you can view Tutorial {target_index + 1}."
            }
        
        # 3. Validation: Game Over check
        # If they finished everything (progress = 8) and ask for page 9 (index 8), show completed screen
        if target_index >= len(self.TUTORIALS):
            if current_progress >= len(self.TUTORIALS):
                embed = discord.Embed(
                    title="🎓 Tutorials Completed!",
                    description="🎉 You have completed all the tutorials!\nType `/index` to see all available commands.",
                    color=discord.Color.gold()
                )
                return {"success": True, "embed": embed}
            else:
                return {"success": False, "message": "Invalid tutorial page number."}

        # 4. Build Embed
        data = self.TUTORIALS[target_index]
        flags = tracker.tutorial_flags if isinstance(tracker.tutorial_flags, dict) else {}

        embed = discord.Embed(
            title=data["title"],
            description=f"{data['description']}\n\n**Reward:** {data['reward_text']}",
            color=discord.Color.orange()
        )

        for step_key, step_desc in data["steps"].items():
            # Check if this specific step is done
            status = "✅" if flags.get(step_key) else "⬜"
            embed.add_field(name=step_desc, value=status, inline=False)

        embed.set_footer(text=f"Page {target_index + 1}/{len(self.TUTORIALS)}")
        return {"success": True, "embed": embed}
    
    def sync_rewards(self, discord_id, guild_id):
        """
        Checks if the user's Local progress lags behind their Global progress.
        If so, grants the missing rewards for this server.
        """
        tracker = self._get_global_tracker(discord_id)
        user = self._get_user(discord_id, guild_id)
        
        if not user:
            return {"success": False, "message": "User profile not found. Try running /tutorial first."}

        global_level = tracker.tutorial_progress
        local_level = user.tutorial_progress # Currently 0 for most users
        
        if local_level >= global_level:
            return {"success": False, "message": "You are all caught up on rewards for this server!"}

        rewards_given = []

        # Iterate through the levels the user completed globally but hasn't claimed locally
        for level_idx in range(local_level, global_level):
            # Safety check in case global progress exceeds defined tutorials
            if level_idx >= len(self.TUTORIALS): 
                break
                
            data = self.TUTORIALS[level_idx]
            reward = data["reward"]
            
            # Grant the reward locally
            if reward["type"] == "coins":
                user.coins += reward["amount"]
            elif reward["type"] == "free_claim":
                user.free_claims += reward["amount"]
            elif reward["type"] == "max_rolls":
                user.max_rolls += reward["amount"]
            
            rewards_given.append(f"• **{data['title']}**: {data['reward_text']}")

        # Fast-forward local progress to match global
        user.tutorial_progress = global_level
        self.session.commit()

        embed = discord.Embed(
            title="🎁 Tutorial Rewards Synced",
            description=f"We found completed tutorials from your other servers!\n\n" + "\n".join(rewards_given),
            color=discord.Color.green()
        )
        return {"success": True, "embed": embed}

    def complete_step(self, discord_id, guild_id, step_key):
        """
        Marks a step as complete Globally. Grants reward Locally if level up.
        Strictly enforced: Can only complete steps for the CURRENT level.
        """
        tracker = self._get_global_tracker(discord_id)
        current_level = tracker.tutorial_progress
        
        if current_level >= len(self.TUTORIALS): return None 

        data = self.TUTORIALS[current_level]
        
        # 1. STRICT ORDER CHECK
        # If the step_key passed isn't in the current level's list, ignore it.
        # This prevents completing Tutorial 2 steps while on Tutorial 1.
        if step_key not in data["steps"]:
            return None 

        # 2. Update Global Flag
        flags = dict(tracker.tutorial_flags) if tracker.tutorial_flags else {}
        if flags.get(step_key):
            return None # Already complete

        flags[step_key] = True
        tracker.tutorial_flags = flags 
        
        # 3. Check Level Completion
        all_done = all(flags.get(k) for k in data["steps"].keys())
        
        result_msg = "✅ **Tutorial Step Complete!** Check `/tutorial`."

        if all_done:
            # 4. GRANT REWARD (To Local User in this Guild)
            user = self._get_user(discord_id, guild_id)
            if user:
                reward = data["reward"]
                if reward["type"] == "coins":
                    user.coins += reward["amount"]
                elif reward["type"] == "free_claim":
                    user.free_claims += reward["amount"]
                elif reward["type"] == "max_rolls":
                    user.max_rolls += reward["amount"]
            
            # 5. Advance Global Level
            tracker.tutorial_progress += 1
            # --- NEW: CHECK FOR GRAND FINALE ---
            # If progress equals length, they just finished the last one (Index 7 -> 8)
            if tracker.tutorial_progress >= len(self.TUTORIALS):
                result_msg = (
                    "🏆 **CONGRATULATIONS!** 🏆\n"
                    "You have completed the entire Tutorial Campaign!\n\n"
                    f"You received **{data['reward_text']}**.\n"
                    "You are now a certified manager. Use **/index** to view the full command list at any time.\n\n"
                    "🚀 **Want a Head Start?**\n"
                    "Invite a friend to play and you **BOTH get 1,000 Coins!** \n"
                    "Type **/invite** to get your link."
                )
            else:
                result_msg = f"🎉 **{data['title']} Completed!**\nReward: **{data['reward_text']}**\nType `/tutorial` for the next one!"

        self.session.commit()
        return result_msg
    
    