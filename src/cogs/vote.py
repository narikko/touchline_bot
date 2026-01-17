import discord
from discord.ext import commands, tasks
import topgg
from src.database.db import get_session
from src.database.models import User

# CONFIGURATION
WEBHOOK_PASSWORD = "jersey123"          

class VoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize the webhook manager
        self.webhook_manager = topgg.WebhookManager(bot).dbl_webhook("/vote", WEBHOOK_PASSWORD)
        
        # Start the server in the background so the bot doesn't freeze
        self.bot.loop.create_task(self.start_webhook())

    async def start_webhook(self):
        """Starts the webhook server on port 5000."""
        # We wrap this in a try/except to prevent crashing if the port is busy
        try:
            await self.webhook_manager.run(5000)
            print("✅ Top.gg Webhook running on port 5000")
        except Exception as e:
            print(f"❌ Failed to start webhook: {e}")

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """Triggered automatically when someone votes on Top.gg"""
        user_id = int(data["user"])
        print(f"🗳️ Vote received from User ID: {user_id}")
        
        session = get_session()
        try:
            # FIX: Get ALL instances of this user across all servers
            # We filter only by discord_id, ignoring guild_id to find them everywhere
            user_profiles = session.query(User).filter_by(discord_id=str(user_id)).all()
            
            if not user_profiles:
                print(f"⚠️ User {user_id} voted but has no profile.")
                return

            # Reward EVERY profile they have
            for profile in user_profiles:
                profile.coins += 250
                profile.roll_refreshes += 1
            
            session.commit()
            print(f"✅ Rewarded {len(user_profiles)} profiles for User {user_id}")

            # Notify the user (DM)
            try:
                discord_user = await self.bot.fetch_user(user_id)
                embed = discord.Embed(title="Thanks for voting! 🗳️", color=discord.Color.green())
                embed.description = "You received **250 Coins** and **1 Roll Refill** in all your servers!"
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass # User has DMs off

        except Exception as e:
            print(f"❌ Error processing vote: {e}")
            session.rollback()
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(VoteCog(bot))