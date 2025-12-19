from unittest.mock import patch
from src.services.gacha_service import GachaService
from src.database.models import Card, User

def test_roll_new_card(session):
    service = GachaService(session)
    
    # FIX: Force the rarity to be 'Legend' so we find Messi (ID 1)
    # The 'object' argument string must point to where determine_rarity is DEFINED/USED
    with patch.object(GachaService, 'determine_rarity', return_value="Legend"):
        result = service.roll_card("100", "999", "Alice")
        
        assert result["success"] is True
        assert result["is_duplicate"] is False
        assert result["player"] is not None
        assert result["rolls_remaining"] == 8

def test_duplicate_gives_coins(session):
    service = GachaService(session)
    
    # Alice already owns Messi (ID 1)
    c1 = Card(user_id=1, player_base_id=1)
    session.add(c1)
    session.commit()
    
    # FIX: Force 'Legend' again so we roll Messi again
    with patch.object(GachaService, 'determine_rarity', return_value="Legend"):
        # We also need to ensure the random query picks ID 1 if there were multiple Legends,
        # but since our seed only has 1 Legend (Messi), this is sufficient.
        result = service.roll_card("100", "999", "Alice")
        
        assert result["success"] is True
        assert result["is_duplicate"] is True
        assert result["coins_gained"] > 0