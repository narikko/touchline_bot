import discord
from src.database.db import get_session
from src.services.trade_service import TradeService

class TradeOfferModal(discord.ui.Modal, title="Make your Counter-Offer"):
    def __init__(self, view, user_b_discord_id, guild_id):
        super().__init__()
        self.trade_view = view
        self.user_b_discord_id = user_b_discord_id
        self.guild_id = guild_id

    player_name = discord.ui.TextInput(
        label="Player Name",
        placeholder="Type the exact name of the player...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        session = get_session()
        service = TradeService(session)
        
        try:
            # Check if this player exists in User B's collection
            card = service.find_card_for_trade(self.user_b_discord_id, self.guild_id, self.player_name.value)
            
            if not card:
                await interaction.followup.send("❌ Card not found, in Starting XI, or on Market.", ephemeral=True)
                return

            # Update View State
            self.trade_view.card_b_id = card.id
            self.trade_view.card_b_name = card.details.name
            
            await self.trade_view.update_embed(interaction)
            await interaction.followup.send(f"You offered **{card.details.name}**!", ephemeral=True)
            
        finally:
            session.close()

class TradingView(discord.ui.View):
    def __init__(self, bot, user_a, user_b, card_a_id, card_a_name):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_a = user_a
        self.user_b = user_b
        
        self.card_a_id = card_a_id
        self.card_a_name = card_a_name
        
        self.card_b_id = None
        self.card_b_name = "Waiting for offer..."
        
        self.a_accepted = False
        self.b_accepted = False
        self.message = None

        # IMPORTANT: Initialize buttons immediately!
        self._update_buttons()

    def _update_buttons(self):
        """Helper to refresh buttons based on current state."""
        self.clear_items()
        
        # Button: Counter Offer (Visible if B hasn't accepted yet)
        if not self.b_accepted:
             offer_btn = discord.ui.Button(label="Make/Change Offer", style=discord.ButtonStyle.blurple, emoji="📤")
             offer_btn.callback = self.offer_callback
             self.add_item(offer_btn)
        
        # Button: Confirm (Only if BOTH sides have an item)
        if self.card_b_id:
            confirm_label = "Confirm Trade"
            style = discord.ButtonStyle.green
            
            # If both clicked, show processing state visually
            if self.a_accepted and self.b_accepted: 
                confirm_label = "Processing..."
                style = discord.ButtonStyle.grey
            
            accept_btn = discord.ui.Button(label=confirm_label, style=style, emoji="✅")
            accept_btn.callback = self.accept_callback
            self.add_item(accept_btn)
            
        # Button: Cancel (Always visible)
        cancel_btn = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red)
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)

    async def update_embed(self, interaction):
        embed = discord.Embed(title="🤝 Trade Desk", color=discord.Color.gold())
        
        icon_a = "✅" if self.a_accepted else "⏳"
        embed.add_field(name=f"{self.user_a.display_name}", value=f"Offer: **{self.card_a_name}**\nStatus: {icon_a}", inline=True)
        
        embed.add_field(name="vs", value="↔️", inline=True)
        
        icon_b = "✅" if self.b_accepted else "⏳"
        embed.add_field(name=f"{self.user_b.display_name}", value=f"Offer: **{self.card_b_name}**\nStatus: {icon_b}", inline=True)

        # Refresh buttons state logic
        self._update_buttons()

        if interaction.message:
            await interaction.message.edit(embed=embed, view=self)
        elif self.message:
            await self.message.edit(embed=embed, view=self)

    async def offer_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_b.id:
            await interaction.response.send_message("Only the target user can make a counter-offer!", ephemeral=True)
            return
        await interaction.response.send_modal(TradeOfferModal(self, self.user_b.id, interaction.guild.id))

    async def accept_callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.user_a.id:
            self.a_accepted = not self.a_accepted
        elif interaction.user.id == self.user_b.id:
            self.b_accepted = not self.b_accepted
        else:
            await interaction.response.send_message("You are not part of this trade.", ephemeral=True)
            return

        await interaction.response.defer()

        # If Both Accepted -> EXECUTE
        if self.a_accepted and self.b_accepted:
            session = get_session()
            service = TradeService(session) 
            try:
                result = service.execute_trade(self.card_a_id, self.card_b_id)
                
                if result["success"]:
                    self.stop()
                    final_embed = discord.Embed(
                        title="✅ Trade Completed!",
                        description=f"{self.user_a.mention} traded **{self.card_a_name}** for {self.user_b.mention}'s **{self.card_b_name}**.",
                        color=discord.Color.green()
                    )
                    if self.message:
                        await self.message.edit(embed=final_embed, view=None)
                    
                    # --- TUTORIAL HOOK (7_trade) ---
                    try:
                        from src.services.tutorial_service import TutorialService
                        tut_service = TutorialService(session)
                        
                        # 1. Credit User A (The Proposer)
                        msg_a = tut_service.complete_step(self.user_a.id, interaction.guild.id, "7_trade")
                        
                        # 2. Credit User B (The Accepter)
                        msg_b = tut_service.complete_step(self.user_b.id, interaction.guild.id, "7_trade")

                        # 3. Send Notifications
                        if msg_a:
                            await interaction.channel.send(f"{self.user_a.mention} {msg_a}")
                        if msg_b:
                            await interaction.channel.send(f"{self.user_b.mention} {msg_b}")

                    except Exception as e:
                        print(f"Tutorial Error in Trade: {e}")
                    # -------------------------------
                    
                else:
                    await interaction.followup.send(f"❌ Trade Failed: {result['message']}", ephemeral=True)
                    self.a_accepted = False
                    self.b_accepted = False
                    await self.update_embed(interaction)
            finally:
                session.close()
        else:
            await self.update_embed(interaction)

    async def cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in [self.user_a.id, self.user_b.id]:
            return
        self.stop()
        if interaction.message:
            await interaction.message.edit(content="❌ Trade Cancelled.", embed=None, view=None)