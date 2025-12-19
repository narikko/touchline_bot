import discord
from src.database.db import get_session
from src.services.match_service import MatchService

class MatchChallengeView(discord.ui.View):
    def __init__(self, challenger, opponent, wager):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.wager = wager
        self.accepted = False

    @discord.ui.button(label="Accept Match", style=discord.ButtonStyle.green, emoji="⚽")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("This challenge is not for you!", ephemeral=True)
            return

        # Check balances
        session = get_session()
        service = MatchService(session)
        
        try:
            # Verify balances again before starting
            c_data = service.get_team_power(self.challenger.id, interaction.guild_id)
            o_data = service.get_team_power(self.opponent.id, interaction.guild_id)
            
            if c_data["user"].coins < self.wager:
                await interaction.response.send_message(f"{self.challenger.mention} is broke! Match cancelled.", ephemeral=True)
                self.stop()
                return
                
            if o_data["user"].coins < self.wager:
                await interaction.response.send_message("You don't have enough coins!", ephemeral=True)
                return

            self.accepted = True
            self.stop() # Stop listening, let the Cog take over
            await interaction.response.defer() # Acknowledge the click
            
        finally:
            session.close()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id and interaction.user.id != self.challenger.id:
            return
        
        await interaction.response.send_message("Match declined.", ephemeral=True)
        self.stop()