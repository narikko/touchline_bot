import discord
from discord import app_commands
from discord.ext import commands
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
        
        # Start the server in the background
        self.bot.loop.create_task(self.start_webhook())

    async def start_webhook(self):
        """Starts the webhook server on port 5000."""
        try:
            await self.webhook_manager.run(5000)
            print("[System] Top.gg Webhook running on port 5000")
        except Exception as e:
            print(f"[Error] Failed to start webhook: {e}")

    # --- NEW: The /vote Command ---
    @app_commands.command(name="vote", description="Get the link to vote and earn rewards.")
    async def vote(self, interaction: discord.Interaction):
        # Generate the dynamic link for your bot
        vote_link = f"https://top.gg/bot/{self.bot.user.id}/vote"

        embed = discord.Embed(title="Vote Rewards", color=discord.Color.blue())
        embed.description = (
            "Vote for us on Top.gg to support the bot and earn rewards!\n\n"
            "**You will receive:**\n"
            "• 250 Coins\n"
            "• 1 Roll Refill\n\n"
            "You can vote once every 12 hours."
        )

        # Create a button that links directly to the page
        view = discord.ui.View()
        button = discord.ui.Button(label="Vote on Top.gg", url=vote_link, style=discord.ButtonStyle.link)
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    # --- Webhook Listener ---
    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        """Triggered automatically when someone votes on Top.gg"""
        user_id = int(data["user"])
        print(f"[Vote] Received from User ID: {user_id}")
        
        session = get_session()
        try:
            # Get ALL instances of this user across all servers
            user_profiles = session.query(User).filter_by(discord_id=str(user_id)).all()
            
            if not user_profiles:
                print(f"[Vote] User {user_id} voted but has no profile in database.")
                return

            # Reward EVERY profile they have
            for profile in user_profiles:
                profile.coins += 250
                profile.roll_refreshes += 1
            
            session.commit()
            print(f"[Vote] Rewarded {len(user_profiles)} profiles for User {user_id}")

            # Notify the user (DM) - Clean text, no emojis
            try:
                discord_user = await self.bot.fetch_user(user_id)
                embed = discord.Embed(title="Vote Successful", color=discord.Color.green())
                embed.description = "Thank you for voting. You have received **250 Coins** and **1 Roll Refill** in all your servers."
                await discord_user.send(embed=embed)
            except discord.Forbidden:
                pass # User has DMs off

        except Exception as e:
            print(f"[Error] Processing vote failed: {e}")
            session.rollback()
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(VoteCog(bot))