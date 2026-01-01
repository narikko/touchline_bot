import random
from sqlalchemy.orm import joinedload
from src.database.models import User, Card, PlayerBase

class MatchService:
    def __init__(self, session):
        self.session = session
        
        # Categorize Slots
        self.ATTACK_SLOTS = ["F1", "F2", "F3"]
        self.MIDFIELD_SLOTS = ["M1", "M2", "M3"]
        self.DEFENSE_SLOTS = ["D1", "D2", "D3", "D4", "GK"]

        # Training Bonuses (Level 1 to Level 5)
        # Level 1 (+3%), Level 2 (+5%), Level 3 (+7%), Level 4 (+10%), Level 5 (+15%)
        self.TRAINING_MULTIPLIERS = [0.03, 0.05, 0.07, 0.10, 0.15]

        self.GOAL_LINES = [
            "What a screamer! ⚽ [Player] finds the top corner!",
            "Beautiful team play! [Player] taps it in! ⚽",
            "[Player] dribbles past the keeper and scores! ⚽",
            "GOAAAL! [Player] with a header from the corner! ⚽"
        ]
        self.SAVE_LINES = [
            "What a save! [Player] denies the goal! 🧤",
            "[Player] blocks the shot with a sliding tackle! 🛡️",
            "The keeper [Player] tips it over the bar! 🧤",
            "Solid defense from [Player] to stop the attack. 🛡️"
        ]

    def get_team_power(self, user_id, guild_id):
        """Calculates Attack, Midfield, Defense scores based on the lineup + Training Upgrades."""
        user = self.session.query(User).filter_by(discord_id=str(user_id), guild_id=str(guild_id)).first()
        if not user: return None

        # Fetch Lineup
        cards = self.session.query(Card).join(PlayerBase)\
            .filter(Card.user_id == user.id, Card.position_in_xi.isnot(None))\
            .all()

        if len(cards) < 11:
            return {"valid": False, "message": "You need a full team of 11 players to play!"}

        stats = {"attack": [], "midfield": [], "defense": [], "gk": None}
        roster = {"attack": [], "midfield": [], "defense": [], "gk": []}

        for card in cards:
            pos = card.position_in_xi
            rating = card.details.rating
            name = card.details.name

            if pos in self.ATTACK_SLOTS:
                stats["attack"].append(rating)
                roster["attack"].append(name)
            elif pos in self.MIDFIELD_SLOTS:
                stats["midfield"].append(rating)
                roster["midfield"].append(name)
            elif pos in self.DEFENSE_SLOTS:
                stats["defense"].append(rating)
                if pos == "GK":
                    stats["gk"] = rating
                    roster["gk"].append(name)
                else:
                    roster["defense"].append(name)

        # Calculate Base Averages
        def avg(lst): return int(sum(lst) / len(lst)) if lst else 0

        att_pwr = avg(stats["attack"])
        mid_pwr = avg(stats["midfield"])
        def_pwr = avg(stats["defense"])

        # --- NEW: APPLY TRAINING UPGRADE BOOST ---
        training_level = user.upgrade_training # Defaults to 0 if not set
        
        if training_level > 0:
            # Ensure we don't crash if level is higher than our list (safety check)
            # Level 1 corresponds to index 0
            index = min(training_level, len(self.TRAINING_MULTIPLIERS)) - 1
            
            if index >= 0:
                bonus_pct = self.TRAINING_MULTIPLIERS[index] # e.g., 0.03 for Level 1
                multiplier = 1.0 + bonus_pct
                
                # Apply boost
                att_pwr = int(att_pwr * multiplier)
                mid_pwr = int(mid_pwr * multiplier)
                def_pwr = int(def_pwr * multiplier)
        # -----------------------------------------
        
        overall = int((att_pwr + mid_pwr + def_pwr) / 3)

        return {
            "valid": True,
            "att": att_pwr, "mid": mid_pwr, "def": def_pwr, "ovr": overall,
            "roster": roster,
            "user": user
        }

    def simulate_match(self, home_stats, away_stats):
        """
        Generates random events (between 5 and 12) spread over 90 seconds.
        """
        timeline = []
        home_score = 0
        away_score = 0

        home_roster = home_stats["roster"]
        away_roster = away_stats["roster"]

        total_ovr = home_stats["ovr"] + away_stats["ovr"]
        if total_ovr == 0: total_ovr = 1
        
        home_advantage = home_stats["ovr"] / total_ovr 

        # CHANGED: Randomize number of events between 5 and 12
        # This makes some matches quiet (5 events) and others chaotic (12 events)
        num_events = random.randint(5, 12)

        # Timestamps between 5s and 85s
        event_timestamps = sorted([random.randint(5, 85) for _ in range(num_events)])

        for real_second in event_timestamps:
            game_minute = int(real_second)

            # 1. Who gets the chance?
            is_home_attack = random.random() < home_advantage
            
            attacker_stats = home_stats if is_home_attack else away_stats
            defender_stats = away_stats if is_home_attack else home_stats
            attacker_roster = home_roster if is_home_attack else away_roster
            defender_roster = away_roster if is_home_attack else home_roster

            # 2. Attack vs Defense Calculation (Including Midfield logic from before)
            att_base = (attacker_stats["att"] + attacker_stats["mid"]) / 2
            att_roll = att_base * random.uniform(0.8, 1.2)

            def_base = (defender_stats["def"] + defender_stats["mid"]) / 2
            def_roll = def_base * random.uniform(0.8, 1.2)

            if att_roll > def_roll:
                # GOAL
                if is_home_attack: home_score += 1
                else: away_score += 1

                r_pos = random.choice(["attack", "midfield", "attack"])
                available_scorers = attacker_roster[r_pos] if attacker_roster[r_pos] else ["Unknown Player"]
                scorer = random.choice(available_scorers)
                
                line = random.choice(self.GOAL_LINES).replace("[Player]", f"**{scorer}**")
                team_name = attacker_stats["user"].club_name
                
                timeline.append({
                    "real_second": real_second, 
                    "game_minute": game_minute,
                    "type": "goal",
                    "text": f"⚽ **GOAL!** {line} ({team_name})",
                    "score": (home_score, away_score)
                })
            else:
                # SAVE
                if random.random() < 0.6: 
                    saver = defender_roster["gk"][0] if defender_roster["gk"] else "GK"
                else:
                    available_defenders = defender_roster["defense"] if defender_roster["defense"] else ["Defender"]
                    saver = random.choice(available_defenders)
                
                line = random.choice(self.SAVE_LINES).replace("[Player]", f"**{saver}**")
                
                timeline.append({
                    "real_second": real_second,
                    "game_minute": game_minute,
                    "type": "save",
                    "text": f"🧤 **SAVE!** {line}",
                    "score": (home_score, away_score)
                })

        return {
            "timeline": timeline,
            "final_score": (home_score, away_score),
            "winner": "home" if home_score > away_score else ("away" if away_score > home_score else "draw")
        }

    def process_wager(self, user_id, opponent_id, amount):
        user = self.session.query(User).filter_by(id=user_id).first()
        opp = self.session.query(User).filter_by(id=opponent_id).first()
        
        if user.coins < amount or opp.coins < amount:
            return False
        
        user.coins -= amount
        opp.coins -= amount
        self.session.commit()
        return True

    def payout(self, user_id, opponent_id, result, amount):
        user = self.session.query(User).filter_by(id=user_id).first()
        opp = self.session.query(User).filter_by(id=opponent_id).first()
        
        pot = amount * 2
        
        if result == "home":
            user.coins += pot
        elif result == "away":
            opp.coins += pot
        else:
            # Draw
            user.coins += amount
            opp.coins += amount
            
        self.session.commit()