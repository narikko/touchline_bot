import discord
from discord.ext import commands
from discord import app_commands
from src.database.db import get_session
from src.services.transfer_service import TransferService

class MarketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="Open the Transfer Market menu.")
    @app_commands.describe(action="Add, Remove, or View status")
    @app_commands.choices(action=[
        app_commands.Choice(name="📋 View Status", value="view"),
        app_commands.Choice(name="➕ Add Player", value="add"),
        app_commands.Choice(name="➖ Remove Player", value="remove"),
    ])
    async def market(self, interaction: discord.Interaction, action: str, player_name: str = None):
        await interaction.response.defer()
        session = get_session()
        service = TransferService(session)

        try:
            # 1. ADD PLAYER
            if action == "add":
                if not player_name:
                    await interaction.followup.send("❌ You must specify a player name to add! Example: `/market add [player]`", ephemeral=True)
                    return

                result = service.add_to_market(str(interaction.user.id), str(interaction.guild_id), player_name)
                
                if result["success"]:
                    embed = discord.Embed(title="✅ Player Listed", color=discord.Color.green())
                    embed.description = (
                        f"**{result['player']}** is now on the Transfer Market.\n"
                        f"⏳ Wait Time: **{result['hours']} hours**\n"
                        f"💰 Sale Value: **{result['value']:,}** 💠"
                    )
                    await interaction.followup.send(embed=embed)

                    # --- TUTORIAL HOOK: 7_tm_add ---
                    try:
                        from src.services.tutorial_service import TutorialService
                        tut_service = TutorialService(session)
                        tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "7_tm_add")
                        if tut_msg: await interaction.channel.send(f"{interaction.user.mention}\n{tut_msg}")
                    except Exception as e: print(f"Tutorial Error: {e}")
                    # -------------------------------

                else:
                    await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)

            # 2. REMOVE PLAYER
            elif action == "remove":
                result = service.remove_from_market(str(interaction.user.id), str(interaction.guild_id))
                if result["success"]:
                    await interaction.followup.send(f"✅ {result['message']}")
                else:
                    await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)

            # 3. VIEW STATUS (Checks timer automatically)
            else:
                status = service.check_transfer_status(str(interaction.user.id), str(interaction.guild_id))
                
                if status["status"] == "completed":
                    embed = discord.Embed(title="Transfer Complete!", color=discord.Color.gold())
                    embed.description = (
                        f"**{status['player']}** has been sold!\n"
                        f"You received: **{status['value']:,}** 💠"
                    )
                    await interaction.followup.send(embed=embed)

                    # --- TUTORIAL HOOK: 7_tm_sold ---
                    try:
                        from src.services.tutorial_service import TutorialService
                        tut_service = TutorialService(session)
                        tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "7_tm_sold")
                        if tut_msg: await interaction.channel.send(f"{interaction.user.mention}\n{tut_msg}")
                    except Exception as e: print(f"Tutorial Error: {e}")
                    # --------------------------------
                    
                elif status["status"] == "waiting":
                    embed = discord.Embed(title="⏳ Transfer in Progress", color=discord.Color.blue())
                    embed.add_field(name="Player", value=status["player"])
                    embed.add_field(name="Expected Return", value=f"{status['value']:,} 💠")
                    embed.add_field(name="Time Remaining", value=status["time_left"])
                    await interaction.followup.send(embed=embed)
                    
                else:
                    embed = discord.Embed(
                        title="Transfer Market", 
                        description="Your transfer list is empty.\nUse `/market add [player]` to list a card for profit!",
                        color=discord.Color.dark_grey()
                    )
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in market command: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(MarketCog(bot))