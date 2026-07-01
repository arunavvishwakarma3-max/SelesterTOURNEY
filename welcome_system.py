import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

class WelcomeGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="welcome", description="Welcome system commands")

    @app_commands.command(name="setup", description="Set up the welcome system in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Existing channel for welcome messages")
    async def setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['welcome_channel_id'] = channel.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = discord.Embed(
            title="✅ WELCOME SYSTEM ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Welcome system configured in your selected channel.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Channel:** {channel.mention}\n\n"
                "New members will automatically receive a welcome message there."
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="Celestia • Welcome System Online")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="test", description="Test the welcome message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def test(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg['welcome_channel_id']:
            await interaction.followup.send("❌ Welcome system not set up. Use `/welcome setup` first.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(cfg['welcome_channel_id'])
        if not channel:
            await interaction.followup.send("❌ Welcome channel not found.", ephemeral=True)
            return

        embed = embeds.welcome_embed(interaction.user, interaction.guild.member_count)
        await channel.send(embed=embed)
        await interaction.followup.send(f"✅ Test welcome sent to {channel.mention}!", ephemeral=True)

async def send_welcome(member: discord.Member):
    cfg = database.get_guild_config_v3(member.guild.id)
    if not cfg or not cfg['welcome_channel_id']:
        return

    channel = member.guild.get_channel(cfg['welcome_channel_id'])
    if not channel:
        return

    embed = embeds.welcome_embed(member, member.guild.member_count)
    try:
        await channel.send(embed=embed)
    except:
        pass
