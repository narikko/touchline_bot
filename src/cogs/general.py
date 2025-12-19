import discord
from discord.ext import commands
from discord import app_commands

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="index", description="View the complete list of commands.")
    async def index(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Manager's Handbook (Index)",
            description="Here is every command available to you.",
            color=discord.Color.teal()
        )

        # 1. Gacha & Collection
        embed.add_field(
            name="🎰 Scouting & Collection",
            value=(
                "`/r` - Roll for a new player.\n"
                "`/daily` - Claim daily rewards.\n"
                "`/collection` - View your players.\n"
                "`/view [name]` - View details of a specific card.\n"
                "`/sell [name]` - Sell a player for coins.\n"
                "`/sort` - Sort collection by rating.\n"
                "`/shortlist` - Manage your wishlist notifications.\n"
                "`/setclub` - Set your favorite team."
            ),
            inline=False
        )

        # 2. Team Management
        embed.add_field(
            name="⚽ Team Management",
            value=(
                "`/team view` - See your Starting XI.\n"
                "`/team set [pos] [name]` - Add a player to your team.\n"
                "`/team bench [name]` - Remove a player from your team.\n"
                "`/team rewards` - Check Team OVL milestones.\n"
                "`/team rename` - Change your club's name."
            ),
            inline=False
        )

        # 3. Economy & Market
        embed.add_field(
            name="💰 Economy & Market",
            value=(
                "`/market add` - List a player for profit (wait time).\n"
                "`/market view` - Check status of your listed player.\n"
                "`/trade [user] [card]` - Swap players with another user.\n"
                "`/upgrades` - Buy club upgrades (Stadium, Scout, etc.)."
            ),
            inline=False
        )

        # 4. Gameplay
        embed.add_field(
            name="🏆 Gameplay",
            value=(
                "`/match [user] [wager]` - Challenge someone to a match.\n"
                "`/profile` - View your stats and timers.\n"
                "`/tutorial` - Check your progress."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(GeneralCog(bot))