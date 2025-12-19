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
            result = service.get_tutorial_status(interaction.user.id, interaction.guild_id, page=page)
            
            if result["success"]:
                await interaction.followup.send(embed=result["embed"])
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
                
        except Exception as e:
            print(f"Error in tutorial: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(TutorialCog(bot))