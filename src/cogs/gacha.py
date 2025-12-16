import discord
from discord.ext import commands
from discord import app_commands
from src.services.gacha_service import GachaService
from src.database.db import get_session
from datetime import datetime, timedelta

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

        #print("DEBUG: Button clicked, processing...")
        
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
    def __init__(self, service, discord_id, guild_id, username, target_user_id=None):
        super().__init__(timeout=60)
        self.service = service
        self.discord_id = discord_id
        self.guild_id = guild_id
        self.username = username
        self.target_user_id = target_user_id if target_user_id else discord_id
        self.page = 1 

    async def update_embed(self, interaction):
        data = self.service.get_user_collection(
            self.discord_id, 
            self.guild_id, 
            page=self.page, 
            per_page=1,
            target_user_id=self.target_user_id
        )
        
        if data["total"] == 0:
            await interaction.response.send_message("You don't have any players yet!", ephemeral=True)
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
        
        embed.add_field(name="Value", value=f"{p.rating} 💠", inline=True)
        embed.add_field(name="Position", value=p.positions, inline=True)
        embed.add_field(name="Rarity", value=p.rarity, inline=True)
        
        # SHOW THE IMAGE
        if p.image_url and p.image_url != "N/A":
            embed.set_image(url=p.image_url)

        # Footer: Card X of Y
        embed.set_footer(text=f"Player {self.page} of {data['total']} | Obtained: {card.obtained_at.strftime('%Y-%m-%d')}")
        
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

    @app_commands.command(name="r", description="Roll for a random player.")
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
            embed.add_field(name="Value", value=f"{player.value} 💠", inline=True)
            
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

    @app_commands.command(name="collection", description="View your collection.")
    async def collection(self, interaction: discord.Interaction, user: discord.User = None, page: int = 1):
        await interaction.response.defer()
        
        session = get_session()
        service = GachaService(session)

        target_user = user if user else interaction.user
        target_id_str = str(target_user.id)

        start_page = max(1, page)
        
        try:
            # 1. Fetch Page 1
            data = service.get_user_collection(str(interaction.user.id), str(interaction.guild_id), page=start_page, per_page=1, target_user_id=target_id_str)
            
            if data["total"] == 0:
                await interaction.followup.send("You don't have any players yet! Type `/r` to start rolling.")
                return
            
            if start_page > data["max_page"]:
                start_page = data["max_page"]
                data = service.get_user_collection(
                    str(interaction.user.id), 
                    str(interaction.guild_id), 
                    page=start_page, 
                    per_page=1,
                    target_user_id=target_id_str
                )

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
            embed.add_field(name="Value", value=f"{p.rating} 💠", inline=True)
            embed.add_field(name="Position", value=p.positions, inline=True)
            embed.add_field(name="Rarity", value=p.rarity, inline=True)

            if p.image_url and p.image_url != "N/A":
                embed.set_image(url=p.image_url)

            embed.set_footer(text=f"Player {start_page} of {data['total']} | Obtained: {card.obtained_at.strftime('%Y-%m-%d')}")

            # 3. Create View
            view = CollectionView(service, str(interaction.user.id), str(interaction.guild_id), interaction.user.display_name, target_user_id=target_id_str)
            view.page = start_page

            view.children[0].disabled = (start_page == 1)
            if data['total'] == 1 or start_page == data['total']:
                view.children[1].disabled = True

            await interaction.followup.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error in collection: {e}")
            await interaction.followup.send("Failed to load collection.")
        finally:
            session.close()

    @app_commands.command(name="sell", description="Sell a player for coins.")
    async def sell(self, interaction: discord.Interaction, player_name: str):
        await interaction.response.defer(ephemeral=True) # Ephemeral so others don't see your business
        session = get_session()
        service = GachaService(session)
        
        try:
            result = service.sell_player(str(interaction.user.id), str(interaction.guild_id), player_name)
            
            if result["success"]:
                await interaction.followup.send(f"Sold **{result['player_name']}** for **{result['coins']}** 💠.\n New Balance: {result['new_balance']} 💠", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="sort", description="Sort your collection by highest value.")
    async def sort(self, interaction: discord.Interaction):
        await interaction.response.defer()
        session = get_session()
        service = GachaService(session)
        
        try:
            result = service.sort_collection(str(interaction.user.id), str(interaction.guild_id))
            
            if result["success"]:
                await interaction.followup.send(f"Collection sorted! Your **{result['count']}** cards are now ordered by Value (Highest to Lowest). Check `/collection`.")
            else:
                await interaction.followup.send(f"❌ {result['message']}")
        finally:
            session.close()

    @app_commands.command(name="move", description="Move a player to a specific page number.")
    async def move(self, interaction: discord.Interaction, player_name: str, page: int):
        await interaction.response.defer()
        session = get_session()
        service = GachaService(session)
        
        try:
            result = service.move_player(str(interaction.user.id), str(interaction.guild_id), player_name, page)
            
            if result["success"]:
                await interaction.followup.send(f"Moved **{result['player']}** to Page **{result['page']}**.")
            else:
                await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):
        await interaction.response.defer()
        session = get_session()
        service = GachaService(session)

        try:
            result = service.claim_daily(str(interaction.user.id), str(interaction.guild_id), interaction.user.name)

            if result["success"]:
                color = discord.Color.gold() if "Lucky" in result["bonus_type"] else discord.Color.green()
                embed = discord.Embed(title=result["bonus_type"], color=color)

                desc = f"You received **{result['total_reward']}** 💠!"

                desc += f"\n\nNew Balance: **{result['new_balance']}** 💠"
                embed.description = desc
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(result["message"], ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="setclub", description="Set your favorite football club.")
    async def setclub(self, interaction: discord.Interaction, club_name: str):
        await interaction.response.defer()
        session = get_session()
        service = GachaService(session)
        
        try:
            result = service.set_favorite_club(str(interaction.user.id), str(interaction.guild_id), club_name)
            
            if result["success"]:
                # Success Case
                await interaction.followup.send(f"Your favorite club has been set to **{result['club']}**!")
            
            elif result["reason"] == "multiple":
                # Multiple Matches Case
                matches_str = "\n".join([f"• {c}" for c in result["matches"]])
                msg = f"🔍 Found multiple clubs matching **'{club_name}'**. Please be more specific:\n\n{matches_str}"
                
                # Prevent message from being too long
                if len(msg) > 1900: 
                    msg = msg[:1900] + "\n... (too many matches, try being more specific)"
                
                await interaction.followup.send(msg, ephemeral=True)
                
            else:
                # No Matches Case
                await interaction.followup.send(f"❌ Club **'{club_name}'** not found in database.", ephemeral=True)
                
        except Exception as e:
            print(f"Error in setclub: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

    @app_commands.command(name="profile", description="View your profile.")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        session = get_session()
        service = GachaService(session)

        try:
            user = service.get_or_create_user(str(interaction.user.id), str(interaction.guild_id), interaction.user.name)
            
            # Fetch collection count
            # We can use the service helper if you added it, or just a quick query
            from src.database.models import Card
            total_cards = session.query(Card).filter_by(user_id=user.id).count()
            
            # Rolls Display
            if user.rolls_remaining >= service.MAX_ROLLS:
                rolls_display = f"**{user.rolls_remaining}** (Max)"
            else:
                roll_timer = service.get_next_reset_time(user.last_roll_reset, service.ROLL_RESET_MINUTES)
                rolls_display = f"**{user.rolls_remaining}** left\nRefill: **{roll_timer}**"

            # Claims Display
            if user.claims_remaining >= service.MAX_CLAIMS:
                claims_display = "✅ **Ready!**"
            else:
                claim_timer = service.get_next_reset_time(user.last_claim_reset, service.CLAIM_RESET_MINUTES)
                claims_display = f"⏳ **{claim_timer}**"

            # Daily Display
            now = datetime.utcnow()
            if user.last_daily_claim:
                next_daily = user.last_daily_claim + timedelta(hours=service.DAILY_RESET_HOURS)
                if now >= next_daily:
                    daily_display = "✅ **Ready!**"
                else:
                    diff = next_daily - now
                    hrs, rem = divmod(int(diff.total_seconds()), 3600)
                    mins, _ = divmod(rem, 60)
                    daily_display = f"⏳ **{hrs}h {mins}m**"
            else:
                 daily_display = "✅ **Ready!**"

            # Favorite Club
            fav_club = f"**{user.favorite_club}**" if user.favorite_club else "Not set (`/setclub`)"

            # --- 2. BUILD EMBED ---
            embed = discord.Embed(
                title=f"📋 {interaction.user.display_name}'s Profile",
                color=discord.Color.dark_blue()
            )
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)
            
            # Timers Row
            embed.add_field(name="✋ Claim", value=claims_display, inline=True)
            embed.add_field(name="🎰 Rolls", value=rolls_display, inline=True)
            embed.add_field(name="🌞 Daily", value=daily_display, inline=True)

            # Info Row
            embed.add_field(name="❤️ Favorite Club", value=fav_club, inline=False)
            embed.add_field(name="🗃️ Collection", value=f"**{total_cards}** Players", inline=True)
            
            # Currency Row
            embed.add_field(name="💠 Coins", value=f"**{user.coins:,}**", inline=False)

            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in profile: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("Failed to load profile.")
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(GachaCog(bot))