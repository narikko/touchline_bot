from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint, BigInteger, JSON
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, nullable=False)
    guild_id = Column(String, nullable=False)
    username = Column(String, nullable=False)
    
    # Economy & Stats
    coins = Column(Integer, default=0)
    club_name = Column(String, nullable=True)
    favorite_club = Column(String, nullable=True)
    
    # Timers
    rolls_remaining = Column(Integer, default=9)
    claims_remaining = Column(Integer, default=1)
    max_rolls = Column(Integer, default=9)
    free_claims = Column(Integer, default=0)
    
    last_roll_reset = Column(DateTime, default=datetime.utcnow)
    last_claim_reset = Column(DateTime, default=datetime.utcnow)
    last_daily_claim = Column(DateTime, nullable=True)
    
    # Upgrades
    upgrade_stadium = Column(Integer, default=0)
    upgrade_board = Column(Integer, default=0)
    upgrade_training = Column(Integer, default=0)
    upgrade_transfer = Column(Integer, default=0)
    upgrade_scout = Column(Integer, default=0)

    # JSON with variant for SQLite/Postgres compatibility
    tutorial_flags = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    tutorial_progress = Column(Integer, default=0)
    team_rewards_flags = Column(JSON().with_variant(JSONB, "postgresql"), default=list)

    redeemed_referral = Column(Boolean, default=False)
    roll_refreshes = Column(Integer, default=0)

    # --- EXPLICIT RELATIONSHIPS (The Fix) ---
    # These replace the old 'backrefs'
    cards = relationship("Card", back_populates="user", cascade="all, delete-orphan")
    shortlist_items = relationship("Shortlist", back_populates="user", cascade="all, delete-orphan")

    formation = Column(String, default="4-3-3")
    
    __table_args__ = (UniqueConstraint('discord_id', 'guild_id', name='_user_guild_uc'),)

class Card(Base):
    __tablename__ = 'cards'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    player_base_id = Column(Integer, ForeignKey('player_base.id'))
    position_in_xi = Column(String, nullable=True) 
    obtained_at = Column(DateTime, default=datetime.utcnow)
    sort_priority = Column(BigInteger, default=0)

    # Link back to User explicitly
    user = relationship("User", back_populates="cards")
    
    # Simple join for details
    details = relationship("PlayerBase")

class PlayerBase(Base):
    __tablename__ = 'player_base'
    
    id = Column(Integer, primary_key=True) 
    name = Column(String, nullable=False)
    club = Column(String, nullable=False)
    nationality = Column(String, nullable=False)
    positions = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    rarity = Column(String, nullable=False) 
    image_url = Column(String, nullable=True)
    
    @property
    def value(self):
        return self.rating 

class MarketListing(Base):
    __tablename__ = 'market_listings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    card_id = Column(Integer, ForeignKey('cards.id'))
    listed_price = Column(Integer, nullable=False)
    available_at = Column(DateTime, nullable=False)
    listed_at = Column(DateTime, default=datetime.utcnow)

class Shortlist(Base):
    __tablename__ = 'shortlists'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    player_base_id = Column(Integer, ForeignKey('player_base.id'))
    
    # Link back to User explicitly
    user = relationship("User", back_populates="shortlist_items")
    player = relationship("PlayerBase")
    
    __table_args__ = (UniqueConstraint('user_id', 'player_base_id', name='_user_shortlist_uc'),)

class GlobalTutorial(Base):
    __tablename__ = 'global_tutorials'
    
    discord_id = Column(String, primary_key=True)
    tutorial_flags = Column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    tutorial_progress = Column(Integer, default=0)