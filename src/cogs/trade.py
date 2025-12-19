import discord
from discord.ext import commands
from discord import app_commands
from src.database.db import get_session
from src.services.trade_service import TradeService # <--- Updated Import
from src.views.trade_view import TradingView

class TradeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trade", description="Start a trade with another player.")
    async def trade(self, interaction: discord.Interaction, user: discord.User, offer_player: str):
        await interaction.response.defer()
        
        if user.id == interaction.user.id:
            await interaction.followup.send("You can't trade with yourself!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.followup.send("You can't trade with a bot!", ephemeral=True)
            return

        session = get_session()
        service = TradeService(session) # <--- USING NEW SERVICE

        try:
            # 1. Validate User A's Offer immediately
            card_a = service.find_card_for_trade(interaction.user.id, interaction.guild_id, offer_player)
            
            if not card_a:
                await interaction.followup.send(f"❌ Could not find **{offer_player}** in your collection (or it's in your Team/Market).", ephemeral=True)
                return

            # 2. Init the View
            view = TradingView(
                self.bot, 
                user_a=interaction.user, 
                user_b=user, 
                card_a_id=card_a.id, 
                card_a_name=card_a.details.name
            )
            
            # 3. Send Initial Message
            embed = discord.Embed(title="🤝 Trade Proposal", color=discord.Color.gold())
            embed.description = f"{interaction.user.mention} wants to trade with {user.mention}!"
            embed.add_field(name=f"{interaction.user.display_name}'s Offer", value=f"**{card_a.details.name}**", inline=True)
            embed.add_field(name=f"{user.display_name}'s Offer", value="*Waiting for offer...*", inline=True)
            
            msg = await interaction.followup.send(content=f"{user.mention}", embed=embed, view=view)
            view.message = msg 

        except Exception as e:
            print(f"Error in trade command: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(TradeCog(bot))