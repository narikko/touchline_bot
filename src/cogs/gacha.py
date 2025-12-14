import discord
from discord.ext import commands
from discord import app_commands
from src.services.gacha_service import GachaService
from src.database.db import get_session

class ClaimView(discord.ui.View):
    def __init__(self, service, guild_id, player_id):
        # Timeout = 60 seconds
        super().__init__(timeout=60)
        self.service = service
        self.guild_id = guild_id
        self.player_id = player_id
        self.message = None 

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
            child.label = "Expired"
            child.style = discord.ButtonStyle.gray
        
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Claim!", style=discord.ButtonStyle.green, emoji="⚽")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Defer the interaction response immediately to prevent "Interaction failed"
        await interaction.response.defer() 
        
        session = get_session()
        service = GachaService(session) # Create new service instance for the interaction

        try:
            # 1. Attempt to claim using the Service
            result = service.claim_card(str(interaction.user.id), self.guild_id, self.player_id)

            if result["success"]:
                # 2. Update UI on success
                card = result["card"]
                player_name = card.details.name # Get the full name from the Card's details relationship
                
                button.disabled = True
                button.label = f"Claimed by {interaction.user.display_name}"
                button.style = discord.ButtonStyle.blurple
                
                # Update the message 
                if interaction.message:
                    await interaction.message.edit(view=self)
                
                # Send a confirmation 
                await interaction.followup.send(
                    f"✅ **{interaction.user.mention}** successfully claimed **{player_name}**!", 
                    ephemeral=False
                )
                self.stop() 
            else:
                # 3. Handle failure 
                await interaction.followup.send(result["message"], ephemeral=True)
        finally:
            session.close()


class GachaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="r", description="Roll for a random soccer player card.")
    async def roll(self, interaction: discord.Interaction):
        # Defer the interaction response immediately for long-running processes
        await interaction.response.defer() 
        
        # 1. Setup Database Session
        session = get_session()
        service = GachaService(session)

        try:
            # 2. Call the Business Logic
            result = service.roll_card(str(interaction.user.id), str(interaction.guild_id), interaction.user.name)

            if not result["success"]:
                await interaction.followup.send(f"❌ {result['message']}")
                return

            player = result["player"]
            
            # 3. Build the Embed
            color = 0xFFD700 if player.rarity == "Legend" else 0xAF0000
            
            embed = discord.Embed(
                title=player.name,
                description=f"**{player.club}**\n{player.nationality}",
                color=color
            )
            
            embed.add_field(name="Position", value=player.positions, inline=True)
            embed.add_field(name="Value", value=f"{player.value} 💎", inline=True)
            
            if player.image_url and player.image_url != "N/A":
                embed.set_image(url=player.image_url)
            
            embed.set_footer(text=f"Rolls: {result['rolls_remaining']} | ID: {player.id}")

            # 4. Handle Response Type
            if result.get("is_duplicate"):
                # A: User rolled a duplicate -> Give Coins
                owner = result['owner_name']
                coins = result['coins_gained']
                
                embed.description += f"\n\n🔒 **Already claimed by {owner}**"
                embed.add_field(name="Duplicate Bonus", value=f"💰 +{coins} Coins", inline=False)
                
                await interaction.followup.send(embed=embed)
            
            else:
                # B: New Card -> Allow Claiming
                embed.description += "\n\n**Claim it before someone else does!**"
                
                # Use interaction.guild_id which is guaranteed to be a string
                view = ClaimView(service, str(interaction.guild_id), player.id)
                message = await interaction.followup.send(embed=embed, view=view)
                
                view.message = message

        except Exception as e:
            await interaction.followup.send("An unexpected error occurred during the roll.")
            print(f"Error in roll slash command: {e}")
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(GachaCog(bot))