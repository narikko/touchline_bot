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
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # 1. Initialize Database
        print("--- Initializing Database ---")
        init_db()
        
        # 2. Load Cogs
        await self.load_extension("src.cogs.gacha") 
        print("--- Cog 'Gacha' Loaded ---")

        # 3. TEMPORARY GUILD SYNC FOR FAST TESTING
        DEV_GUILD_ID = discord.Object(id=775442968177541150) 
        
        print("--- Syncing to Development Guild ---")
        try:
            # Syncs commands only to the specified Guild ID
            self.tree.copy_global_to(guild=DEV_GUILD_ID)
            synced = await self.tree.sync(guild=DEV_GUILD_ID)
            print(f"Synced {len(synced)} command(s) to Guild ID {775442968177541150}.")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

async def main():
    bot = SoccerBot()
    token = DISCORD_TOKEN
    if not token:
        print("FATAL ERROR: DISCORD_TOKEN not found in environment.")
        return
        
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())