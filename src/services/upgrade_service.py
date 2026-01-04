from src.database.models import User
from src.services.team_service import TeamService

class UpgradeService:
    def __init__(self, session):
        self.session = session
        
        # Configuration mapped from your arrays
        self.UPGRADE_CONFIG = {
            "stadium": {
                "name": "Stadium 🏟️",
                "description": "Increases chances of rolling a player from your **Favorite Club** (excluding Legends).",
                "bonuses": ["0.5%", "1%", "2%", "3%", "5%"], 
                "prices": [1000, 2000, 4000, 8000, 16000] 
            },
            "board": {
                "name": "Board 👔",
                "description": "Boosts **overall income** (Dailies, Selling, Duplicates).",
                "bonuses": ["5%", "10%", "15%", "20%", "25%"], 
                "prices": [3000, 9000, 27000, 50000, 81000]
            },
            "training": {
                "name": "Training Facility 🏋️‍♂️",
                "description": "Boosts the overall **value rating** of your Starting XI.",
                "bonuses": ["3%", "5%", "7%", "10%", "15%"], 
                "prices": [500, 1000, 3000, 8000, 12000]
            },
            "transfer": {
                "name": "Transfer Market 📜",
                "description": "Reduces the **wait time** for transfers to be completed.",
                "bonuses": ["24 hours", "18 hours", "12 hours", "6 hours", "3 hours"],
                "prices": [2000, 5000, 10000, 30000, 75000]
            },
            "scout": {
                "name": "Scout Network 🔭",
                "description": "Increases **Shortlist** size. Get notified when others roll your target players!",
                # Capacities: Lvl0=1, Lvl1=3, Lvl2=5, Lvl3=10, Lvl4=15, Lvl5=25
                "bonuses": ["3 Slots", "4 Slots", "5 Slots", "7 Slots", "10 Slots"], 
                "prices": [750, 1500, 3000, 7500, 17500],
            }
        }

    def _get_user(self, discord_id, guild_id):
        return self.session.query(User).filter_by(discord_id=discord_id, guild_id=guild_id).first()

    def get_menu_info(self, discord_id, guild_id):
        """Returns data for the %u info menu."""
        user = self._get_user(discord_id, guild_id)
        if not user:
            # If user doesn't exist, just show default prices (level 0)
            user_balance = 0
            current_levels = {k: 0 for k in self.UPGRADE_CONFIG}
        else:
            user_balance = user.coins
            # Fetch current levels safely
            current_levels = {
                k: getattr(user, f"upgrade_{k}", 0) for k in self.UPGRADE_CONFIG
            }

        info_list = []
        
        for key, config in self.UPGRADE_CONFIG.items():
            lvl = current_levels[key] # 0 to 5
            max_lvl = len(config["prices"])
            
            # Determine Next Price
            # If lvl is 0, next price is prices[0]
            if lvl < max_lvl:
                next_price = config["prices"][lvl]
                # Preview the next bonus
                next_bonus = config["bonuses"][lvl]
            else:
                next_price = "MAX"
                next_bonus = config["bonuses"][-1] # Show max bonus

            # Current Bonus String
            if lvl == 0:
                current_bonus_display = "None"
            else:
                current_bonus_display = str(config["bonuses"][lvl - 1])
                # Add "%" for board
                if key == "board": current_bonus_display += "%"

            info_list.append({
                "name": config["name"],
                "key": key,
                "current_level": lvl,
                "max_level": max_lvl,
                "next_price": next_price,
                "current_bonus": current_bonus_display,
                "next_bonus": next_bonus,
                "description": config["description"]
            })

        return {"success": True, "upgrades": info_list, "user_balance": user_balance}

    def buy_upgrade(self, discord_id, guild_id, upgrade_key):
        """Attempts to level up a specific upgrade."""
        user = self._get_user(discord_id, guild_id)
        if not user:
            return {"success": False, "message": "User not found. Run /r or /start first."}
        
        key = upgrade_key.lower()
        if key not in self.UPGRADE_CONFIG:
            return {"success": False, "message": f"Upgrade '{upgrade_key}' does not exist. Try: stadium, board, training, transfer."}

        config = self.UPGRADE_CONFIG[key]
        
        # 1. Get Current Level
        current_level = getattr(user, f"upgrade_{key}", 0)
        max_level = len(config["prices"])

        # 2. Check Max Level
        if current_level >= max_level:
            return {"success": False, "message": f"**{config['name']}** is already at Max Level!"}

        # 3. Get Price
        # The price to get to Level 1 is at index 0
        cost = config["prices"][current_level]

        # 4. Check Balance
        if user.coins < cost:
            return {"success": False, "message": f"You need **{cost}** coins to upgrade {config['name']}."}

        # 5. Execute
        user.coins -= cost
        setattr(user, f"upgrade_{key}", current_level + 1)
        self.session.commit()

        # Get the new bonus value to display
        new_bonus = config["bonuses"][current_level] # Now at this index

        reward_msg = TeamService.process_milestone_check(self, user)

        return {
            "success": True, 
            "name": config["name"],
            "new_level": current_level + 1,
            "cost": cost,
            "new_bonus": new_bonus,
            "balance": user.coins,
            "reward": reward_msg
        }