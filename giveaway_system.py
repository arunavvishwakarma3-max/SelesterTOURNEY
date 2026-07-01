import datetime
import random
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

class GiveawayGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="giveaway", description="Giveaway system commands")

    @app_commands.command(name="setup", description="Set up the giveaway system in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Existing channel for giveaways")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['giveaway_channel_id'] = channel.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = discord.Embed(
            title="✅ GIVEAWAY SYSTEM ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Giveaway system configured in your selected channel.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Channel:** {channel.mention}\n\n"
                "Admins can now start giveaways using `/giveaway start`"
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="SELESTER V3 • Giveaway System Online")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="start", description="Start a giveaway.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Channel to host the giveaway in",
        prize="Prize to give away",
        duration_minutes="Duration in minutes",
        winners="Number of winners (default 1)"
    )
    async def start(self, interaction: discord.Interaction, channel: discord.TextChannel, prize: str, duration_minutes: int, winners: int = 1):
        await interaction.response.defer(ephemeral=True)

        if duration_minutes < 1 or duration_minutes > 43200:
            await interaction.followup.send("❌ Duration must be between 1 minute and 30 days.", ephemeral=True)
            return
        if winners < 1 or winners > 20:
            await interaction.followup.send("❌ Winners must be between 1 and 20.", ephemeral=True)
            return

        ends_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration_minutes)
        ends_str = ends_at.strftime("%b %d, %Y %I:%M %p UTC")

        g_id = database.create_giveaway(interaction.guild_id, channel.id, prize, winners, ends_at.isoformat(), interaction.user.id)

        embed = discord.Embed(
            title="🎉 GIVEAWAY!",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**{prize}**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=embeds.COLOR_GOLD
        )
        embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
        embed.add_field(name="👑 Winners", value=f"`{winners}`", inline=True)
        embed.add_field(name="⏰ Ends", value=f"<t:{int(ends_at.timestamp())}:R>", inline=True)
        embed.add_field(name="👤 Hosted by", value=interaction.user.mention, inline=True)
        embed.add_field(name="🎯 How to Enter", value="React with 🎉 to enter the giveaway!", inline=False)
        embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
        embed.set_footer(text=f"Click 🎉 to enter • Giveaway ID: {g_id} • SELESTER V3")
        msg = await channel.send(content="🎉 **GIVEAWAY** 🎉", embed=embed)
        await msg.add_reaction("🎉")

        database.set_giveaway_message(g_id, msg.id)

        await interaction.followup.send(f"✅ Giveaway started in {channel.mention}!", ephemeral=True)

        await asyncio.sleep(duration_minutes * 60)

        giveaway = database.get_giveaway(msg.id)
        if not giveaway or giveaway['status'] != 'active':
            return

        msg = await channel.fetch_message(msg.id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        async for user in reaction.users():
            if not user.bot:
                users.append(user)

        if len(users) < winners:
            winners_count = len(users)
        else:
            winners_count = winners

        selected = random.sample(users, winners_count) if users else []
        winner_mentions = ", ".join(u.mention for u in selected) if selected else "No one"

        database.end_giveaway(giveaway['id'])

        embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED!",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Prize:** {prize}\n"
                f"**Winner(s):** {winner_mentions}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=embeds.COLOR_GOLD
        )
        embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
        embed.add_field(name="👤 Hosted by", value=interaction.user.mention, inline=False)
        embed.set_footer(text="SELESTER V3 • Giveaway System")
        await msg.edit(content="🎉 **GIVEAWAY ENDED** 🎉", embed=embed)
        if selected:
            await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**!")

    @app_commands.command(name="reroll", description="Reroll a giveaway winner.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(message_id="ID of the giveaway message")
    async def reroll(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            mid = int(message_id)
        except:
            await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)
            return

        giveaway = database.get_giveaway(mid)
        if not giveaway:
            await interaction.followup.send("❌ Giveaway not found.", ephemeral=True)
            return

        try:
            channel = interaction.guild.get_channel(giveaway['channel_id'])
            msg = await channel.fetch_message(mid)
        except:
            await interaction.followup.send("❌ Could not fetch the giveaway message.", ephemeral=True)
            return

        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        async for user in reaction.users():
            if not user.bot:
                users.append(user)

        if not users:
            await interaction.followup.send("❌ No eligible users to reroll.", ephemeral=True)
            return

        winner = random.choice(users)
        await channel.send(f"🎉 **Reroll!** New winner: {winner.mention}! Won **{giveaway['prize']}**!")
        await interaction.followup.send(f"✅ Rerolled! New winner: {winner.mention}", ephemeral=True)

    @app_commands.command(name="end", description="End a giveaway early.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(message_id="ID of the giveaway message")
    async def end(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            mid = int(message_id)
        except:
            await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)
            return

        giveaway = database.get_giveaway(mid)
        if not giveaway or giveaway['status'] != 'active':
            await interaction.followup.send("❌ Giveaway not found or already ended.", ephemeral=True)
            return

        database.end_giveaway(giveaway['id'])
        try:
            channel = interaction.guild.get_channel(giveaway['channel_id'])
            msg = await channel.fetch_message(mid)
            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED EARLY",
                description=f"**Prize:** {giveaway['prize']}\n**Ended by:** {interaction.user.mention}",
                color=embeds.COLOR_RED
            )
            await msg.edit(embed=embed)
            await interaction.followup.send("✅ Giveaway ended early.", ephemeral=True)
        except:
            await interaction.followup.send("✅ Giveaway ended (could not edit message).", ephemeral=True)

    @app_commands.command(name="list", description="List active giveaways.")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_giveaways(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        giveaways = database.get_active_giveaways(interaction.guild_id)
        if not giveaways:
            await interaction.followup.send("❌ No active giveaways.", ephemeral=True)
            return
        lines = []
        for g in giveaways:
            ends = datetime.datetime.fromisoformat(g['ends_at']).strftime("%b %d, %I:%M %p")
            lines.append(f"🔹 **{g['prize']}** — Ends: `{ends}` — ID: `{g['message_id']}`")
        embed = discord.Embed(
            title="🎉 Active Giveaways",
            description="\n".join(lines),
            color=embeds.COLOR_GOLD
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
