from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint, BigInteger
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    # Internal Database ID (e.g., User #1, User #2)
    # We use this to link Cards to Users efficiently.
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # The combination of these two MUST be unique
    discord_id = Column(String, nullable=False)
    guild_id = Column(String, nullable=False)
    
    username = Column(String)
    
    # Economy
    coins = Column(Integer, default=0)
    
    # Game State
    club_name = Column(String, default="My Club")
    favorite_club = Column(String, default="")
    
    # Gameplay Resources
    rolls_remaining = Column(Integer, default=9)
    claims_remaining = Column(Integer, default=1)
    max_rolls = Column(Integer, default=9)
    free_claims = Column(Integer, default=0)
    
    # Timers (Stored as UTC timestamps)
    last_roll_reset = Column(DateTime, default=datetime.utcnow)
    last_claim_reset = Column(DateTime, default=datetime.utcnow)
    last_daily_claim = Column(DateTime, nullable=True)
    
    # Upgrades
    upgrade_stadium = Column(Integer, default=0)
    upgrade_board = Column(Integer, default=0)
    upgrade_training = Column(Integer, default=0)
    upgrade_transfer = Column(Integer, default=0)

    # Progress Flags
    # Stores [True, False, ...] for tutorial steps
    tutorial_flags = Column(JSONB, default=list) 
    tutorial_progress = Column(Integer, default=0)
    
    # Stores [True, False, ...] for team value rewards (300, 400, etc.)
    team_rewards_flags = Column(JSONB, default=list)
    
    # Relationships
    cards = relationship("Card", back_populates="owner")
    market_listings = relationship("MarketListing", back_populates="seller")

    # Ensures one user cannot have duplicate rows for the same server
    __table_args__ = (UniqueConstraint('discord_id', 'guild_id', name='_user_server_uc'),)


class PlayerBase(Base):
    __tablename__ = 'player_base'
    
    # This represents the "Definition" of a player 
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    name = Column(String, nullable=False)
    club = Column(String)
    nationality = Column(String)
    positions = Column(String) # e.g. "ST/CF"
    rating = Column(Integer)
    rarity = Column(String) # "Common", "Rare", "Ultra", "Legend"
    image_url = Column(String)
    
    value = Column(Integer)


class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Links to the User's internal ID (which represents User+Server)
    user_id = Column(Integer, ForeignKey('users.id'))
    player_base_id = Column(Integer, ForeignKey('player_base.id'))
    
    obtained_at = Column(DateTime, default=datetime.utcnow)
    sort_priority = Column(BigInteger, default=0)
    
    # Team Management
    # "F1", "F2", "GK", etc. or None if on bench
    position_in_xi = Column(String, nullable=True) 
    
    owner = relationship("User", back_populates="cards")
    details = relationship("PlayerBase")


class MarketListing(Base):
    __tablename__ = 'market_listings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey('users.id'))
    card_id = Column(Integer, ForeignKey('cards.id'))
    
    listed_price = Column(Integer)
    listed_at = Column(DateTime, default=datetime.utcnow)
    available_at = Column(DateTime)
    
    seller = relationship("User", back_populates="market_listings")
    card = relationship("Card")