import datetime
import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

bot_ref = None

def set_bot_ref(bot):
    global bot_ref
    bot_ref = bot

class ServerGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="server", description="Server management commands")

    @app_commands.command(name="announce", description="Send an announcement to the announcement channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        title="Announcement title",
        message="Announcement message content",
        channel="Channel to send to (defaults to announcement channel)",
        ping_everyone="Whether to ping @everyone"
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        title: str,
        message: str,
        channel: discord.TextChannel = None,
        ping_everyone: bool = False
    ):
        await interaction.response.defer(ephemeral=True)

        embed = embeds.premium_announcement_embed(title, message)
        target = channel or interaction.channel

        content = "@everyone" if ping_everyone else None
        await target.send(content=content, embed=embed)
        await interaction.followup.send(f"✅ Announcement sent to {target.mention}!", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        member="Member to ban",
        reason="Reason for the ban",
        delete_days="Delete messages from this many days"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
        delete_days: int = 0
    ):
        await interaction.response.defer(ephemeral=True)

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.followup.send("❌ You cannot ban someone with a higher or equal role.", ephemeral=True)
            return

        try:
            await member.ban(reason=reason, delete_message_days=delete_days)
            embed = discord.Embed(
                title="🔨 MEMBER BANNED",
                description=f"**{member}** has been banned.",
                color=embeds.COLOR_RED
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to ban that member.", ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        member="Member to kick",
        reason="Reason for the kick"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer(ephemeral=True)

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.followup.send("❌ You cannot kick someone with a higher or equal role.", ephemeral=True)
            return

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="👢 MEMBER KICKED",
                description=f"**{member}** has been kicked.",
                color=embeds.COLOR_AMBER
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to kick that member.", ephemeral=True)

    @app_commands.command(name="mute", description="Timeout a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="Member to mute",
        minutes="Duration in minutes (default 10)",
        reason="Reason for the mute"
    )
    async def mute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int = 10,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            duration = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            embed = discord.Embed(
                title="🔇 MEMBER MUTED",
                description=f"**{member}** has been timed out for {minutes} minutes.",
                color=embeds.COLOR_AMBER
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to mute that member.", ephemeral=True)

    @app_commands.command(name="unmute", description="Remove timeout from a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="Member to unmute"
    )
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            await member.timeout(None)
            await interaction.followup.send(f"✅ **{member}** has been unmuted.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to unmute that member.", ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel (disable send messages for @everyone).")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        channel="Channel to lock (defaults to current)",
        reason="Reason for locking"
    )
    async def lock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        reason: str = "No reason provided"
    ):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel

        try:
            overwrite = target.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = False
            await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)

            embed = discord.Embed(
                title="🔒 CHANNEL LOCKED",
                description=f"{target.mention} has been locked.",
                color=embeds.COLOR_RED
            )
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            await target.send(embed=embed)
            await interaction.followup.send(f"✅ {target.mention} locked.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to lock channels.", ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock a channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        channel="Channel to unlock (defaults to current)"
    )
    async def unlock(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel

        try:
            overwrite = target.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = None
            await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)

            embed = discord.Embed(
                title="🔓 CHANNEL UNLOCKED",
                description=f"{target.mention} has been unlocked.",
                color=embeds.COLOR_GREEN
            )
            await target.send(embed=embed)
            await interaction.followup.send(f"✅ {target.mention} unlocked.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to unlock channels.", ephemeral=True)

    @app_commands.command(name="purge", description="Delete multiple messages from a channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        amount="Number of messages to delete (max 100)",
        channel="Channel to purge (defaults to current)"
    )
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: int,
        channel: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel

        if amount < 1 or amount > 100:
            await interaction.followup.send("❌ Amount must be between 1 and 100.", ephemeral=True)
            return

        deleted = await target.purge(limit=amount)
        await interaction.followup.send(f"✅ Deleted {len(deleted)} messages in {target.mention}.", ephemeral=True)

    @app_commands.command(name="nick", description="Change a member's nickname.")
    @app_commands.checks.has_permissions(manage_nicknames=True)
    @app_commands.describe(
        member="Member to rename",
        nickname="New nickname (leave blank to reset)"
    )
    async def nick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        nickname: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        try:
            await member.edit(nick=nickname)
            if nickname:
                await interaction.followup.send(f"✅ **{member}** nickname set to `{nickname}`.", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ **{member}** nickname reset.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to change that member's nickname.", ephemeral=True)

    @app_commands.command(name="role", description="Add or remove a role from a member.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.describe(
        member="Member to modify",
        role="Role to add or remove",
        action="Whether to add or remove the role"
    )
    async def role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        action: str = "add"
    ):
        await interaction.response.defer(ephemeral=True)

        if role >= interaction.guild.me.top_role:
            await interaction.followup.send("❌ I cannot manage that role (it's higher than my highest role).", ephemeral=True)
            return

        try:
            if action.lower() == "add":
                if role in member.roles:
                    await interaction.followup.send(f"⚠️ **{member}** already has {role.mention}.", ephemeral=True)
                    return
                await member.add_roles(role)
                await interaction.followup.send(f"✅ Added {role.mention} to **{member}**.", ephemeral=True)
            elif action.lower() == "remove":
                if role not in member.roles:
                    await interaction.followup.send(f"⚠️ **{member}** doesn't have {role.mention}.", ephemeral=True)
                    return
                await member.remove_roles(role)
                await interaction.followup.send(f"✅ Removed {role.mention} from **{member}**.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Invalid action. Use `add` or `remove`.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage roles.", ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode on a channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(
        seconds="Slowmode in seconds (0 to disable, max 21600)",
        channel="Channel to set slowmode on (defaults to current)"
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: int,
        channel: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel

        if seconds < 0 or seconds > 21600:
            await interaction.followup.send("❌ Seconds must be between 0 and 21600.", ephemeral=True)
            return

        try:
            await target.edit(slowmode_delay=seconds)
            if seconds > 0:
                await interaction.followup.send(f"✅ Slowmode set to {seconds}s in {target.mention}.", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Slowmode disabled in {target.mention}.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to edit this channel.", ephemeral=True)

    @app_commands.command(name="rules", description="Send the server rules to a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Channel to send rules to (defaults to current)"
    )
    async def rules(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None
    ):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel

        embed = embeds.rules_embed(interaction.guild)

        await target.send(embed=embed)
        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['rules_channel_id'] = target.id
        database.save_guild_config_v3(interaction.guild_id, cfg)
        await interaction.followup.send(f"✅ Rules posted in {target.mention}!", ephemeral=True)

    @app_commands.command(name="setname", description="Change the bot's username.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(name="New username for the bot")
    async def setname(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        if not bot_ref:
            await interaction.followup.send("❌ Bot reference not set.", ephemeral=True)
            return
        try:
            await bot_ref.user.edit(username=name)
            await interaction.followup.send(f"✅ Bot name changed to **{name}**!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to change name: {e}", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.defer(ephemeral=True)
        database.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        warnings = database.get_warnings(interaction.guild_id, member.id)
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} has been warned.",
            color=embeds.COLOR_AMBER
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Warnings", value=f"`{len(warnings)}` total", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="warnings", description="View warnings for a member.")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(member="Member to check warnings for")
    async def warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        warnings = database.get_warnings(interaction.guild_id, member.id)
        if not warnings:
            await interaction.followup.send(f"✅ {member.mention} has **no warnings**.", ephemeral=True)
            return
        lines = []
        for w in warnings[:10]:
            lines.append(f"`#{w['id']}` — {w['reason']} — <@{w['moderator_id']}>")
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.display_name}",
            description="\n".join(lines),
            color=embeds.COLOR_AMBER
        )
        embed.set_footer(text=f"Total: {len(warnings)} warnings")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarn", description="Clear all warnings for a member.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Member to clear warnings for")
    async def clearwarn(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        database.clear_warnings(interaction.guild_id, member.id)
        await interaction.followup.send(f"✅ Cleared all warnings for {member.mention}.", ephemeral=True)

    @app_commands.command(name="nuke", description="Clone and delete a channel (nuke it).")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(channel="Channel to nuke (defaults to current)")
    async def nuke(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        target = channel or interaction.channel
        pos = target.position
        new = await target.clone(reason=f"Nuked by {interaction.user}")
        await target.delete()
        await new.edit(position=pos)
        embed = discord.Embed(
            title="💣 CHANNEL NUKED",
            description=f"This channel has been nuked by {interaction.user.mention}",
            color=embeds.COLOR_RED
        )
        await new.send(embed=embed)
        await interaction.followup.send(f"✅ {new.mention} has been nuked!", ephemeral=True)

    @app_commands.command(name="addemoji", description="Add an emoji to the server.")
    @app_commands.checks.has_permissions(manage_expressions=True)
    @app_commands.describe(name="Emoji name", emoji="The emoji image file (upload)")
    async def addemoji(self, interaction: discord.Interaction, name: str, emoji: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        if not emoji.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            await interaction.followup.send("❌ File must be a PNG, JPG, or GIF image.", ephemeral=True)
            return
        try:
            data = await emoji.read()
            new_emoji = await interaction.guild.create_custom_emoji(name=name, image=data, reason=f"Added by {interaction.user}")
            await interaction.followup.send(f"✅ Emoji {new_emoji} `:{name}:` added!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to add emoji: {e}", ephemeral=True)

    @app_commands.command(name="lockdown", description="Lockdown the server (lock all channels).")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for channel in interaction.guild.channels:
            try:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
                    count += 1
            except:
                pass
        embed = discord.Embed(
            title="🔒 SERVER LOCKDOWN",
            description=f"**{count}** channels have been locked by {interaction.user.mention}.",
            color=embeds.COLOR_RED
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        if interaction.guild.system_channel:
            await interaction.guild.system_channel.send(embed=embed)

    @app_commands.command(name="unlockdown", description="Undo a server lockdown.")
    @app_commands.checks.has_permissions(administrator=True)
    async def unlockdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for channel in interaction.guild.channels:
            try:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(interaction.guild.default_role, send_messages=None)
                    count += 1
            except:
                pass
        embed = discord.Embed(
            title="🔓 SERVER UNLOCKED",
            description=f"**{count}** channels have been unlocked by {interaction.user.mention}.",
            color=embeds.COLOR_GREEN
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        if interaction.guild.system_channel:
            await interaction.guild.system_channel.send(embed=embed)
