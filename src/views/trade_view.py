import discord
from src.database.db import get_session
from src.services.trade_service import TradeService

# --- MODAL FOR ADDING COINS ---
class AddCoinsModal(discord.ui.Modal, title="Add Coins to Trade"):
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="e.g. 5000",
        required=True,
        min_length=1,
        max_length=7
    )

    def __init__(self, view_ref, is_user_a):
        super().__init__()
        self.view_ref = view_ref
        self.is_user_a = is_user_a # Boolean: True if User A, False if User B

    async def on_submit(self, interaction: discord.Interaction):
        try:
            val = int(self.amount.value)
            if val < 0: raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Please enter a valid positive number.", ephemeral=True)

        # Check Balance
        session = get_session()
        service = TradeService(session)
        has_funds = service.check_balance(interaction.user.id, interaction.guild.id, val)
        session.close()

        if not has_funds:
            return await interaction.response.send_message(f"❌ You don't have **{val:,}** coins!", ephemeral=True)

        # Update View State
        if self.is_user_a:
            self.view_ref.coins_a = val
        else:
            self.view_ref.coins_b = val

        # Reset Acceptance because terms changed
        self.view_ref.accepted_a = False
        self.view_ref.accepted_b = False
        
        await interaction.response.send_message(f"✅ Added **{val:,}** coins to the offer.", ephemeral=True)
        await self.view_ref.update_embed(interaction)

# --- MODAL FOR COUNTER OFFER (PLAYERS) ---
class CounterOfferModal(discord.ui.Modal, title="Make Counter Offer"):
    offer_input = discord.ui.TextInput(
        label="Player Names (Max 3)", 
        placeholder="e.g. Haaland, De Bruyne", 
        required=True
    )
    def __init__(self, view_ref):
        super().__init__()
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        session = get_session()
        service = TradeService(session)
        result = service.validate_offer(interaction.user.id, interaction.guild_id, self.offer_input.value)
        session.close()

        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        self.view_ref.cards_b = result["cards"]
        self.view_ref.accepted_a = False
        self.view_ref.accepted_b = True # Auto-accept own offer
        await interaction.followup.send("✅ Offer updated!", ephemeral=True)
        await self.view_ref.update_embed(interaction)

# --- MAIN VIEW ---
class TradingView(discord.ui.View):
    def __init__(self, bot, user_a, user_b, cards_a):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_a = user_a
        self.user_b = user_b
        
        self.cards_a = cards_a 
        self.cards_b = []      
        
        # NEW: Coin States
        self.coins_a = 0
        self.coins_b = 0
        
        self.accepted_a = True 
        self.accepted_b = False
        self.message = None

    async def update_embed(self, interaction):
        # Format strings with Coins
        offer_a_str = ", ".join([f"**{c.details.name}**" for c in self.cards_a])
        if self.coins_a > 0:
            if not self.cards_a: offer_a_str = "" # Clean formatting if only coins
            prefix = "\n+ " if self.cards_a else ""
            offer_a_str += f"{prefix}💰 **{self.coins_a:,} Coins**"
        if not offer_a_str: offer_a_str = "*None*"

        offer_b_str = ", ".join([f"**{c.details.name}**" for c in self.cards_b])
        if self.coins_b > 0:
            if not self.cards_b: offer_b_str = ""
            prefix = "\n+ " if self.cards_b else ""
            offer_b_str += f"{prefix}💰 **{self.coins_b:,} Coins**"
        if not offer_b_str: offer_b_str = "*Waiting for offer...*"

        embed = discord.Embed(title="🤝 Trade Negotiation", color=discord.Color.blue())
        status_a = "✅ Ready" if self.accepted_a else "⏳ Thinking..."
        status_b = "✅ Ready" if self.accepted_b else "⏳ Thinking..."

        embed.add_field(name=f"{self.user_a.name} ({status_a})", value=offer_a_str, inline=False)
        embed.add_field(name=f"⬇️ ⬆️", value="vs", inline=False)
        embed.add_field(name=f"{self.user_b.name} ({status_b})", value=offer_b_str, inline=False)
        
        # EXECUTE TRADE
        if self.accepted_a and self.accepted_b:
             embed.color = discord.Color.green()
             embed.set_footer(text="Processing Trade...")
             for item in self.children: item.disabled = True
             
             if self.message: await self.message.edit(embed=embed, view=self)
             elif interaction.message: await interaction.message.edit(embed=embed, view=self)

             session = get_session()
             service = TradeService(session)
             
             ids_a = [c.id for c in self.cards_a]
             ids_b = [c.id for c in self.cards_b]
             
             # Pass user IDs explicitly to handle money-only trades safely
             res = service.execute_multi_trade(
                 self.user_a.id, self.user_b.id, 
                 ids_a, ids_b, 
                 self.coins_a, self.coins_b
             )
             
             if res["success"]:
                 embed.title = "✅ Trade Completed!"
                 embed.description = f"**Trade Summary:**\n{offer_a_str}\n↔\n{offer_b_str}"
                 
                 # --- TUTORIAL HOOK ---
                 try:
                     from src.services.tutorial_service import TutorialService
                     tut = TutorialService(session)
                     msg_a = tut.complete_step(self.user_a.id, interaction.guild.id, "7_trade")
                     msg_b = tut.complete_step(self.user_b.id, interaction.guild.id, "7_trade")
                     
                     if msg_a: await interaction.channel.send(f"{self.user_a.mention} {msg_a}")
                     if msg_b: await interaction.channel.send(f"{self.user_b.mention} {msg_b}")
                 except ImportError:
                     pass # Tutorial Service not found
                 except Exception as e:
                     print(f"Tutorial Hook Error: {e}")
                 # ---------------------

             else:
                 embed.title = "❌ Trade Failed"
                 embed.description = res["message"]
                 embed.color = discord.Color.red()
             
             session.close()
             
             if self.message: await self.message.edit(embed=embed, view=None)
             elif interaction.message: await interaction.message.edit(embed=embed, view=None)
             return

        if self.message: await self.message.edit(embed=embed, view=self)
        elif interaction.message: await interaction.message.edit(embed=embed, view=self)

    # --- BUTTONS ---

    @discord.ui.button(label="Add Coins 💰", style=discord.ButtonStyle.secondary, row=1)
    async def add_coins(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_a.id:
            await interaction.response.send_modal(AddCoinsModal(self, is_user_a=True))
        elif interaction.user.id == self.user_b.id:
            await interaction.response.send_modal(AddCoinsModal(self, is_user_a=False))
        else:
            await interaction.response.send_message("You are not part of this trade.", ephemeral=True)

    @discord.ui.button(label="Add/Change Players", style=discord.ButtonStyle.primary, row=1)
    async def counter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_b.id:
            return await interaction.response.send_message("Only the trade partner can add cards!", ephemeral=True)
        await interaction.response.send_modal(CounterOfferModal(self))

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success, row=2)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user_a.id:
            self.accepted_a = not self.accepted_a
        elif interaction.user.id == self.user_b.id:
            # Ensure B offers SOMETHING (Cards OR Coins)
            if not self.cards_b and self.coins_b == 0: 
                return await interaction.response.send_message("You must offer at least one player or coins!", ephemeral=True)
            self.accepted_b = not self.accepted_b
        else:
            return await interaction.response.send_message("You are not part of this trade.", ephemeral=True)
        
        await interaction.response.defer()
        await self.update_embed(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=2)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.user_a.id, self.user_b.id]: return
        embed = discord.Embed(title="❌ Trade Cancelled", color=discord.Color.red())
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)