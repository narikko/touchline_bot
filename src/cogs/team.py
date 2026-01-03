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

    # --- SUBCOMMAND: FORMATION ---
    @team_group.command(name="formation", description="Change your team's tactical formation.")
    @app_commands.describe(style="Select a formation")
    @app_commands.choices(style=[
        app_commands.Choice(name="4-3-3 (Balanced)", value="4-3-3"),
        app_commands.Choice(name="4-4-2 (Classic)", value="4-4-2"),
        app_commands.Choice(name="3-4-3 (Attack)", value="3-4-3"),
        app_commands.Choice(name="3-5-2 (Midfield)", value="3-5-2"),
        app_commands.Choice(name="5-3-2 (Defensive)", value="5-3-2"),
        app_commands.Choice(name="4-5-1 (Control)", value="4-5-1"),
    ])
    async def set_formation(self, interaction: discord.Interaction, style: app_commands.Choice[str]):
        await interaction.response.defer()
        session = get_session()
        service = TeamService(session)
        try:
            result = service.change_formation(interaction.user.id, interaction.guild_id, style.value)
            await interaction.followup.send(result["message"])
        finally:
            session.close()

    # --- SUBCOMMAND: VIEW ---
    @team_group.command(name="view", description="View your (or another user's) starting XI.")
    @app_commands.describe(user="The user whose team you want to view (optional).")
    async def view_team(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer()
        target_user = user if user else interaction.user
        if target_user.bot:
            await interaction.followup.send("🤖 Bots don't play football!", ephemeral=True)
            return

        session = get_session()
        service = TeamService(session)
        
        try:
            result = service.get_starting_xi(target_user.id, interaction.guild_id)
            if not result["success"]:
                msg = f"❌ **{target_user.display_name}** hasn't set up their club yet." if user else result["message"]
                await interaction.followup.send(msg)
                return

            club_name = result["club_name"]
            lineup = result["lineup"]
            ovl_value = result["ovl_value"]
            formation = result["formation"]
            config = result["config"] # Contains {D: 4, M: 3, F: 3}
            
            embed = discord.Embed(
                title=f"⚽ {club_name} ({formation})", 
                description=f"Overall Value: **{ovl_value}**",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Manager: {target_user.display_name}", icon_url=target_user.display_avatar.url)
            
            def get_field(pos_code):
                player = lineup.get(pos_code)
                return f"**{player.name}** ({player.rating})" if player else "---"

            # Dynamic Field Generation
            embed.add_field(name="🧤 Goalkeeper", value=get_field("GK"), inline=False)
            
            # Defenders
            d_str = ""
            for i in range(1, config["D"] + 1):
                d_str += f"D{i}: {get_field(f'D{i}')}\n"
            embed.add_field(name="🛡️ Defenders", value=d_str, inline=False)
            
            # Midfielders
            m_str = ""
            for i in range(1, config["M"] + 1):
                m_str += f"M{i}: {get_field(f'M{i}')}\n"
            embed.add_field(name="⚙️ Midfielders", value=m_str, inline=False)
            
            # Forwards
            f_str = ""
            for i in range(1, config["F"] + 1):
                f_str += f"F{i}: {get_field(f'F{i}')}\n"
            embed.add_field(name="🔥 Forwards", value=f_str, inline=False)
            
            await interaction.followup.send(embed=embed)

            # Tutorial Hook (Only for self)
            if target_user.id == interaction.user.id:
                try:
                    from src.services.tutorial_service import TutorialService
                    tut_service = TutorialService(session)
                    tut_msg = tut_service.complete_step(interaction.user.id, interaction.guild_id, "5_view_team")
                    if tut_msg: await interaction.followup.send(tut_msg)
                except: pass

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