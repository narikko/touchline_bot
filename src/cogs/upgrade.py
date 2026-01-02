import discord
from discord.ext import commands
from discord import app_commands
from src.services.upgrade_service import UpgradeService
from src.database.db import get_session

class UpgradeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="upgrades", description="Manage your team upgrades (Stadium, Board, Training, Transfer).")
    @app_commands.describe(action="Choose 'Info' to see prices, or select an upgrade to buy.")
    @app_commands.choices(action=[
        app_commands.Choice(name="ℹ️ View Prices & Info", value="info"),
        app_commands.Choice(name="🏟️ Buy: Stadium", value="stadium"),
        app_commands.Choice(name="👔 Buy: Board", value="board"),
        app_commands.Choice(name="🏋️‍♂️ Buy: Training Facility", value="training"),
        app_commands.Choice(name="📜 Buy: Transfer Market", value="transfer"),
        app_commands.Choice(name="🔭 Buy: Scout Network", value="scout"),
    ])
    async def upgrades(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        # 1. Defer response (db ops might take a moment)
        await interaction.response.defer()
        
        session = get_session()
        service = UpgradeService(session)

        try:
            choice = action.value

            # --- OPTION 1: VIEW INFO MENU ---
            if choice == "info":
                data = service.get_menu_info(str(interaction.user.id), str(interaction.guild_id))
                
                embed = discord.Embed(
                    title="🏗️ Club Upgrades", 
                    description="Invest in your club to gain long-term bonuses.",
                    color=discord.Color.blue()
                )
                
                # Show current balance in footer
                embed.set_footer(text=f"Your Balance: {data['user_balance']:,} 💠")
                
                for item in data["upgrades"]:
                    # Format Price
                    if item['next_price'] == "MAX":
                        price_str = "✅ **MAXED**"
                    else:
                        price_str = f"**{item['next_price']:,}** 💠"
                    
                    # Format Bonus Text (Current -> Next)
                    bonus_str = f"Current: **{item['current_bonus']}**"
                    if item['next_price'] != "MAX":
                        bonus_str += f" ➡ **{item['next_bonus']}**"
                    
                    # Add Field
                    embed.add_field(
                        name=f"{item['name']} (Lvl {item['current_level']}/{item['max_level']})",
                        value=f"{item['description']}\n💰 Cost: {price_str}\n📈 {bonus_str}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)

                # --- TUTORIAL HOOK: 6_info ---
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "6_info")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except Exception as e: print(f"Tutorial Error: {e}")
                # -----------------------------

            # --- OPTION 2: BUY AN UPGRADE ---
            else:
                # The 'choice' variable holds "stadium", "board", etc.
                result = service.buy_upgrade(str(interaction.user.id), str(interaction.guild_id), choice)
                
                if result["success"]:
                    embed = discord.Embed(
                        title=f"✅ Upgraded {result['name']}!",
                        description=(
                            f"Level increased to **{result['new_level']}**.\n"
                            f"New Bonus: **{result['new_bonus']}**\n\n"
                            f"💸 Paid: **{result['cost']:,}** 💠\n"
                            f"💰 Remaining Balance: **{result['balance']:,}** 💠"
                        ),
                        color=discord.Color.green()
                    )
                    await interaction.followup.send(embed=embed)

                    if result["reward"]:
                        await interaction.followup.send(result["reward"])

                    # --- TUTORIAL HOOK: 6_buy ---
                    try:
                        from src.services.tutorial_service import TutorialService
                        tut_service = TutorialService(session)
                        tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "6_buy")
                        if tut_msg: await interaction.followup.send(tut_msg)
                    except Exception as e: print(f"Tutorial Error: {e}")
                    # ----------------------------

                else:
                    # Failure (Not enough money, max level, etc.)
                    embed = discord.Embed(
                        title="❌ Upgrade Failed",
                        description=(
                            f"{result['message']}\n\n"
                            "💸 **Need cash fast?**\n"
                            "Invite a friend with **/invite** to instantly earn **1,000 Coins**!"
                        ),
                        color=discord.Color.red()
                    )
                    await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Error in upgrades command: {e}")
            await interaction.followup.send("An error occurred while processing the upgrade.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(UpgradeCog(bot))