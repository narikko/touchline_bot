# tests/test_economy.py
from datetime import datetime, timedelta
from unittest.mock import patch
from src.services.upgrade_service import UpgradeService
from src.services.transfer_service import TransferService
from src.database.models import MarketListing, Card, User

def test_buy_upgrade_success(session):
    service = UpgradeService(session)
    # Alice buys Stadium Level 1 (Cost 1000)
    # Initial: 10,000 coins. Level: 0.
    result = service.buy_upgrade("100", "999", "stadium")
    
    assert result["success"] is True
    assert result["new_level"] == 1
    assert result["balance"] == 9000  # 10000 - 1000

def test_buy_upgrade_poor(session):
    service = UpgradeService(session)
    # Set Alice's coins to 0
    alice = session.query(User).filter_by(discord_id="100").first()
    alice.coins = 0
    session.commit()
    
    result = service.buy_upgrade("100", "999", "stadium")
    assert result["success"] is False
    assert "You need" in result["message"]

def test_market_listing(session):
    t_service = TransferService(session)
    
    # Give Alice a Messi card
    card = Card(user_id=1, player_base_id=1)
    session.add(card)
    session.commit()
    
    # List Messi
    result = t_service.add_to_market("100", "999", "Messi")
    assert result["success"] is True
    
    # Verify DB
    listing = session.query(MarketListing).first()
    assert listing is not None
    assert listing.card_id == card.id

def test_market_sale_complete(session):
    t_service = TransferService(session)
    
    # Give Alice a card and list it
    card = Card(user_id=1, player_base_id=1) # Value 5000
    session.add(card)
    session.commit()
    t_service.add_to_market("100", "999", "Messi")
    
    # Mock time to be 4 days in the future (Market wait is 3 days default)
    future = datetime.utcnow() + timedelta(days=4)
    
    with patch('src.services.transfer_service.datetime') as mock_date:
        mock_date.utcnow.return_value = future
        
        # Check status
        result = t_service.check_transfer_status("100", "999")
        
        assert result["status"] == "completed"
        # Base 5000 * 2.0 = 10000
        assert result["value"] == 10000 
        
        # User coins should be 10000 (start) + 10000 (sale) = 20000
        # (Note: In unit tests user ID is usually 1 for "100")
        alice = session.query(User).filter_by(discord_id="100").first()
        assert alice.coins == 20000