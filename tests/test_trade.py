# tests/test_trade.py
"""
from src.services.trade_service import TradeService
from src.database.models import Card

def test_trade_success(session):
    service = TradeService(session)
    
    # Alice (1) has Messi (1)
    # Bob (2) has Pedri (2)
    c1 = Card(user_id=1, player_base_id=1)
    c2 = Card(user_id=2, player_base_id=2)
    session.add_all([c1, c2])
    session.commit()
    
    # Execute Trade
    result = service.execute_trade(c1.id, c2.id)
    
    assert result["success"] is True
    
    # Refresh from DB
    session.refresh(c1)
    session.refresh(c2)
    
    # Alice (1) should now own Pedri (c2)
    # Bob (2) should now own Messi (c1)
    assert c1.user_id == 2
    assert c2.user_id == 1

def test_trade_fail_if_equipped(session):
    service = TradeService(session)
    
    # Alice has Messi in her Starting XI
    c1 = Card(user_id=1, player_base_id=1, position_in_xi="RW")
    c2 = Card(user_id=2, player_base_id=2)
    session.add_all([c1, c2])
    session.commit()
    
    result = service.execute_trade(c1.id, c2.id)
    
    assert result["success"] is False
    assert "Starting XI" in result["message"]
    
    # Verify ownership did NOT change
    session.refresh(c1)
    assert c1.user_id == 1
    """