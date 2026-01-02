import discord
from discord import app_commands
from discord.ext import commands
from src.services.team_service import TeamService
from src.database.db import get_session

class TeamCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. Create the Parent Group "/team"
    team_group = app_commands.Group(name="team", description="Manage your starting XI and club details.")

    # --- SUBCOMMAND: VIEW ---
    # --- SUBCOMMAND: VIEW ---
    @team_group.command(name="view", description="View your (or another user's) starting XI.")
    @app_commands.describe(user="The user whose team you want to view (optional).")
    async def view_team(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer()
        
        # 1. Determine Target (If no user specified, view self)
        target_user = user if user else interaction.user
        
        # Optional: Prevent viewing bots
        if target_user.bot:
            await interaction.followup.send("🤖 Bots don't play football!", ephemeral=True)
            return

        session = get_session()
        service = TeamService(session)
        
        try:
            # 2. Get the team for the TARGET user
            result = service.get_starting_xi(target_user.id, interaction.guild_id)
            
            if not result["success"]:
                # If viewing someone else, make the error clearer
                if user:
                    await interaction.followup.send(f"❌ **{target_user.display_name}** hasn't set up their club yet.")
                else:
                    await interaction.followup.send(result["message"])
                return

            club_name = result["club_name"]
            lineup = result["lineup"]
            ovl_value = result["ovl_value"]
            
            # 3. Build Embed
            embed = discord.Embed(
                title=f"⚽ {club_name}", 
                description=f"Overall Value: **{ovl_value}**",
                color=discord.Color.blue()
            )
            
            # Add footer to clarify whose team this is
            embed.set_footer(text=f"Manager: {target_user.display_name}", icon_url=target_user.display_avatar.url)
            
            def get_field(pos_code):
                player = lineup.get(pos_code)
                return f"**{player.name}** ({player.rating})" if player else "---"

            embed.add_field(name="🧤 Goalkeeper", value=get_field("GK"), inline=False)
            embed.add_field(name="🛡️ Defenders", value=f"D1: {get_field('D1')}\nD2: {get_field('D2')}\nD3: {get_field('D3')}\nD4: {get_field('D4')}", inline=False)
            embed.add_field(name="⚙️ Midfielders", value=f"M1: {get_field('M1')}\nM2: {get_field('M2')}\nM3: {get_field('M3')}", inline=False)
            embed.add_field(name="🔥 Forwards", value=f"F1: {get_field('F1')}\nF2: {get_field('F2')}\nF3: {get_field('F3')}", inline=False)
            
            await interaction.followup.send(embed=embed)

            # --- TUTORIAL HOOK: 5_view_team ---
            # Only trigger tutorial if viewing YOURSELF (otherwise they cheat the step by looking at others)
            if target_user.id == interaction.user.id:
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_view_team")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except Exception as e: print(f"Tutorial Error: {e}")
            # ----------------------------------

        finally:
            session.close()

    # --- SUBCOMMAND: SET (Arguments are REQUIRED here) ---
    @team_group.command(name="set", description="Add a player to your starting XI.")
    @app_commands.describe(position="Position (GK, D1-D4, M1-M3, F1-F3)", player_name="Name of the player")
    async def set_player(self, interaction: discord.Interaction, position: str, player_name: str):
        await interaction.response.defer()
        session = get_session()
        service = TeamService(session)
        
        try:
            result = service.set_lineup_player(interaction.user.id, interaction.guild_id, position, player_name)
            await interaction.followup.send(result["message"])

            # --- TUTORIAL HOOK: 5_set ---
            # Only trigger if action was successful
            if result.get("success"):
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_set")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except Exception as e: print(f"Tutorial Error: {e}")
            # ----------------------------

        finally:
            session.close()

    # --- SUBCOMMAND: BENCH (Argument is REQUIRED here) ---
    @team_group.command(name="bench", description="Remove a player from your starting XI.")
    @app_commands.describe(player_name="Name of the player to remove")
    async def bench_player(self, interaction: discord.Interaction, player_name: str):
        await interaction.response.defer()
        session = get_session()
        service = TeamService(session)
        
        try:
            result = service.remove_from_lineup(interaction.user.id, interaction.guild_id, player_name)
            await interaction.followup.send(result["message"])

            # --- TUTORIAL HOOK: 5_bench ---
            if result.get("success"):
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_bench")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except Exception as e: print(f"Tutorial Error: {e}")
            # ------------------------------

        finally:
            session.close()

    # --- SUBCOMMAND: RENAME ---
    @team_group.command(name="rename", description="Change your club's name.")
    @app_commands.describe(new_name="The new name for your club")
    async def rename_club(self, interaction: discord.Interaction, new_name: str):
        await interaction.response.defer()
        session = get_session()
        service = TeamService(session)
        
        try:
            result = service.rename_club(interaction.user.id, interaction.guild_id, new_name)
            await interaction.followup.send(result["message"])

            # --- TUTORIAL HOOK: 5_rename ---
            if result.get("success"):
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_rename")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except Exception as e: print(f"Tutorial Error: {e}")
            # -------------------------------

        finally:
            session.close()

    # --- SUBCOMMAND: REWARDS ---
    @team_group.command(name="rewards", description="View and claim team building rewards.")
    async def team_rewards(self, interaction: discord.Interaction):
        await interaction.response.defer()
        session = get_session()
        service = TeamService(session)
        
        try:
            data = service.get_team_stats_and_rewards(interaction.user.id, interaction.guild_id)
            if not data:
                await interaction.followup.send("User not found. Register first!", ephemeral=True)
                return

            embed = discord.Embed(
                title="🏆 Team Building Rewards",
                description=f"Current Team OVL: **{data['ovl_value']}**\nPlayers in XI: **{data['player_count']}/11**\n\n",
                color=discord.Color.gold()
            )

            if data.get('training_bonus', 0) > 0:
                 embed.description += f"*(Includes +{data['training_bonus']} boost from Training Facility)*\n\n"

            reward_text = ""
            for r in data["rewards"]:
                check = "✅" if r["claimed"] else "⬜"
                reward_text += f"{check} **{r['desc']}**\n└ Reward: {r['reward']}\n\n"
            
            embed.add_field(name="Milestones", value=reward_text)
            embed.set_footer(text="Rewards are automatically applied when you reach the milestone!")
            
            await interaction.followup.send(embed=embed)

            # --- TUTORIAL HOOK: 5_rewards ---
            try:
                from src.services.tutorial_service import TutorialService
                tut_service = TutorialService(session)
                tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_rewards")
                if tut_msg: await interaction.followup.send(tut_msg)
            except Exception as e: print(f"Tutorial Error: {e}")
            # --------------------------------

        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(TeamCog(bot))