# tests/test_match.py
from src.services.match_service import MatchService
from src.database.models import User

def test_match_wager_processing(session):
    service = MatchService(session)
    
    # Alice (10k), Bob (10k)
    # Wager 1000
    success = service.process_wager(1, 2, 1000)
    
    assert success is True
    
    u1 = session.query(User).filter_by(discord_id="100").first()
    u2 = session.query(User).filter_by(discord_id="200").first()
    
    assert u1.coins == 9000
    assert u2.coins == 9000

def test_match_payout(session):
    service = MatchService(session)
    
    # Assuming wager was processed (coins deducted)
    # Pot is 2000. Winner is Alice ("home").
    service.payout(1, 2, "home", 1000)
    
    u1 = session.query(User).filter_by(discord_id="100").first()
    
    # 10000 start - 1000 wager + 2000 win = 11000
    # Note: In test flow, we need to manually deduct first or assume previous state
    # If we just run payout on fresh 10k users: 10k + 2k = 12k
    assert u1.coins == 12000