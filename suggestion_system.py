import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

class SuggestionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="💡 Submit a Suggestion")

        self.content = discord.ui.TextInput(
            label="Your Suggestion",
            placeholder="Describe your suggestion in detail...",
            style=discord.TextStyle.paragraph,
            min_length=10,
            max_length=1500,
            required=True
        )
        self.add_item(self.content)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('suggestion_channel_id'):
            await interaction.followup.send("❌ Suggestions system not set up.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(cfg['suggestion_channel_id'])
        if not channel:
            await interaction.followup.send("❌ Suggestions channel not found.", ephemeral=True)
            return

        content = self.content.value
        s_id = database.create_suggestion(interaction.guild_id, channel.id, interaction.user.id, content)

        embed = embeds.suggestion_embed(s_id, interaction.user, content)
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        database.set_suggestion_message(s_id, msg.id)
        await interaction.followup.send(f"✅ Suggestion submitted in {channel.mention}!", ephemeral=True)

class SuggestionGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="suggestion", description="Suggestion system commands")

    @app_commands.command(name="setup", description="Set up the suggestion system in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Existing channel for suggestions")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['suggestion_channel_id'] = channel.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = discord.Embed(
            title="✅ SUGGESTIONS SYSTEM ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Suggestions system configured in your selected channel.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Channel:** {channel.mention}\n\n"
                "Members can now submit suggestions using:\n"
                "▸ `/suggestion submit` or `/suggest submit`"
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="SELESTER V3 • Suggestions System Online")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="submit", description="Submit a suggestion (opens modal).")
    async def submit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuggestionModal())

    @app_commands.command(name="approve", description="Approve a suggestion.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(message_id="Message ID of the suggestion")
    async def approve(self, interaction: discord.Interaction, message_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            mid = int(message_id)
        except:
            await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)
            return

        suggestion = database.get_suggestion(mid)
        if not suggestion:
            await interaction.followup.send("❌ Suggestion not found.", ephemeral=True)
            return

        database.update_suggestion_status(mid, "approved")
        try:
            channel = interaction.guild.get_channel(suggestion['channel_id'])
            msg = await channel.fetch_message(mid)
            embed = msg.embeds[0]
            embed.set_field_at(0, name="Status", value="`✅ Approved`", inline=False)
            embed.color = embeds.COLOR_GREEN
            await msg.edit(embed=embed)
        except:
            pass
        await interaction.followup.send("✅ Suggestion approved!", ephemeral=True)

    @app_commands.command(name="deny", description="Deny a suggestion.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(message_id="Message ID of the suggestion", reason="Reason for denial")
    async def deny(self, interaction: discord.Interaction, message_id: str, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        try:
            mid = int(message_id)
        except:
            await interaction.followup.send("❌ Invalid message ID.", ephemeral=True)
            return

        suggestion = database.get_suggestion(mid)
        if not suggestion:
            await interaction.followup.send("❌ Suggestion not found.", ephemeral=True)
            return

        database.update_suggestion_status(mid, "denied")
        try:
            channel = interaction.guild.get_channel(suggestion['channel_id'])
            msg = await channel.fetch_message(mid)
            embed = msg.embeds[0]
            embed.set_field_at(0, name="Status", value=f"`❌ Denied` — {reason}", inline=False)
            embed.color = embeds.COLOR_RED
            await msg.edit(embed=embed)
        except:
            pass
        await interaction.followup.send("✅ Suggestion denied.", ephemeral=True)

class SuggestGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="suggest", description="Submit a suggestion")

    @app_commands.command(name="submit", description="Submit a suggestion (opens modal).")
    async def submit(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuggestionModal())
