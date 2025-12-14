# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DISCORD_TOKEN:
    raise ValueError("Missing DISCORD_TOKEN in .env file")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL in .env file")