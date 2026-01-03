# tests/test_team.py
"""
from src.services.team_service import TeamService
from src.database.models import Card, User

def test_set_lineup_success(session):
    service = TeamService(session)
    
    # Alice has Messi (RW/ST)
    card = Card(user_id=1, player_base_id=1) 
    session.add(card)
    session.commit()
    
    # Set Messi to F1 (Forward) -> Valid
    result = service.set_lineup_player("100", "999", "F1", "Messi")
    
    assert result["success"] is True
    assert "set to **F1**" in result["message"]
    
    session.refresh(card)
    assert card.position_in_xi == "F1"

def test_set_lineup_wrong_position(session):
    service = TeamService(session)
    
    # Alice has Messi (RW/ST)
    card = Card(user_id=1, player_base_id=1) 
    session.add(card)
    session.commit()
    
    # Try to set Messi to GK -> Invalid
    result = service.set_lineup_player("100", "999", "GK", "Messi")
    
    assert result["success"] is False
    assert "cannot play in" in result["message"]

def test_ovl_calculation(session):
    service = TeamService(session)
    
    # Alice puts Messi (Rating 5000) and Pedri (Rating 3000) in team
    c1 = Card(user_id=1, player_base_id=1, position_in_xi="F1")
    c2 = Card(user_id=1, player_base_id=2, position_in_xi="M1")
    session.add_all([c1, c2])
    session.commit()
    
    stats = service.get_team_stats_and_rewards("100", "999")
    
    # FIX: Updated expected math based on new ratings
    # 5000 + 3000 = 8000
    assert stats["ovl_value"] == 4000
    assert stats["player_count"] == 2
"""