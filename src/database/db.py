# src/database/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import DATABASE_URL
from src.database.models import Base

# Create engine
engine = create_engine(DATABASE_URL)

# Create Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Creates tables if they don't exist"""
    Base.metadata.create_all(bind=engine)

def get_session():
    """Returns a new DB session"""
    return SessionLocal()