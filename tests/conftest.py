# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, User, PlayerBase, Card

# Use in-memory SQLite for speed and isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def session():
    """Creates a new database session for a test."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)  # Create tables
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # --- SEED BASIC DATA ---
    # Create 2 Users
    u1 = User(discord_id="100", guild_id="999", username="Alice", coins=10000)
    u2 = User(discord_id="200", guild_id="999", username="Bob", coins=10000)
    
    # Create 3 Players
    # FIX: 'value' is a property, so we put the value/score into 'rating'.
    # This matches your seed_db.py logic.
    p1 = PlayerBase(id=1, name="Messi", rating=5000, rarity="Legend", positions="RW/ST", club="Inter Miami", nationality="Argentina")
    p2 = PlayerBase(id=2, name="Pedri", rating=3000, rarity="Ultra Rare", positions="CM", club="Barcelona", nationality="Spain")
    p3 = PlayerBase(id=3, name="Van Dijk", rating=4000, rarity="Ultra Rare", positions="CB", club="Liverpool", nationality="Netherlands")
    
    session.add_all([u1, u2, p1, p2, p3])
    session.commit()
    
    yield session  # This is where the test runs
    
    session.close()
    Base.metadata.drop_all(engine)