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
        # init_db() # Ensure this import is correct based on your file structure
        
        # 2. Load Cogs
        extensions = [
            "src.cogs.gacha", "src.cogs.team", "src.cogs.upgrade",
            "src.cogs.market", "src.cogs.trade", "src.cogs.match",
            "src.cogs.tutorial", "src.cogs.vote", "src.cogs.general"
        ]
        for ext in extensions:
            await self.load_extension(ext)
        print("--- Cogs Loaded ---")

        # 3. Sync Commands
        # If ENV is 'dev', sync to specific guild. If 'prod', sync globally.
        import os
        env = os.getenv("ENV", "prod") # Default to prod if missing
        
        if env == "dev":
            DEV_GUILD_ID = discord.Object(id=775442968177541150)
            print(f"--- Syncing to Development Guild ({DEV_GUILD_ID.id}) ---")
            self.tree.copy_global_to(guild=DEV_GUILD_ID)
            await self.tree.sync(guild=DEV_GUILD_ID)
        else:
            print("--- Syncing Globally (This may take up to 1 hour) ---")
            await self.tree.sync()
            
        print("--- Sync Complete ---")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        await self.change_presence(activity=discord.Game(name="Start your journey with /tutorial"))
async def main():
    bot = SoccerBot()

    @bot.command(name="sync")
    @commands.is_owner()
    async def sync(ctx):
        # This syncs to the specific server (guild) immediately
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Synced {len(synced)} commands to this server!")

    @bot.command(name="fix_duplicates")
    @commands.is_owner()
    async def fix_duplicates(ctx):
        # 1. Clear the local guild commands queue
        bot.tree.clear_commands(guild=ctx.guild)
        
        # 2. Sync this empty queue to the guild (effectively deleting the guild commands on Discord's side)
        await bot.tree.sync(guild=ctx.guild)
        
        await ctx.send("✅ Guild-specific commands cleared! You should now only see the Global commands (updates might take 1 hour).")
        
    token = DISCORD_TOKEN
    if not token:
        print("FATAL ERROR: DISCORD_TOKEN not found in environment.")
        return
        
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())