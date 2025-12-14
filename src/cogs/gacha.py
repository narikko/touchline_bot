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
        # 1. Defer/Acknowledge the interaction
        await interaction.response.defer() 

        print("DEBUG: Button clicked, processing...")
        
        session = get_session()
        service = GachaService(session) 

        try:
            # 2. Attempt to claim using the Service
            #print(f"DEBUG: Calling claim_card for Player ID: {self.player_id}")
            
            result = service.claim_card(str(interaction.user.id), self.guild_id, self.player_id)

            if result["success"]:
                #print("DEBUG: Result was successful")
                # 3. Handle successful claim
                card = result["card"]
                player_name = card.details.name
                
                # Update button state
                button.disabled = True
                button.label = f"Claimed by {interaction.user.display_name}"
                button.style = discord.ButtonStyle.blurple
                
                # Use EDIT on the FOLLOWUP message
                if interaction.message:
                    await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
                
                # Send confirmation
                await interaction.followup.send(
                    f"✅ **{interaction.user.mention}** successfully claimed **{player_name}**!", 
                    ephemeral=False
                )
                self.stop() 
            else:
                print(f"DEBUG: Result failed - {result['message']}")
                await interaction.followup.send(result["message"], ephemeral=True)

        except Exception as e:
            print(f"CRITICAL ERROR in claim_button: {e}")
            import traceback
            traceback.print_exc() 
            await interaction.followup.send("An error occurred while claiming.", ephemeral=True)
            
        finally:
            #print("DEBUG: Closing session")
            session.close()

class CollectionView(discord.ui.View):
    def __init__(self, service, discord_id, guild_id, username):
        super().__init__(timeout=60)
        self.service = service
        self.discord_id = discord_id
        self.guild_id = guild_id
        self.username = username
        self.page = 1 # Current card index (1-based)

    async def update_embed(self, interaction):
        data = self.service.get_user_collection(
            self.discord_id, 
            self.guild_id, 
            page=self.page, 
            per_page=1
        )
        
        if data["total"] == 0:
            await interaction.response.send_message("You don't have any cards yet!", ephemeral=True)
            return

        # Get the single card from the list
        card = data["cards"][0]
        p = card.details

        # Rarity Color & Emoji
        if p.rarity == "Legend":
            color = 0xFFD700
            icon = "🌟"
        elif p.rarity == "Ultra Rare":
            color = 0x9400D3 
            icon = ""
        else:
            color = 0xAF0000
            icon = ""

        # Build the "Big Card" Embed
        embed = discord.Embed(
            title=f"{icon} {p.name}",
            description=f"**{p.club}**\n{p.nationality}",
            color=color
        )
        
        embed.add_field(name="Rating", value=f"{p.rating} 💎", inline=True)
        embed.add_field(name="Position", value=p.positions, inline=True)
        embed.add_field(name="Rarity", value=p.rarity, inline=True)
        
        # SHOW THE IMAGE
        if p.image_url and p.image_url != "N/A":
            embed.set_image(url=p.image_url)

        # Footer: Card X of Y
        embed.set_footer(text=f"Card {self.page} of {data['total']} | Obtained: {card.obtained_at.strftime('%Y-%m-%d')}")
        
        # Update Button States
        self.children[0].disabled = (self.page == 1) # Previous
        self.children[1].disabled = (self.page == data['total']) # Next
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        await self.update_embed(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        await self.update_embed(interaction)

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

    @app_commands.command(name="collection", description="View your card collection (Gallery Mode).")
    async def collection(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        session = get_session()
        service = GachaService(session)
        
        try:
            # 1. Fetch Page 1
            data = service.get_user_collection(str(interaction.user.id), str(interaction.guild_id), page=1, per_page=1)
            
            if data["total"] == 0:
                await interaction.followup.send("You don't have any cards yet! Type `/r` to start rolling.")
                return

            # 2. Build Initial Embed 
            card = data["cards"][0]
            p = card.details

            if p.rarity == "Legend":
                color = 0xFFD700
                icon = "🌟"
            elif p.rarity == "Ultra Rare":
                color = 0x9400D3 
                icon = ""
            else:
                color = 0xAF0000
                icon = ""

            embed = discord.Embed(
                title=f"{icon} {p.name}",
                description=f"**{p.club}**\n{p.nationality}",
                color=color
            )
            embed.add_field(name="Rating", value=f"{p.rating} 💎", inline=True)
            embed.add_field(name="Position", value=p.positions, inline=True)
            embed.add_field(name="Rarity", value=p.rarity, inline=True)

            if p.image_url and p.image_url != "N/A":
                embed.set_image(url=p.image_url)

            embed.set_footer(text=f"Card 1 of {data['total']} | Obtained: {card.obtained_at.strftime('%Y-%m-%d')}")

            # 3. Create View
            view = CollectionView(service, str(interaction.user.id), str(interaction.guild_id), interaction.user.display_name)
            
            # Disable Prev button initially
            view.children[0].disabled = True
            # Disable Next button if they only have 1 card
            if data['total'] == 1:
                view.children[1].disabled = True

            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error in collection: {e}")
            await interaction.followup.send("Failed to load collection.")
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(GachaCog(bot))