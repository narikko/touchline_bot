import discord
from discord.ext import commands
from discord import app_commands
from src.database.db import get_session
from src.services.tutorial_service import TutorialService

class TutorialCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tutorial", description="View your current tutorial progress.")
    @app_commands.describe(page="View a specific tutorial page (cannot view locked pages).")
    async def tutorial(self, interaction: discord.Interaction, page: int = None):
        await interaction.response.defer()
        session = get_session()
        service = TutorialService(session)
        
        try:
            result = service.get_tutorial_status(interaction.user.id, interaction.guild_id, interaction.user.name, page=page)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"])
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
                
        except Exception as e:
            print(f"Error in tutorial: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="claim_tutorial_rewards", description="Claim tutorial rewards completed on other servers.")
    async def claim_rewards(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        session = get_session()
        service = TutorialService(session)
        
        try:
            result = service.sync_rewards(interaction.user.id, interaction.guild_id)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"])
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
                
        except Exception as e:
            print(f"Error in claim_rewards: {e}")
            await interaction.followup.send("An error occurred while syncing rewards.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(TutorialCog(bot))