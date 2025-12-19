import discord
from src.database.db import get_session
from src.services.gacha_service import GachaService

class FreeClaimView(discord.ui.View):
    def __init__(self, user_id, guild_id):
        super().__init__(timeout=60)
        self.user_id = str(user_id)
        self.guild_id = str(guild_id)
        self.value = None # True if confirmed, False if cancelled

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the user who typed the command to click
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This confirmation is not for you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yes, use Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Disable buttons immediately to prevent double clicks
        for child in self.children:
            child.disabled = True
        
        # Create a FRESH session for the transaction
        session = get_session()
        service = GachaService(session)
        
        try:
            result = service.use_free_claim(self.user_id, self.guild_id)
            
            if result["success"]:
                embed = discord.Embed(
                    title="🎫 Free Claim Used!",
                    description=(
                        f"You used a **Free Claim ticket**.\n"
                        f"✅ **Claims Available:** {result['claims_remaining']}\n"
                        f"🎫 **Tickets Remaining:** {result['free_claims_left']}"
                    ),
                    color=discord.Color.green()
                )
                embed.set_footer(text="Use /claim (or /r) to grab a card now!")
                await interaction.edit_original_response(content=None, embed=embed, view=None)
            else:
                await interaction.edit_original_response(content=f"❌ {result['message']}", view=None)
                
        except Exception as e:
            print(f"Error in free claim confirm: {e}")
            await interaction.edit_original_response(content="❌ An error occurred processing the ticket.", view=None)
        finally:
            session.close()
            self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.edit_original_response(content="❌ Free Claim cancelled.", embed=None, view=None)
        self.stop()