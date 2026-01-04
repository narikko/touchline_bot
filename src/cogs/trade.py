import discord
from discord.ext import commands
from discord import app_commands
from src.database.db import get_session
from src.services.trade_service import TradeService
from src.views.trade_view import TradingView

class TradeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trade", description="Trade players/coins. Use commas for multiple players.")
    @app_commands.describe(offer="The player(s) you are offering (e.g. 'Messi, Neymar')")
    async def trade(self, interaction: discord.Interaction, user: discord.User, offer: str):
        await interaction.response.defer()
        
        if user.id == interaction.user.id or user.bot:
            await interaction.followup.send("Invalid trade partner.", ephemeral=True)
            return

        session = get_session()
        service = TradeService(session)

        try:
            # 1. Validate User A's Offer
            result_a = service.validate_offer(interaction.user.id, interaction.guild_id, offer)
            
            if not result_a["success"]:
                await interaction.followup.send(result_a["message"], ephemeral=True)
                return

            offered_cards_a = result_a["cards"]

            # 2. Create View
            view = TradingView(
                bot=self.bot, 
                user_a=interaction.user, 
                user_b=user, 
                cards_a=offered_cards_a
            )
            
            # 3. Format Display
            offer_names = ", ".join([f"**{c.details.name}**" for c in offered_cards_a])
            
            embed = discord.Embed(title="🤝 Multi-Player Trade", color=discord.Color.gold())
            embed.description = f"{interaction.user.mention} proposes a trade with {user.mention}!"
            
            embed.add_field(name=f"📤 {interaction.user.name}'s Offer", value=offer_names, inline=False)
            embed.add_field(name=f"📥 {user.name}'s Offer", value="*Waiting for offer...*", inline=False)
            embed.set_footer(text="Use the buttons below to add Coins or Counter-offer.")
            
            msg = await interaction.followup.send(content=f"{user.mention}, you have a trade request!", embed=embed, view=view)
            view.message = msg 

        except Exception as e:
            print(f"Error in trade: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(TradeCog(bot))