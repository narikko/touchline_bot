import discord
from src.database.db import get_session
from src.services.trade_service import TradeService

# --- MODAL FOR USER B TO TYPE THEIR OFFER ---
class CounterOfferModal(discord.ui.Modal, title="Make Counter Offer"):
    offer_input = discord.ui.TextInput(
        label="Player Names (Max 3)",
        placeholder="e.g. Haaland, De Bruyne",
        required=True
    )

    def __init__(self, view_ref):
        super().__init__()
        self.view_ref = view_ref # Reference to the main View

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        session = get_session()
        service = TradeService(session)
        
        # Validate User B's input
        result = service.validate_offer(interaction.user.id, interaction.guild_id, self.offer_input.value)
        session.close()

        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        # Save User B's cards to the view
        # We store the objects temporarily to display names
        self.view_ref.cards_b = result["cards"]
        self.view_ref.accepted_a = False # Reset accept status if offer changes
        self.view_ref.accepted_b = True  # Auto-accept their own offer
        
        await interaction.followup.send("✅ Offer updated!", ephemeral=True)
        await self.view_ref.update_embed(interaction)


# --- MAIN VIEW ---
class TradingView(discord.ui.View):
    def __init__(self, bot, user_a, user_b, cards_a):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_a = user_a
        self.user_b = user_b
        
        self.cards_a = cards_a # List of Card Objects
        self.cards_b = []      # Starts empty
        
        self.accepted_a = True # User A accepted by starting the trade
        self.accepted_b = False
        self.message = None

    async def update_embed(self, interaction):
        names_a = ", ".join([f"**{c.details.name}**" for c in self.cards_a])
        names_b = ", ".join([f"**{c.details.name}**" for c in self.cards_b]) if self.cards_b else "*None*"

        embed = discord.Embed(title="🤝 Trade Negotiation", color=discord.Color.blue())
        
        # Visual Indicators for Status
        status_a = "✅ Ready" if self.accepted_a else "⏳ Thinking..."
        status_b = "✅ Ready" if self.accepted_b else "⏳ Thinking..."

        embed.add_field(name=f"{self.user_a.name} ({status_a})", value=names_a, inline=False)
        embed.add_field(name=f"⬇️ ⬆️", value="vs", inline=False)
        embed.add_field(name=f"{self.user_b.name} ({status_b})", value=names_b, inline=False)
        
        # Check if complete
        if self.accepted_a and self.accepted_b:
             embed.color = discord.Color.green()
             embed.set_footer(text="Both parties accepted! Processing...")
             
             # Disable buttons visual only (logic handled below)
             for item in self.children: item.disabled = True
             
             if self.message:
                 await self.message.edit(embed=embed, view=self)
             elif interaction.message:
                 await interaction.message.edit(embed=embed, view=self)

             # Execute Trade
             session = get_session()
             service = TradeService(session)
             
             ids_a = [c.id for c in self.cards_a]
             ids_b = [c.id for c in self.cards_b]
             
             res = service.execute_multi_trade(ids_a, ids_b)
             
             if res["success"]:
                 embed.title = "✅ Trade Completed!"
                 embed.description = f"Owners swapped successfully.\n\n{names_a} ↔ {names_b}"
                 
                 # --- TUTORIAL HOOK ---
                 try:
                     from src.services.tutorial_service import TutorialService
                     tut = TutorialService(session)
                     msg_a = tut.complete_step(self.user_a.id, interaction.guild.id, "7_trade")
                     msg_b = tut.complete_step(self.user_b.id, interaction.guild.id, "7_trade")
                     
                     if msg_a: await interaction.channel.send(f"{self.user_a.mention} {msg_a}")
                     if msg_b: await interaction.channel.send(f"{self.user_b.mention} {msg_b}")
                 except Exception as e:
                     print(f"Tutorial Hook Error: {e}")
                 # ---------------------
             else:
                 embed.title = "❌ Trade Failed"
                 embed.description = res["message"]
                 embed.color = discord.Color.red()
             
             session.close()

             if self.message:
                 await self.message.edit(embed=embed, view=None)
             elif interaction.message:
                 await interaction.message.edit(embed=embed, view=None)
             return

        # Normal Update
        if self.message:
            await self.message.edit(embed=embed, view=self)
        elif interaction.message:
            await interaction.message.edit(embed=embed, view=self)


    @discord.ui.button(label="Make Offer / Counter", style=discord.ButtonStyle.primary)
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_b.id:
            return await interaction.response.send_message("Only the trade partner can add cards!", ephemeral=True)
        
        # Open Modal for User B to type names
        await interaction.response.send_modal(CounterOfferModal(self))

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_a.id:
            self.accepted_a = not self.accepted_a # Toggle
        elif interaction.user.id == self.user_b.id:
            if not self.cards_b:
                return await interaction.response.send_message("You must offer at least one player!", ephemeral=True)
            self.accepted_b = not self.accepted_b # Toggle
        else:
            return await interaction.response.send_message("You are not part of this trade.", ephemeral=True)

        await interaction.response.defer()
        await self.update_embed(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_a.id, self.user_b.id]:
             return await interaction.response.send_message("You cannot cancel this trade.", ephemeral=True)
        
        embed = discord.Embed(title="❌ Trade Cancelled", description=f"Cancelled by {interaction.user.mention}", color=discord.Color.red())
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)