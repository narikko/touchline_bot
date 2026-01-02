import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
from src.database.db import get_session
from src.database.models import User

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View the complete list of commands.")
    async def index(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Manager's Handbook (Index)",
            description="Here is every command available to you.",
            color=discord.Color.teal()
        )

        # 1. Gacha & Collection (Added /freeclaim)
        embed.add_field(
            name="🗃️ Scouting & Collection",
            value=(
                "`/r` - Roll for a new player.\n"
                "`/daily` - Claim daily rewards.\n"
                "`/freeclaim` - Use a free claim token.\n"  # <-- Added
                "`/collection` - View your players.\n"
                "`/view [name]` - View details of a specific card.\n"
                "`/sell [name]` - Sell a player for coins.\n"
                "`/sort` - Sort collection by rating.\n"
                "`/shortlist` - Manage your wishlist notifications.\n"
                "`/setclub` - Set your favorite team."
            ),
            inline=False
        )

        # 2. Social & Rewards (NEW SECTION for Referrals)
        embed.add_field(
            name="🤝 Social & Rewards",
            value=(
                "`/invite` - Get the link to add Touchline to a server.\n"
                "`/refer [user]` - Redeem a referral reward (1000 Coins + 2 Tickets).\n"
                "`/use_refresh` - Use a ticket to instantly refill your rolls.\n"
                "`/claim_tutorial_rewards` - Claim tutorial rewards completed on other servers."
            ),
            inline=False
        )

        # 3. Team Management
        embed.add_field(
            name="⚽ Team Management",
            value=(
                "`/team view` - See your Starting XI.\n"
                "`/team set [pos] [name]` - Add a player to your team.\n"
                "`/team bench [name]` - Remove a player from your team.\n"
                "`/team rewards` - Check Team OVL milestones.\n"
                "`/team rename` - Change your club's name."
            ),
            inline=False
        )

        # 4. Economy & Market
        embed.add_field(
            name="💰 Economy & Market",
            value=(
                "`/market add` - List a player for profit (wait time).\n"
                "`/market view` - Check status of your listed player.\n"
                "`/trade [user] [card]` - Swap players with another user.\n"
                "`/upgrades` - Buy club upgrades (Stadium, Scout, etc.)."
            ),
            inline=False
        )

        # 5. Gameplay
        embed.add_field(
            name="🏆 Gameplay",
            value=(
                "`/match [user] [wager]` - Challenge someone to a match.\n"
                "`/profile` - View your stats and timers.\n"
                "`/tutorial` - Check your progress."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Get the link to add Touchline to your server!")
    async def invite(self, interaction: discord.Interaction):
        # Replace CLIENT_ID with your actual Bot ID from Developer Portal
        invite_url = "https://discord.com/oauth2/authorize?client_id=1132170181012115556&permissions=378944&integration_type=0&scope=bot+applications.commands"
        
        embed = discord.Embed(title="Bring Touchline to your Club! ⚽", color=0x00ff00)
        embed.description = (
            "**Help your friends start their managerial career!**\n\n"
            "Tell them to use **/refer user:@You** once they join.\n"
            "🎁 **Both of you will receive:**\n"
            "💰 **1,000 Coins**\n"
            "🎟️ **2x Roll Refreshes** (Instant Refills!)"
        )
        
        view = discord.ui.View()
        button = discord.ui.Button(label="Add to Server", url=invite_url, style=discord.ButtonStyle.link)
        view.add_item(button)
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="refer", description="Enter the friend who invited you to get rewards!")
    @app_commands.describe(friend="The veteran manager who invited you")
    async def refer(self, interaction: discord.Interaction, friend: discord.User):
        session = get_session()
        
        try:
            # --- SECURITY CHECK: 7-Day Account Age ---
            account_age = datetime.now(timezone.utc) - interaction.user.created_at
            if account_age.days < 7:
                await interaction.response.send_message(
                    "🛑 **Security Alert:** Your Discord account is too new!\n"
                    "To prevent bot farming, you must have an account older than **7 days** to use referrals.",
                    ephemeral=True
                )
                return

            # --- VALIDATION CHECKS ---
            # 1. Self-referral
            if friend.id == interaction.user.id:
                await interaction.response.send_message("❌ You cannot refer yourself!", ephemeral=True)
                return
            
            # 2. Bot referral
            if friend.bot:
                await interaction.response.send_message("❌ You cannot refer a bot!", ephemeral=True)
                return

            # 3. Get Players from DB
            # Note: You might need your specific 'get_user' helper function here if you have one
            new_player = session.query(User).filter_by(discord_id=str(interaction.user.id)).first()
            if not new_player:
                # If they haven't started yet, maybe create them or tell them to run /tutorial
                await interaction.response.send_message("❌ Please run **/tutorial** to create your team first!", ephemeral=True)
                return

            veteran = session.query(User).filter_by(discord_id=str(friend.id)).first()
            if not veteran:
                await interaction.response.send_message(f"❌ **{friend.name}** hasn't started playing Touchline yet!", ephemeral=True)
                return

            # 4. Check if already redeemed
            if new_player.redeemed_referral:
                await interaction.response.send_message("❌ You have already redeemed a referral code!", ephemeral=True)
                return

            # --- GIVE REWARDS ---
            COIN_REWARD = 1000
            REFRESH_REWARD = 2

            # Give to New Player
            new_player.coins += COIN_REWARD
            new_player.roll_refreshes += REFRESH_REWARD
            new_player.redeemed_referral = True  # Mark as used!

            # Give to Veteran
            veteran.coins += COIN_REWARD
            veteran.roll_refreshes += REFRESH_REWARD
            
            session.commit()

            # --- SUCCESS MESSAGE ---
            embed = discord.Embed(title="🤝 Scouting Successful!", color=0xFFD700)
            embed.description = (
                f"**{interaction.user.name}** honored **{friend.name}**'s invite!\n\n"
                f"**Rewards for Both:**\n"
                f"💰 +{COIN_REWARD} Coins\n"
                f"🎟️ +{REFRESH_REWARD} Roll Refreshes"
            )
            embed.set_footer(text="Use /use_refresh to refill your rolls!")
            await interaction.response.send_message(embed=embed)

        except Exception as e:
            print(f"Error in refer: {e}")
            await interaction.response.send_message("❌ An error occurred processing the referral.", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="use_refresh", description="Use a ticket to instantly refill your rolls!")
    async def use_refresh(self, interaction: discord.Interaction):
        session = get_session()
        try:
            user = session.query(User).filter_by(discord_id=str(interaction.user.id)).first()
            if not user:
                await interaction.response.send_message("❌ Run /tutorial first!", ephemeral=True)
                return

            # 1. Check Inventory
            if user.roll_refreshes <= 0:
                await interaction.response.send_message(
                    "❌ You don't have any Refresh Tickets!\n"
                    "Invite friends with **/invite** to earn more.", 
                    ephemeral=True
                )
                return

            # 2. Check if they are already full (Prevent Waste)
            # using 'rolls_remaining' based on your screenshot
            if user.rolls_remaining >= user.max_rolls:
                await interaction.response.send_message(
                    f"❌ Your rolls are already full (**{user.rolls_remaining}/{user.max_rolls}**)! \nSave your ticket for later.", 
                    ephemeral=True
                )
                return

            # 3. Create the Confirmation View
            embed = discord.Embed(
                title="🎟️ Use Refresh Ticket?",
                description=(
                    f"You have **{user.roll_refreshes}** tickets.\n"
                    f"This will restore your rolls to **{user.max_rolls}/{user.max_rolls}**."
                ),
                color=discord.Color.blue()
            )

            # Define the Buttons
            class ConfirmView(discord.ui.View):
                def __init__(self, db_session, db_user):
                    super().__init__(timeout=30)
                    self.session = db_session
                    self.user = db_user
                    self.value = None

                @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    # Re-check inventory just in case
                    if self.user.roll_refreshes <= 0:
                        await interaction.response.send_message("❌ Error: Ticket already used.", ephemeral=True)
                        return
                    
                    # --- EXECUTE LOGIC ---
                    self.user.roll_refreshes -= 1
                    self.user.rolls_remaining = self.user.max_rolls
                    self.user.last_roll_reset = datetime.utcnow()
                    self.session.commit()
                    
                    await interaction.response.edit_message(
                        content=f"✅ **Success!** Used 1 Ticket. Rolls refilled to **{self.user.max_rolls}**! ⚽", 
                        embed=None, 
                        view=None
                    )
                    self.stop()

                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await interaction.response.edit_message(content="❌ Cancelled.", embed=None, view=None)
                    self.stop()

            # Send the confirmation
            view = ConfirmView(session, user)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            print(f"Error in use_refresh: {e}")
            await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            session.close() # Close session if error

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))