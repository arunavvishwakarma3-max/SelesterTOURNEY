import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import asyncio
import json

APP_TYPES = {
    "helper": {
        "name": "Helper",
        "emoji": "🛡️",
        "color": 0x3498DB,
        "description": "Help new players and maintain order",
        "questions": [
            ("IGN", "What is your Minecraft in-game name?", 2, 24),
            ("Age", "How old are you?", 1, 3),
            ("Hours", "How many hours per day can you be active?", 1, 20),
            ("Why", "Why do you want to be a Helper?", 20, 1000),
            ("Experience", "Do you have any previous staff experience? If so, where?", 10, 1000),
            ("Scenario", "How would you handle a player breaking rules in chat?", 20, 1000),
        ]
    },
    "admin": {
        "name": "Admin",
        "emoji": "⚡",
        "color": 0xE74C3C,
        "description": "Full admin powers to manage staff and server",
        "questions": [
            ("IGN", "What is your Minecraft in-game name?", 2, 24),
            ("Age", "How old are you?", 1, 3),
            ("Hours", "How many hours per day can you be active?", 1, 20),
            ("Why", "Why do you want to be an Admin?", 20, 1000),
            ("Experience", "Do you have any previous staff experience? If so, where?", 10, 1000),
            ("Friend Scenario", "How would you handle a friend breaking rules?", 20, 1000),
            ("Disagreement", "What would you do if you disagree with another staff member's decision?", 20, 1000),
        ]
    },
    "tier_tester": {
        "name": "Tier Tester",
        "emoji": "🎯",
        "color": 0x9B59B6,
        "description": "Evaluate player skills and assign tiers",
        "questions": [
            ("IGN", "What is your Minecraft in-game name?", 2, 24),
            ("Age", "How old are you?", 1, 3),
            ("Gamemode", "What gamemode(s) do you want to test for?", 2, 100),
            ("Current Tier", "What is your current tier in that gamemode?", 2, 50),
            ("Hours", "How many hours per day can you be active?", 1, 20),
            ("Why", "Why do you want to be a Tier Tester?", 20, 1000),
            ("Experience", "Do you have experience in competitive play?", 10, 1000),
        ]
    },
    "staff_report": {
        "name": "Staff Report",
        "emoji": "🚨",
        "color": 0xFF1744,
        "description": "Report a staff member for misconduct",
        "questions": [
            ("Target", "Who are you reporting?", 2, 100),
            ("What Happened", "What did they do?", 20, 1000),
            ("When", "When did this happen?", 5, 100),
            ("Evidence", "Do you have evidence? (screenshots, messages, etc.)", 10, 1000),
            ("Details", "Any additional details?", 10, 1000),
        ]
    }
}

active_applications = {}


class ApplicationState:
    def __init__(self, guild_id, user_id, app_type, thread):
        self.guild_id = guild_id
        self.user_id = user_id
        self.app_type = app_type
        self.thread = thread
        self.current_question = 0
        self.answers = {}


class ApplicationPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply Helper", style=discord.ButtonStyle.primary, emoji="🛡️", custom_id="app_panel_helper")
    async def helper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_application(interaction, "helper")

    @discord.ui.button(label="Apply Admin", style=discord.ButtonStyle.danger, emoji="⚡", custom_id="app_panel_admin")
    async def admin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_application(interaction, "admin")

    @discord.ui.button(label="Apply Tier Tester", style=discord.ButtonStyle.secondary, emoji="🎯", custom_id="app_panel_tier")
    async def tier_tester_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_application(interaction, "tier_tester")

    @discord.ui.button(label="Staff Report", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="app_panel_report")
    async def staff_report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_application(interaction, "staff_report")


