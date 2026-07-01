import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import datetime

class StaffApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📋 Staff Application")

    ign = discord.ui.TextInput(
        label="In-Game Name",
        placeholder="Your Minecraft IGN",
        min_length=2,
        max_length=24,
        required=True
    )
    age = discord.ui.TextInput(
        label="Age",
        placeholder="Your age",
        min_length=1,
        max_length=3,
        required=True
    )
    why = discord.ui.TextInput(
        label="Why do you want to be staff?",
        placeholder="Tell us why you'd be a good staff member...",
        style=discord.TextStyle.paragraph,
        min_length=20,
        max_length=1000,
        required=True
    )
    experience = discord.ui.TextInput(
        label="Staff Experience",
        placeholder="Any previous moderation experience?",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=1000,
        required=True
    )
    hours = discord.ui.TextInput(
        label="Hours Available (per day)",
        placeholder="e.g. 4-6 hours",
        min_length=1,
        max_length=20,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('staff_apps_channel_id'):
            await interaction.followup.send("❌ Staff applications system is not set up. Ask an admin to run `/apply staff setup`.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(cfg['staff_apps_channel_id'])
        if not channel:
            await interaction.followup.send("❌ Staff applications channel not found.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 NEW STAFF APPLICATION",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "A new staff application has been submitted!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x9B59B6
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Applicant", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="🎮 IGN", value=f"```{self.ign.value}```", inline=True)
        embed.add_field(name="📅 Age", value=f"```{self.age.value}```", inline=True)
        embed.add_field(name="⏰ Hours/Day", value=f"```{self.hours.value}```", inline=True)
        embed.add_field(name="💬 Why Staff?", value=f"```{self.why.value}```", inline=False)
        embed.add_field(name="📜 Experience", value=f"```{self.experience.value}```", inline=False)
        embed.add_field(
            name="📌 Status",
            value="```css\n[ Pending Review ]\n```",
            inline=False
        )
        embed.set_footer(text=f"Submitted • {datetime.datetime.utcnow().strftime('%b %d, %Y %I:%M %p UTC')}")
        embed.timestamp = discord.utils.utcnow()

        msg = await channel.send(
            content="🔔 <@&" + str(cfg.get('tier_staff_role_id', 0)) + ">" if cfg.get('tier_staff_role_id') else None,
            embed=embed
        )
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        await interaction.followup.send(
            embed=discord.Embed(
                title="✅ APPLICATION SUBMITTED",
                description=(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Your staff application has been received!\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "We will review it and get back to you. Please be patient."
                ),
                color=embeds.COLOR_GREEN
            ),
            ephemeral=True
        )

class ApplyGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="apply", description="Application commands")

    @app_commands.command(name="staff", description="Submit a staff application.")
    async def staff(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StaffApplicationModal())

    @app_commands.command(name="staffsetup", description="Set up the staff applications system in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Existing channel for staff applications",
        staff_role="Role to ping when new applications come in (optional)"
    )
    async def staffsetup(self, interaction: discord.Interaction, channel: discord.TextChannel, staff_role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['staff_apps_channel_id'] = channel.id
        if staff_role:
            cfg['tier_staff_role_id'] = staff_role.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = discord.Embed(
            title="✅ STAFF APPLICATIONS ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Staff applications configured in your selected channel.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Channel:** {channel.mention}\n"
                f"{f'👤 **Staff Role:** {staff_role.mention}' if staff_role else ''}\n\n"
                "Members can now apply using `/apply staff`"
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="Celestia • Staff Applications")
        await interaction.followup.send(embed=embed, ephemeral=True)
