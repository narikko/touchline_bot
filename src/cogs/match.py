import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from src.database.db import get_session
from src.services.match_service import MatchService
from src.views.match_view import MatchChallengeView

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="match", description="Challenge another player to a match (30 mins).")
    @app_commands.describe(opponent="The user you want to play against", wager="Amount of coins to bet")
    async def match(self, interaction: discord.Interaction, opponent: discord.User, wager: int):
        await interaction.response.defer()
        
        if opponent.id == interaction.user.id or opponent.bot:
            await interaction.followup.send("You cannot play against yourself or bots!", ephemeral=True)
            return
            
        if wager < 500:
            await interaction.followup.send("Minimum wager is **500** 💠.", ephemeral=True)
            return

        session = get_session()
        service = MatchService(session)

        try:
            # 1. Validate
            home_stats = service.get_team_power(interaction.user.id, interaction.guild_id)
            away_stats = service.get_team_power(opponent.id, interaction.guild_id)

            if not home_stats["valid"]:
                await interaction.followup.send(f"❌ You cannot play: {home_stats['message']}", ephemeral=True)
                return
            if not away_stats["valid"]:
                await interaction.followup.send(f"❌ Opponent cannot play: {away_stats['message']}", ephemeral=True)
                return

            if home_stats["user"].coins < wager:
                await interaction.followup.send(f"❌ You need **{wager}** 💠 to play.", ephemeral=True)
                return
            if away_stats["user"].coins < wager:
                await interaction.followup.send(f"❌ {opponent.display_name} does not have enough coins.", ephemeral=True)
                return

            # 2. Challenge Phase
            view = MatchChallengeView(interaction.user, opponent, wager)
            await interaction.followup.send(
                f"⚽ **MATCH CHALLENGE**\n{interaction.user.mention} vs {opponent.mention}\n"
                f"💰 Wager: **{wager}** 💠\n"
                f"📊 OVR: **{home_stats['ovr']}** vs **{away_stats['ovr']}**\n"
                f"⏳ Duration: **30 Minutes**\n\n"
                f"{opponent.mention}, do you accept?",
                view=view
            )

            await view.wait()

            if not view.accepted:
                await interaction.edit_original_response(content="❌ Match Cancelled / Declined.", view=None)
                return

            # 3. Start Match Logic
            if not service.process_wager(home_stats["user"].id, away_stats["user"].id, wager):
                await interaction.edit_original_response(content="Transaction failed (balance changed). Match cancelled.", view=None)
                return
            
            try:
                from src.services.tutorial_service import TutorialService
                tut_service = TutorialService(session) 
                
                # 1. Challenger
                msg_challenger = tut_service.complete_step(interaction.user.id, interaction.guild_id, "8_match")
                
                # 2. Opponent
                msg_opponent = tut_service.complete_step(opponent.id, interaction.guild_id, "8_match")

                # 3. Send Notifications
                # We use channel.send because we don't want to mess up the match embed
                if msg_challenger:
                    await interaction.channel.send(f"{interaction.user.mention}\n{msg_challenger}")
                
                if msg_opponent:
                    await interaction.channel.send(f"{opponent.mention}\n{msg_opponent}")

            except Exception as e:
                print(f"Tutorial Error: {e}")

            # Pre-calculate the entire match script
            match_data = service.simulate_match(home_stats, away_stats)
            timeline = match_data["timeline"]

            # Initialize Embed
            embed = discord.Embed(title="⚽ Match Started!", color=discord.Color.green())
            embed.add_field(name=home_stats["user"].club_name, value="0", inline=True)
            embed.add_field(name="vs", value="⏱️ 0'", inline=True)
            embed.add_field(name=away_stats["user"].club_name, value="0", inline=True)
            embed.set_footer(text="Match is live! Updates will appear here.")

            # IMPORTANT: Send a FRESH message using channel.send
            # Interaction tokens expire in 15 mins. A regular message lasts forever.
            await interaction.edit_original_response(content="✅ **Match Accepted!** Generating live commentary below...", view=None)
            match_msg = await interaction.channel.send(embed=embed)

            # 4. The 30-Minute Loop
            current_home_score = 0
            current_away_score = 0
            elapsed_real_time = 0

            for event in timeline:
                # Sleep until the next event happens
                wait_time = event["real_second"] - elapsed_real_time
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                elapsed_real_time = event["real_second"]
                
                # Update Scores and Text
                minute = event["game_minute"]
                text = event["text"]
                current_home_score, current_away_score = event["score"]
                
                embed.description = f"**{minute}'** {text}"
                embed.set_field_at(0, name=home_stats["user"].club_name, value=str(current_home_score), inline=True)
                embed.set_field_at(1, name="vs", value=f"⏱️ {minute}'", inline=True)
                embed.set_field_at(2, name=away_stats["user"].club_name, value=str(current_away_score), inline=True)
                
                if event["type"] == "goal":
                    embed.color = discord.Color.gold()
                else:
                    embed.color = discord.Color.blue()
                
                try:
                    await match_msg.edit(embed=embed)
                except discord.NotFound:
                    print("Match message deleted by user.")
                    # We continue the loop to ensure payout happens, even if display is gone

            # 5. Finish the remaining time (up to 30 mins / 1800s)
            remaining_time = 1800 - elapsed_real_time
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)

            # 6. Payout
            service.payout(home_stats["user"].id, away_stats["user"].id, match_data["winner"], wager)
            
            winner_text = "Draw!"
            if match_data["winner"] == "home":
                winner_text = f"🏆 {interaction.user.mention} Wins!"
            elif match_data["winner"] == "away":
                winner_text = f"🏆 {opponent.mention} Wins!"

            embed.title = "🏁 Full Time"
            embed.description = f"**Match Finished!**\n{winner_text}\n\n💰 **Pot:** {wager*2} 💠"
            embed.set_field_at(1, name="vs", value="FT", inline=True)
            embed.color = discord.Color.green()
            
            try:
                # Send a NEW message tagging them so they get notified
                await match_msg.edit(embed=embed)
                await interaction.channel.send(f"{interaction.user.mention} {opponent.mention} **Match Finished!** Check the results above.")
            except:
                pass

        except Exception as e:
            print(f"Error in match command: {e}")
            await interaction.followup.send("An error occurred.", ephemeral=True)
        finally:
            session.close()

async def setup(bot):
    await bot.add_cog(MatchCog(bot))