class ApplicationReviewView(discord.ui.View):
    def __init__(self, app_id: int):
        super().__init__(timeout=None)
        self.app_id = app_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅", custom_id="app_review_accept")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(self.app_id)
        if not app_data:
            await interaction.followup.send("Application not found.", ephemeral=True)
            return
        if app_data['status'] != 'pending':
            await interaction.followup.send(f"Already **{app_data['status']}**.", ephemeral=True)
            return

        database.update_staff_application_status(self.app_id, 'accepted', interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = 0x00E676
        embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"ACCEPTED • ID: {self.app_id} • Celestia")
        await interaction.message.edit(embed=embed, view=None)

        member = interaction.guild.get_member(app_data['user_id'])
        if member:
            try:
                app_type = app_data.get('application_type', 'staff')
                type_name = APP_TYPES.get(app_type, {}).get('name', 'Staff')
                await member.send(
                    embed=discord.Embed(
                        title="Application Accepted!",
                        description=(
                            f"Your **{type_name}** application in **{interaction.guild.name}** "
                            f"has been **accepted**!\n\nAn admin will assign you the role shortly."
                        ),
                        color=0x00E676
                    )
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send("Application accepted.", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌", custom_id="app_review_reject")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(self.app_id)
        if not app_data:
            await interaction.followup.send("Application not found.", ephemeral=True)
            return
        if app_data['status'] != 'pending':
            await interaction.followup.send(f"Already **{app_data['status']}**.", ephemeral=True)
            return

        database.update_staff_application_status(self.app_id, 'rejected', interaction.user.id)

        embed = interaction.message.embeds[0]
        embed.color = 0xFF1744
        embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"REJECTED • ID: {self.app_id} • Celestia")
        await interaction.message.edit(embed=embed, view=None)

        member = interaction.guild.get_member(app_data['user_id'])
        if member:
            try:
                app_type = app_data.get('application_type', 'staff')
                type_name = APP_TYPES.get(app_type, {}).get('name', 'Staff')
                await member.send(
                    embed=discord.Embed(
                        title="Application Rejected",
                        description=(
                            f"Your **{type_name}** application in **{interaction.guild.name}** "
                            f"has been **rejected**.\n\nYou can reapply after 7 days."
                        ),
                        color=0xFF1744
                    )
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send("Application rejected.", ephemeral=True)


async def start_application(interaction: discord.Interaction, app_type: str):
    key = (interaction.guild_id, interaction.user.id)
    if key in active_applications:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Already Applying",
                description="You have an active application. Finish or wait for it to be reviewed.",
                color=0xFF9F00
            ),
            ephemeral=True
        )
        return

    pending = database.get_pending_staff_application(interaction.guild_id, interaction.user.id)
    if pending:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Already Applied",
                description=f"You already have a pending application (#{pending['id']}).",
                color=0xFF9F00
            ),
            ephemeral=True
        )
        return

    app_info = APP_TYPES[app_type]

    try:
        thread = await interaction.channel.create_thread(
            name=f"{app_type.replace('_', '-')}-app-{interaction.user.name}",
            auto_archive_duration=60,
            type=discord.ChannelType.private_thread,
            reason="Application"
        )
        await thread.add_user(interaction.user)
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Permission Error",
                description="I can't create threads here. Contact an admin.",
                color=0xFF1744
            ),
            ephemeral=True
        )
        return

    welcome = discord.Embed(
        title=f"{app_info['emoji']} {app_info['name']} Application",
        description=(
            f"Welcome {interaction.user.mention}!\n\n"
            f"You are applying for **{app_info['name']}**.\n"
            "Answer each question by typing your response.\n\n"
            "**Be honest and take your time.**"
        ),
        color=app_info['color']
    )
    await thread.send(embed=welcome)

    state = ApplicationState(interaction.guild_id, interaction.user.id, app_type, thread)
    active_applications[key] = state

    await _ask_question(state)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="Application Started",
            description=f"Go to {thread.mention} to complete your **{app_info['name']}** application.",
            color=0x00E676
        ),
        ephemeral=True
    )


async def _ask_question(state):
    app_info = APP_TYPES[state.app_type]
    _, question_text, min_len, max_len = app_info['questions'][state.current_question]

    embed = discord.Embed(
        title=f"Question {state.current_question + 1}/{len(app_info['questions'])}",
        description=question_text,
        color=app_info['color']
    )
    embed.set_footer(text=f"Min {min_len} • Max {max_len} characters")
    await state.thread.send(embed=embed)


async def handle_application_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return False

    key = (message.guild.id, message.author.id)
    if key not in active_applications:
        return False

    state = active_applications[key]
    if message.channel.id != state.thread.id:
        return False

    app_info = APP_TYPES[state.app_type]
    _, question_text, min_len, max_len = app_info['questions'][state.current_question]

    content = message.content.strip()

    if len(content) < min_len:
        await message.channel.send(
            embed=discord.Embed(description=f"Too short. Minimum **{min_len}** characters.", color=0xFF1744),
            delete_after=5
        )
        return True

    if len(content) > max_len:
        await message.channel.send(
            embed=discord.Embed(description=f"Too long. Maximum **{max_len}** characters.", color=0xFF1744),
            delete_after=5
        )
        return True

    state.answers[app_info['questions'][state.current_question][0]] = content
    state.current_question += 1

    if state.current_question < len(app_info['questions']):
        await _ask_question(state)
    else:
        await _complete_application(state)

    return True


