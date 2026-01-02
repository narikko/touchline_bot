from sqlalchemy.orm import joinedload
from src.database.models import User, Card, PlayerBase, MarketListing

class TradeService:
    def __init__(self, session):
        self.session = session

    def get_or_create_user(self, discord_id, guild_id, username):
        user = self.session.query(User).filter_by(discord_id=str(discord_id), guild_id=str(guild_id)).first()
        if not user:
            user = User(discord_id=str(discord_id), guild_id=str(guild_id), username=username)
            self.session.add(user)
            self.session.commit()
        return user

    def validate_offer(self, discord_id, guild_id, player_names_str):
        """
        Parses a string like "Messi, Ronaldo" and finds valid cards.
        Returns: {"success": True, "cards": [Card objects]} or Error.
        """
        user = self.get_or_create_user(discord_id, guild_id, "Unknown")
        
        # 1. Parse Input
        # Split by comma, strip whitespace, remove empty strings
        names = [n.strip() for n in player_names_str.split(',') if n.strip()]
        
        if len(names) > 3:
            return {"success": False, "message": "❌ You can only trade up to **3 players** at once."}
        
        if not names:
            return {"success": False, "message": "❌ No valid player names provided."}

        found_cards = []
        found_ids = set()

        # 2. Find Each Card
        for name in names:
            # We search for a card owned by the user
            card = self.session.query(Card).join(PlayerBase)\
                .options(joinedload(Card.details))\
                .outerjoin(MarketListing, Card.id == MarketListing.card_id)\
                .filter(Card.user_id == user.id)\
                .filter(PlayerBase.name.ilike(f"%{name}%"))\
                .filter(MarketListing.id == None)\
                .order_by(Card.sort_priority.desc())\
                .first()

            if not card:
                return {"success": False, "message": f"❌ You don't own a tradable card matching **'{name}'**."}
            
            if card.position_in_xi:
                return {"success": False, "message": f"❌ **{card.details.name}** is in your Starting XI. Bench them first."}
            
            if card.id in found_ids:
                 return {"success": False, "message": f"❌ You are trying to offer **{card.details.name}** twice!"}

            found_cards.append(card)
            found_ids.add(card.id)

        return {"success": True, "cards": found_cards}

    def execute_multi_trade(self, card_ids_a, card_ids_b):
        """
        Swaps ownership of two LISTS of cards.
        """
        # Fetch all cards involved
        cards_a = self.session.query(Card).filter(Card.id.in_(card_ids_a)).all()
        cards_b = self.session.query(Card).filter(Card.id.in_(card_ids_b)).all()

        # 1. Verification
        if len(cards_a) != len(card_ids_a) or len(cards_b) != len(card_ids_b):
             return {"success": False, "message": "Trade failed: One or more cards no longer exist."}

        # Check XI status again just to be safe
        for c in cards_a + cards_b:
            if c.position_in_xi:
                return {"success": False, "message": f"Trade failed: **{c.details.name}** is in a Starting XI."}

        # 2. Get Owners (From the first card of each side)
        # We enforce at least 1 card per side
        if not cards_a or not cards_b:
             return {"success": False, "message": "Trade failed: Both sides must offer at least one card."}

        owner_a_id = cards_a[0].user_id
        owner_b_id = cards_b[0].user_id

        # 3. SWAP
        # All cards from A go to B
        for c in cards_a:
            c.user_id = owner_b_id
            c.position_in_xi = None # Reset pos
            c.is_locked = False     # Unlock if locked

        # All cards from B go to A
        for c in cards_b:
            c.user_id = owner_a_id
            c.position_in_xi = None
            c.is_locked = False

        self.session.commit()
        
        return {
            "success": True, 
            "message": "Trade Successful!"
        }