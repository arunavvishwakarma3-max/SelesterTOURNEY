import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import datetime


class StaffApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Staff Application")

    ign = discord.ui.TextInput(
        label="In-Game Name",
        placeholder="Your Minecraft IGN",
        min_length=2,
        max_length=24,
        required=True
    )
    age = discord.ui.TextInput(
        label="Age",
        placeholder="e.g. 18",
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

        if not self.age.value.strip().isdigit():
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Invalid Age",
                    description="Age must be a number. Please try again.",
                    color=0xFF1744
                ),
                ephemeral=True
            )
            return

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('staff_apps_channel_id'):
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Not Configured",
                    description="Staff applications are not set up. Ask an admin to run `/apply staffsetup`.",
                    color=0xFF1744
                ),
                ephemeral=True
            )
            return

        pending = database.get_pending_staff_application(interaction.guild_id, interaction.user.id)
        if pending:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Already Applied",
                    description=(
                        f"You already have a pending application (#{pending['id']}).\n"
                        "Wait for it to be reviewed before applying again."
                    ),
                    color=0xFF9F00
                ),
                ephemeral=True
            )
            return

        app_id = database.create_staff_application(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            ign=self.ign.value.strip(),
            age=self.age.value.strip(),
            why=self.why.value.strip(),
            experience=self.experience.value.strip(),
            hours=self.hours.value.strip()
        )

        channel = interaction.guild.get_channel(cfg['staff_apps_channel_id'])
        if not channel:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Channel Not Found",
                    description="The staff applications channel no longer exists. Ask an admin to reconfigure.",
                    color=0xFF1744
                ),
                ephemeral=True
            )
            return

        app_data = database.get_staff_application(app_id)
        embed = embeds.staff_application_embed(app_data, interaction.user)

        ping_content = None
        role_id = cfg.get('staff_apps_role_id')
        if role_id:
            ping_content = f"<@&{role_id}>"

        msg = await channel.send(content=ping_content, embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        database.set_staff_application_message(app_id, msg.id)

        await interaction.followup.send(
            embed=discord.Embed(
                title="Application Submitted",
                description=(
                    f"Your staff application has been submitted successfully.\n"
                    f"Application ID: **#{app_id}**\n\n"
                    "You will be notified when it's reviewed."
                ),
                color=0x00E676
            ),
            ephemeral=True
        )


class ApplyGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="apply", description="Staff application commands")

    @app_commands.command(name="staff", description="Submit a staff application.")
    async def staff(self, interaction: discord.Interaction):
        await interaction.response.send_modal(StaffApplicationModal())

    @app_commands.command(name="staffsetup", description="Configure the staff applications system.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Channel for staff applications",
        staff_role="Role to ping on new applications (optional)"
    )
    async def staffsetup(self, interaction: discord.Interaction, channel: discord.TextChannel, staff_role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['staff_apps_channel_id'] = channel.id
        if staff_role:
            cfg['staff_apps_role_id'] = staff_role.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        desc_lines = [
            f"**Channel:** {channel.mention}",
        ]
        if staff_role:
            desc_lines.append(f"**Staff Role:** {staff_role.mention}")
        desc_lines.append("\nMembers can apply using `/apply staff`")

        await interaction.followup.send(
            embed=discord.Embed(
                title="Staff Applications Configured",
                description="\n".join(desc_lines),
                color=0x00E676
            ),
            ephemeral=True
        )

    @app_commands.command(name="accept", description="Accept a staff application.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        application_id="The application ID to accept",
        note="Optional note to include"
    )
    async def accept(self, interaction: discord.Interaction, application_id: int, note: str = None):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(application_id)
        if not app_data:
            await interaction.followup.send(
                embed=discord.Embed(title="Not Found", description=f"Application #{application_id} not found.", color=0xFF1744),
                ephemeral=True
            )
            return

        if app_data['guild_id'] != interaction.guild.id:
            await interaction.followup.send(
                embed=discord.Embed(title="Wrong Server", description="This application belongs to another server.", color=0xFF1744),
                ephemeral=True
            )
            return

        if app_data['status'] != 'pending':
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Already Reviewed",
                    description=f"Application #{application_id} is already **{app_data['status']}**.",
                    color=0xFF9F00
                ),
                ephemeral=True
            )
            return

        database.update_staff_application_status(application_id, 'accepted', interaction.user.id, note or '')

        embed = embeds.staff_application_reviewed_embed(app_data, 'accepted', interaction.user, note)
        applicant = interaction.guild.get_member(app_data['user_id'])
        if applicant:
            try:
                await applicant.send(
                    embed=discord.Embed(
                        title="Application Accepted",
                        description=(
                            f"Your staff application in **{interaction.guild.name}** has been **accepted**!\n\n"
                            f"An admin will assign you the staff role shortly."
                            + (f"\n\nNote: {note}" if note else "")
                        ),
                        color=0x00E676
                    )
                )
            except discord.Forbidden:
                pass

        cfg = database.get_guild_config_v3(interaction.guild.id)
        if cfg and cfg.get('staff_apps_channel_id') and app_data.get('message_id'):
            channel = interaction.guild.get_channel(cfg['staff_apps_channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(app_data['message_id'])
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                except (discord.NotFound, discord.Forbidden):
                    pass

        await interaction.followup.send(
            embed=discord.Embed(
                title="Application Accepted",
                description=f"Application #{application_id} accepted. {applicant.mention if applicant else 'Applicant'} has been notified.",
                color=0x00E676
            ),
            ephemeral=True
        )

    @app_commands.command(name="reject", description="Reject a staff application.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        application_id="The application ID to reject",
        reason="Reason for rejection"
    )
    async def reject(self, interaction: discord.Interaction, application_id: int, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(application_id)
        if not app_data:
            await interaction.followup.send(
                embed=discord.Embed(title="Not Found", description=f"Application #{application_id} not found.", color=0xFF1744),
                ephemeral=True
            )
            return

        if app_data['guild_id'] != interaction.guild.id:
            await interaction.followup.send(
                embed=discord.Embed(title="Wrong Server", description="This application belongs to another server.", color=0xFF1744),
                ephemeral=True
            )
            return

        if app_data['status'] != 'pending':
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Already Reviewed",
                    description=f"Application #{application_id} is already **{app_data['status']}**.",
                    color=0xFF9F00
                ),
                ephemeral=True
            )
            return

        database.update_staff_application_status(application_id, 'rejected', interaction.user.id, reason)

        embed = embeds.staff_application_reviewed_embed(app_data, 'rejected', interaction.user, reason)
        applicant = interaction.guild.get_member(app_data['user_id'])
        if applicant:
            try:
                await applicant.send(
                    embed=discord.Embed(
                        title="Application Rejected",
                        description=(
                            f"Your staff application in **{interaction.guild.name}** has been **rejected**.\n\n"
                            f"**Reason:** {reason}\n\n"
                            "You can reapply after 7 days."
                        ),
                        color=0xFF1744
                    )
                )
            except discord.Forbidden:
                pass

        cfg = database.get_guild_config_v3(interaction.guild.id)
        if cfg and cfg.get('staff_apps_channel_id') and app_data.get('message_id'):
            channel = interaction.guild.get_channel(cfg['staff_apps_channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(app_data['message_id'])
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                except (discord.NotFound, discord.Forbidden):
                    pass

        await interaction.followup.send(
            embed=discord.Embed(
                title="Application Rejected",
                description=f"Application #{application_id} rejected. {applicant.mention if applicant else 'Applicant'} has been notified.",
                color=0xFF1744
            ),
            ephemeral=True
        )

    @app_commands.command(name="list", description="List staff applications.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(
        status_filter=[
            app_commands.Choice(name="Pending", value="pending"),
            app_commands.Choice(name="Accepted", value="accepted"),
            app_commands.Choice(name="Rejected", value="rejected"),
            app_commands.Choice(name="All", value="all"),
        ]
    )
    async def list_apps(self, interaction: discord.Interaction, status_filter: str = "pending"):
        await interaction.response.defer(ephemeral=True)

        status = None if status_filter == "all" else status_filter
        apps = database.get_staff_applications(interaction.guild.id, status=status)

        if not apps:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="No Applications",
                    description=f"No {status_filter} applications found.",
                    color=0x7289DA
                ),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Staff Applications — {status_filter.title()}",
            color=0x7289DA
        )

        lines = []
        for app in apps[:15]:
            status_emoji = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(app['status'], "⚪")
            lines.append(
                f"{status_emoji} **#{app['id']}** — <@{app['user_id']}> | IGN: `{app['ign']}` | Age: `{app['age']}` | {app['created_at'][:10]}"
            )

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Showing {len(apps[:15])} of {len(apps)} applications")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Check your staff application status.")
    async def status(self, interaction: discord.Interaction):
        apps = database.get_staff_applications(interaction.guild.id)
        my_apps = [a for a in apps if a['user_id'] == interaction.user.id]

        if not my_apps:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="No Applications",
                    description="You haven't submitted any staff applications in this server.",
                    color=0x7289DA
                ),
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Your Applications",
            color=0x7289DA
        )

        for app in my_apps[:5]:
            status_emoji = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(app['status'], "⚪")
            value = f"Status: {status_emoji} **{app['status'].title()}**\nSubmitted: {app['created_at'][:10]}"
            if app['status'] != 'pending':
                value += f"\nReviewed by: <@{app['reviewed_by']}>" if app.get('reviewed_by') else ""
                if app.get('review_note'):
                    value += f"\nNote: {app['review_note']}"
            embed.add_field(name=f"Application #{app['id']}", value=value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