async def _complete_application(state):
    app_info = APP_TYPES[state.app_type]
    member = state.thread.guild.get_member(state.user_id)

    answers_json = json.dumps(state.answers)

    app_id = database.create_staff_application(
        guild_id=state.guild_id,
        user_id=state.user_id,
        ign=state.answers.get("IGN", ""),
        age=state.answers.get("Age", ""),
        why=state.answers.get("Why", state.answers.get("What Happened", "")),
        experience=state.answers.get("Experience", state.answers.get("Details", "")),
        hours=state.answers.get("Hours", ""),
    )
    database.update_staff_application_type(app_id, state.app_type)
    database.update_staff_application_data(app_id, answers_json)
    database.set_staff_application_channel(app_id, state.thread.id)

    review_embed = embeds.staff_application_review_embed(
        app_id=app_id,
        app_type=state.app_type,
        member=member,
        answers=state.answers
    )

    cfg = database.get_guild_config_v3(state.guild_id)
    review_channel_id = cfg.get('application_review_channel_id') if cfg else None

    if review_channel_id:
        review_channel = state.thread.guild.get_channel(review_channel_id)
        if review_channel:
            view = ApplicationReviewView(app_id)
            msg = await review_channel.send(embed=review_embed, view=view)
            database.set_staff_application_message(app_id, msg.id)

    await state.thread.send(
        embed=discord.Embed(
            title="Application Submitted!",
            description=(
                "Your application has been submitted for review!\n\n"
                "You will be DM'd when it's reviewed.\n"
                "This thread will be archived shortly."
            ),
            color=0x00E676
        )
    )

    await asyncio.sleep(5)
    try:
        await state.thread.edit(archived=True, locked=True)
    except Exception:
        pass

    key = (state.guild_id, state.user_id)
    if key in active_applications:
        del active_applications[key]


class ApplyPanelGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="app", description="Application panel commands")

    @app_commands.command(name="panel", description="Post the application panel in a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel to post the panel in")
    async def panel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        embed = embeds.application_panel_embed()
        view = ApplicationPanelView()
        await channel.send(embed=embed, view=view)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['application_panel_channel_id'] = channel.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        await interaction.followup.send(
            embed=discord.Embed(
                title="Panel Posted",
                description=f"Application panel posted in {channel.mention}",
                color=0x00E676
            ),
            ephemeral=True
        )

    @app_commands.command(name="reviewchannel", description="Set the channel where applications are sent for review.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel for application reviews")
    async def reviewchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['application_review_channel_id'] = channel.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        await interaction.followup.send(
            embed=discord.Embed(
                title="Review Channel Set",
                description=f"Applications will be sent to {channel.mention} for review.",
                color=0x00E676
            ),
            ephemeral=True
        )

    @app_commands.command(name="refresh", description="Refresh the application panel embed (same channel, no restart needed).")
    @app_commands.checks.has_permissions(administrator=True)
    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('application_panel_channel_id'):
            await interaction.followup.send(
                embed=discord.Embed(title="Not Configured", description="No panel channel set. Use `/app panel` first.", color=0xFF1744),
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(cfg['application_panel_channel_id'])
        if not channel:
            await interaction.followup.send(
                embed=discord.Embed(title="Channel Not Found", description="The panel channel was deleted. Use `/app panel` to set a new one.", color=0xFF1744),
                ephemeral=True
            )
            return

        async for msg in channel.history(limit=10):
            if msg.author == interaction.guild.me and msg.embeds:
                embed_title = msg.embeds[0].title or ""
                if "Applications" in embed_title:
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    break

        embed = embeds.application_panel_embed()
        view = ApplicationPanelView()
        await channel.send(embed=embed, view=view)

        await interaction.followup.send(
            embed=discord.Embed(
                title="Panel Refreshed",
                description=f"Application panel updated in {channel.mention}",
                color=0x00E676
            ),
            ephemeral=True
        )

    @app_commands.command(name="accept", description="Accept an application.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(application_id="Application ID", role="Role to assign (optional)")
    async def accept(self, interaction: discord.Interaction, application_id: int, role: discord.Role = None):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(application_id)
        if not app_data:
            await interaction.followup.send("Application not found.", ephemeral=True)
            return
        if app_data['guild_id'] != interaction.guild.id:
            await interaction.followup.send("Wrong server.", ephemeral=True)
            return
        if app_data['status'] != 'pending':
            await interaction.followup.send(f"Already **{app_data['status']}**.", ephemeral=True)
            return

        database.update_staff_application_status(application_id, 'accepted', interaction.user.id)

        member = interaction.guild.get_member(app_data['user_id'])
        if member and role:
            try:
                await member.add_roles(role, reason=f"Application #{application_id} accepted")
            except discord.Forbidden:
                pass

        if app_data.get('message_id') and app_data.get('channel_id'):
            ch = interaction.guild.get_channel(app_data['channel_id'])
            if ch:
                try:
                    msg = await ch.fetch_message(app_data['message_id'])
                    embed = msg.embeds[0]
                    embed.color = 0x00E676
                    embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
                    if role:
                        embed.add_field(name="Role Given", value=role.mention, inline=True)
                    embed.set_footer(text=f"ACCEPTED • ID: {application_id} • Celestia")
                    await msg.edit(embed=embed, view=None)
                except Exception:
                    pass

        if member:
            try:
                app_type = app_data.get('application_type', 'staff')
                type_name = APP_TYPES.get(app_type, {}).get('name', 'Staff')
                dm_desc = f"Your **{type_name}** application in **{interaction.guild.name}** has been **accepted**!"
                if role:
                    dm_desc += f"\n\nYou've been given the **{role.name}** role."
                await member.send(
                    embed=discord.Embed(title="Application Accepted!", description=dm_desc, color=0x00E676)
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send(f"Application #{application_id} accepted.", ephemeral=True)

    @app_commands.command(name="reject", description="Reject an application.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(application_id="Application ID", reason="Reason")
    async def reject(self, interaction: discord.Interaction, application_id: int, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)

        app_data = database.get_staff_application(application_id)
        if not app_data:
            await interaction.followup.send("Application not found.", ephemeral=True)
            return
        if app_data['guild_id'] != interaction.guild.id:
            await interaction.followup.send("Wrong server.", ephemeral=True)
            return
        if app_data['status'] != 'pending':
            await interaction.followup.send(f"Already **{app_data['status']}**.", ephemeral=True)
            return

        database.update_staff_application_status(application_id, 'rejected', interaction.user.id, reason)

        if app_data.get('message_id') and app_data.get('channel_id'):
            ch = interaction.guild.get_channel(app_data['channel_id'])
            if ch:
                try:
                    msg = await ch.fetch_message(app_data['message_id'])
                    embed = msg.embeds[0]
                    embed.color = 0xFF1744
                    embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
                    embed.add_field(name="Reason", value=reason, inline=False)
                    embed.set_footer(text=f"REJECTED • ID: {application_id} • Celestia")
                    await msg.edit(embed=embed, view=None)
                except Exception:
                    pass

        member = interaction.guild.get_member(app_data['user_id'])
        if member:
            try:
                app_type = app_data.get('application_type', 'staff')
                type_name = APP_TYPES.get(app_type, {}).get('name', 'Staff')
                await member.send(
                    embed=discord.Embed(
                        title="Application Rejected",
                        description=(
                            f"Your **{type_name}** application in **{interaction.guild.name}** "
                            f"has been **rejected**.\n\n**Reason:** {reason}\n\n"
                            "You can reapply after 7 days."
                        ),
                        color=0xFF1744
                    )
                )
            except discord.Forbidden:
                pass

        await interaction.followup.send(f"Application #{application_id} rejected.", ephemeral=True)

    @app_commands.command(name="list", description="List applications.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(status_filter=[
        app_commands.Choice(name="Pending", value="pending"),
        app_commands.Choice(name="Accepted", value="accepted"),
        app_commands.Choice(name="Rejected", value="rejected"),
        app_commands.Choice(name="All", value="all"),
    ])
    async def list_apps(self, interaction: discord.Interaction, status_filter: str = "pending"):
        await interaction.response.defer(ephemeral=True)

        status = None if status_filter == "all" else status_filter
        apps = database.get_staff_applications(interaction.guild.id, status=status)

        if not apps:
            await interaction.followup.send(
                embed=discord.Embed(title="No Applications", description=f"No {status_filter} applications.", color=0x7289DA),
                ephemeral=True
            )
            return

        embed = discord.Embed(title=f"Applications — {status_filter.title()}", color=0x7289DA)

        lines = []
        for app in apps[:15]:
            se = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(app['status'], "⚪")
            at = app.get('application_type', 'staff')
            ai = APP_TYPES.get(at, {})
            te = ai.get('emoji', '📋')
            lines.append(f"{se} {te} **#{app['id']}** — <@{app['user_id']}> | `{app['ign']}` | {app['created_at'][:10]}")

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"{min(len(apps), 15)} of {len(apps)} shown")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="status", description="Check your application status.")
    async def status(self, interaction: discord.Interaction):
        apps = database.get_staff_applications(interaction.guild.id)
        my_apps = [a for a in apps if a['user_id'] == interaction.user.id]

        if not my_apps:
            await interaction.response.send_message(
                embed=discord.Embed(title="No Applications", description="You haven't applied yet.", color=0x7289DA),
                ephemeral=True
            )
            return

        embed = discord.Embed(title="Your Applications", color=0x7289DA)
        for app in my_apps[:5]:
            se = {"pending": "🟡", "accepted": "🟢", "rejected": "🔴"}.get(app['status'], "⚪")
            at = app.get('application_type', 'staff')
            ai = APP_TYPES.get(at, {})
            te = ai.get('emoji', '📋')
            val = f"Status: {se} **{app['status'].title()}**\nType: {te} {ai.get('name', 'Staff')}\nSubmitted: {app['created_at'][:10]}"
            if app.get('review_note'):
                val += f"\nNote: {app['review_note']}"
            embed.add_field(name=f"#{app['id']}", value=val, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
