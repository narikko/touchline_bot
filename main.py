import asyncio
import os
import discord
from discord.ext import commands
from src.config import DISCORD_TOKEN
from src.database.db import init_db

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True

class SoccerBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="%", intents=intents, help_command=None)

    async def setup_hook(self):
        # 1. Initialize Database
        print("--- Initializing Database ---")
        init_db()
        
        # 2. Load Cogs
        await self.load_extension("src.cogs.gacha") 
        print("--- Cog 'Gacha' Loaded ---")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

async def main():
    bot = SoccerBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())