import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import views

class RankedGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ranked", description="Ranked gamemode system commands")

    @app_commands.command(name="setup", description="Set up the ranked system in existing channels.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        queue_channel="Existing channel for ranked queue",
        results_channel="Existing channel for ranked results",
        ranked_role="Role awarded to ranked players (optional)"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        queue_channel: discord.TextChannel,
        results_channel: discord.TextChannel,
        ranked_role: discord.Role = None
    ):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['ranked_queue_channel_id'] = queue_channel.id
        cfg['ranked_results_channel_id'] = results_channel.id
        if ranked_role:
            cfg['ranked_role_id'] = ranked_role.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = discord.Embed(
            title="🏆 RANKED GAMEMODES",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**Compete in 1v1 matches and climb the leaderboard!**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Select a gamemode below to view the queue and start playing."
            ),
            color=embeds.COLOR_RANKED
        )
        embed.add_field(
            name="📋 COMPETITIVE RULES",
            value=(
                "```diff\n"
                "+ ✅ Fair Play — No hacking or cheating\n"
                "+ ✅ Respect opponents at all times\n"
                "+ ✅ Report any bugs to staff\n"
                "- ❌ No intentional disconnecting\n"
                "```\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "**📊 Point System:**\n"
                "▸ Winner: **+10 points**\n"
                "▸ Loser: **+1 point**\n"
                "▸ Top players appear on `/lb ranked`"
            ),
            inline=False
        )
        embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
        embed.set_footer(text="SELESTER V3 • Ranked Competitive System")
        view = views.RankedGamemodeSelect()
        await queue_channel.send(embed=embed, view=view)

        success_embed = discord.Embed(
            title="✅ RANKED SYSTEM ACTIVATED",
            description=(
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Ranked system configured in your selected channels.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Queue Channel:** {queue_channel.mention}\n"
                f"📌 **Results Channel:** {results_channel.mention}\n"
                f"{f'👤 **Ranked Role:** {ranked_role.mention}' if ranked_role else ''}\n\n"
                f"Players can now select a gamemode and start their ranked journey!"
            ),
            color=embeds.COLOR_GREEN
        )
        success_embed.set_footer(text="SELESTER V3 • Ranked System Online")
        await interaction.followup.send(embed=success_embed, ephemeral=True)

    @app_commands.command(name="stats", description="Check your ranked stats.")
    @app_commands.describe(gamemode="Gamemode to check stats for")
    async def stats(
        self,
        interaction: discord.Interaction,
        gamemode: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        if not gamemode:
            entries = database.get_ranked_leaderboard(interaction.guild_id, limit=999)
            user_entries = [e for e in entries if e['user_id'] == interaction.user.id]
            if not user_entries:
                await interaction.followup.send("❌ You have no ranked stats yet. Play some matches!", ephemeral=True)
                return

            embed = discord.Embed(title="📊 YOUR RANKED STATS", color=embeds.COLOR_RANKED)
            for e in user_entries:
                embed.add_field(
                    name=f"🎮 {e['gamemode']}",
                    value=f"**Points:** {e['points']} | W: {e['wins']} L: {e['losses']}",
                    inline=False
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        stats = database.get_ranked_stats(interaction.guild_id, interaction.user.id, gamemode)
        if not stats:
            await interaction.followup.send(f"❌ No stats for **{gamemode}**. Play some matches!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 {gamemode.upper()} STATS",
            description=f"<@{interaction.user.id}>",
            color=embeds.COLOR_RANKED
        )
        embed.add_field(name="Points", value=f"`{stats['points']}`", inline=True)
        embed.add_field(name="Wins", value=f"`{stats['wins']}`", inline=True)
        embed.add_field(name="Losses", value=f"`{stats['losses']}`", inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

class LbGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="lb", description="Leaderboard commands")

    @app_commands.command(name="ranked", description="Show the ranked leaderboard.")
    @app_commands.describe(gamemode="Filter by gamemode (optional)")
    async def ranked(
        self,
        interaction: discord.Interaction,
        gamemode: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        entries = database.get_ranked_leaderboard(interaction.guild_id, gamemode)
        embed = embeds.ranked_leaderboard_embed(entries, gamemode)
        await interaction.followup.send(embed=embed, ephemeral=True)
