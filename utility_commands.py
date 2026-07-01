import datetime
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import embeds

bot_start_time = None

def set_start_time():
    global bot_start_time
    bot_start_time = datetime.datetime.utcnow()

class UtilityGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="utility", description="General utility commands")

    @app_commands.command(name="ping", description="Check bot latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(interaction.client.latency * 1000)
        embed = discord.Embed(
            title="🏓 PONG!",
            description=f"**Latency:** `{latency}ms`\n**Websocket:** `{latency}ms`",
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="Celestia • Utility")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="Show how long the bot has been online.")
    async def uptime(self, interaction: discord.Interaction):
        if not bot_start_time:
            await interaction.response.send_message("❌ Bot start time not recorded.", ephemeral=True)
            return
        delta = datetime.datetime.utcnow() - bot_start_time
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        embed = discord.Embed(
            title="⏱️ BOT UPTIME",
            description=f"`{days}d {hours}h {minutes}m {seconds}s`",
            color=embeds.COLOR_BLUE
        )
        embed.set_footer(text="Celestia • Utility")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Get a user's avatar.")
    @app_commands.describe(member="Member to get avatar of (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(
            title=f"🖼️ {member.display_name}'s Avatar",
            color=member.color if member.color.value else embeds.COLOR_BLUE
        )
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="banner", description="Get a user's banner.")
    @app_commands.describe(member="Member to get banner of (defaults to you)")
    async def banner(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        user = await interaction.client.fetch_user(member.id)
        if user.banner:
            embed = discord.Embed(
                title=f"🖼️ {member.display_name}'s Banner",
                color=member.color if member.color.value else embeds.COLOR_BLUE
            )
            embed.set_image(url=user.banner.url)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {member.display_name} has no banner.", ephemeral=True)

    @app_commands.command(name="userinfo", description="View detailed info about a user.")
    @app_commands.describe(member="Member to get info about (defaults to you)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        roles = [r.mention for r in member.roles if r != interaction.guild.default_role]
        created = member.created_at.strftime("%b %d, %Y")
        joined = member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown"

        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            color=member.color if member.color.value else embeds.COLOR_BLUE
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="**Username**", value=f"`{member}`", inline=True)
        embed.add_field(name="**ID**", value=f"`{member.id}`", inline=True)
        embed.add_field(name="**Bot**", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="**Created**", value=f"`{created}`", inline=True)
        embed.add_field(name="**Joined**", value=f"`{joined}`", inline=True)
        embed.add_field(name="**Top Role**", value=member.top_role.mention, inline=True)
        embed.add_field(name=f"**Roles ({len(roles)})**", value=" ".join(roles[:10]) or "None", inline=False)
        embed.set_footer(text=f"Celestia • User Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="View detailed server information.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        created = guild.created_at.strftime("%b %d, %Y")
        bots = sum(1 for m in guild.members if m.bot)
        humans = guild.member_count - bots
        channels = len(guild.channels)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count

        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=embeds.COLOR_PURPLE
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="**ID**", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="**Owner**", value=guild.owner.mention, inline=True)
        embed.add_field(name="**Created**", value=f"`{created}`", inline=True)
        embed.add_field(name="**Members**", value=f"`{guild.member_count}` (👤 {humans} 🤖 {bots})", inline=True)
        embed.add_field(name="**Channels**", value=f"`{channels}` (📝 {text_channels} 🔊 {voice_channels} 📁 {categories})", inline=True)
        embed.add_field(name="**Roles**", value=f"`{len(guild.roles)}`", inline=True)
        embed.add_field(name="**Boosts**", value=f"`Level {boost_level}` ({boost_count} boosts)", inline=True)
        embed.add_field(name="**Emojis**", value=f"`{len(guild.emojis)}`", inline=True)
        embed.set_footer(text="Celestia • Server Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roleinfo", description="View information about a role.")
    @app_commands.describe(role="Role to get info about")
    async def roleinfo(self, interaction: discord.Interaction, role: discord.Role):
        created = role.created_at.strftime("%b %d, %Y")
        perm_list = [perm.replace("_", " ").title() for perm, val in role.permissions if val]
        perms = ", ".join(perm_list[:10]) if perm_list else "None"
        if len(perm_list) > 10:
            perms += f" *(+{len(perm_list) - 10} more)*"

        embed = discord.Embed(title=f"🔍 {role.name}", color=role.color if role.color.value else embeds.COLOR_DARK)
        embed.add_field(name="**ID**", value=f"`{role.id}`", inline=True)
        embed.add_field(name="**Color**", value=f"`{role.color}`", inline=True)
        embed.add_field(name="**Position**", value=f"`{role.position}`", inline=True)
        embed.add_field(name="**Mentionable**", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="**Displayed Separately**", value="Yes" if role.hoist else "No", inline=True)
        embed.add_field(name="**Members**", value=f"`{len(role.members)}`", inline=True)
        embed.add_field(name="**Created**", value=f"`{created}`", inline=True)
        embed.add_field(name="**Key Permissions**", value=perms, inline=False)
        embed.set_footer(text="Celestia • Role Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="View information about a channel.")
    @app_commands.describe(channel="Channel to get info about (defaults to current)")
    async def channelinfo(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        created = channel.created_at.strftime("%b %d, %Y")
        embed = discord.Embed(
            title=f"#️⃣ {channel.name}",
            color=embeds.COLOR_BLUE
        )
        embed.add_field(name="**ID**", value=f"`{channel.id}`", inline=True)
        embed.add_field(name="**Type**", value=f"`{str(channel.type).title()}`", inline=True)
        embed.add_field(name="**Category**", value=f"`{channel.category.name if channel.category else 'None'}`", inline=True)
        embed.add_field(name="**Topic**", value=channel.topic or "No topic", inline=False)
        embed.add_field(name="**Slowmode**", value=f"`{channel.slowmode_delay}s`" if channel.slowmode_delay else "`Disabled`", inline=True)
        embed.add_field(name="**NSFW**", value="Yes" if channel.nsfw else "No", inline=True)
        embed.add_field(name="**Created**", value=f"`{created}`", inline=True)
        embed.add_field(name="**Position**", value=f"`{channel.position}`", inline=True)
        embed.set_footer(text="Celestia • Channel Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botinfo", description="View bot information and stats.")
    async def botinfo(self, interaction: discord.Interaction):
        bot = interaction.client
        total_guilds = len(bot.guilds)
        total_users = sum(g.member_count for g in bot.guilds)
        total_channels = sum(len(g.channels) for g in bot.guilds)
        commands_count = len(bot.tree._global_commands)

        embed = discord.Embed(
            title="🤖 Celestia",
            description="**The ultimate tournament & server management bot.**",
            color=embeds.COLOR_PURPLE
        )
        if bot.user:
            embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.add_field(name="**Servers**", value=f"`{total_guilds}`", inline=True)
        embed.add_field(name="**Users**", value=f"`{total_users:,}`", inline=True)
        embed.add_field(name="**Channels**", value=f"`{total_channels}`", inline=True)
        embed.add_field(name="**Commands**", value=f"`{commands_count}`", inline=True)
        embed.add_field(name="**Library**", value="`discord.py`", inline=True)
        if bot_start_time:
            delta = datetime.datetime.utcnow() - bot_start_time
            embed.add_field(name="**Uptime**", value=f"`{delta.days}d {delta.seconds//3600}h`", inline=True)
        embed.set_footer(text="Celestia • Bot Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="membercount", description="View the server member count breakdown.")
    async def membercount(self, interaction: discord.Interaction):
        guild = interaction.guild
        total = guild.member_count
        bots = sum(1 for m in guild.members if m.bot)
        humans = total - bots
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        embed = discord.Embed(
            title=f"👥 {guild.name} — Member Count",
            color=embeds.COLOR_GREEN
        )
        embed.add_field(name="**Total**", value=f"`{total}`", inline=True)
        embed.add_field(name="**Humans**", value=f"`{humans}`", inline=True)
        embed.add_field(name="**Bots**", value=f"`{bots}`", inline=True)
        embed.add_field(name="**Online**", value=f"`{online}`", inline=True)
        embed.set_footer(text="Celestia • Member Count")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roles", description="List all roles in the server.")
    async def roles(self, interaction: discord.Interaction):
        roles = interaction.guild.roles[1:]
        roles = sorted(roles, key=lambda r: r.position, reverse=True)
        lines = []
        for r in roles:
            lines.append(f"{r.mention} — `{len(r.members)} members`")
        chunks = [lines[i:i+15] for i in range(0, len(lines), 15)]
        embed = discord.Embed(
            title=f"📋 Server Roles ({len(roles)})",
            description="\n".join(chunks[0]),
            color=embeds.COLOR_BLUE
        )
        if len(chunks) > 1:
            embed.set_footer(text=f"Page 1/{len(chunks)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emojis", description="List all emojis in the server.")
    async def emojis(self, interaction: discord.Interaction):
        emojis = interaction.guild.emojis
        if not emojis:
            await interaction.response.send_message("❌ No custom emojis in this server.", ephemeral=True)
            return
        lines = [f"{e} `:{e.name}:` — ID: `{e.id}`" for e in emojis[:50]]
        embed = discord.Embed(
            title=f"😀 Server Emojis ({len(emojis)})",
            description="\n".join(lines),
            color=embeds.COLOR_GOLD
        )
        if len(emojis) > 50:
            embed.set_footer(text=f"Showing 50/{len(emojis)} emojis")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invite", description="Get the bot's invite link.")
    async def invite(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🔗 Invite Celestia",
            description="Click [**here**](https://discord.com/api/oauth2/authorize?client_id={}) to add me to your server!".format(
                interaction.client.user.id if interaction.client.user else ""
            ),
            color=embeds.COLOR_PURPLE
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="website", description="Visit the Celestia website.")
    async def website(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌐 Celestia WEBSITE",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Full bot info, commands & tier system\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x9B59B6
        )
        embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
        embed.add_field(
            name="📂 LINK",
            value="[**Click here to open**](https://selesteruhc.surge.sh)",
            inline=False
        )
        embed.add_field(
            name="📋 PAGES",
            value="▸ `Commands` — All 100+ slash commands\n▸ `Tiers` — HT1 to Below Avg explained\n▸ `FAQ` — Common questions answered",
            inline=False
        )
        embed.set_footer(text="Celestia • Bot Info")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="read", description="Fetch and display a webpage's text content.")
    @app_commands.describe(url="The URL to read")
    async def read(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(ephemeral=False)
        if not url.startswith(("http://", "https://")):
            await interaction.followup.send("❌ Must be a valid http(s) URL.", ephemeral=True)
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    text = await resp.text()
                    status = resp.status
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch: `{e}`", ephemeral=True)
            return

        content = text.strip()
        if len(content) > 4000:
            content = content[:3997] + "..."

        embed = discord.Embed(
            title=f"📄 {url}",
            description=f"```\n{content}\n```",
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text=f"Status: {status} • Size: {len(text)} chars")
        await interaction.followup.send(embed=embed)
