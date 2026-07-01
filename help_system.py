import discord
from discord import app_commands
from discord.ext import commands
import embeds

async def _can_access(interaction: discord.Interaction) -> bool:
    if interaction.user == interaction.guild.owner:
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    return False

@app_commands.default_permissions(administrator=True)
async def help_callback(interaction: discord.Interaction):
    if not await _can_access(interaction):
        await interaction.response.send_message("❌ Only the server owner or admins can use this.", ephemeral=True)
        return

    embed = discord.Embed(
        title="📚 Celestia — Command List",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Complete command reference**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x9B59B6
    )

    embed.add_field(
        name="🏆 Tournament `/t`",
        value=(
            "`setup` `create` `enter` `leave` `start` `checkin` `checkin_end`\n"
            "`result` `dq` `removeteam` `match` `bracket` `standings`\n"
            "`stats` `history` `rules` `season` `reset` `setstage`"
        ),
        inline=False
    )

    embed.add_field(
        name="🎯 Tier Test `/tier`",
        value="`setup` — Auto-create tier channels\n`result` — Submit tier evaluation",
        inline=False
    )

    embed.add_field(
        name="🏆 Ranked `/ranked` `/lb`",
        value="`setup` — Auto-create ranked channels\n`stats` — Your ranked stats\n`lb ranked` — Leaderboard",
        inline=False
    )

    embed.add_field(
        name="🎵 Music `/music`",
        value=(
            "`setup` `playmusic` `stop` `skip` `queue`\n"
            "`pause` `resume` `volume` `nowplaying` `loop`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛡️ Server `/server`",
        value=(
            "`announce` `ban` `kick` `mute` `unmute` `lock` `unlock`\n"
            "`purge` `nick` `role` `slowmode` `rules` `setname`\n"
            "`warn` `warnings` `clearwarn` `nuke` `addemoji`\n"
            "`lockdown` `unlockdown`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋 Welcome `/welcome`",
        value="`setup` — Auto-create welcome channel\n`test` — Test welcome message",
        inline=False
    )

    embed.add_field(
        name="💡 Suggestions `/suggestion` `/suggest`",
        value="`setup` — Auto-create channel\n`submit` — Submit a suggestion\n`approve` / `deny` — Review",
        inline=False
    )

    embed.add_field(
        name="🎫 Tickets `/ticket`",
        value="`setup` — Auto-create ticket category + panel\n`panel` `close` `add` `remove` `claim` `subject`",
        inline=False
    )

    embed.add_field(
        name="🎉 Giveaways `/giveaway`",
        value="`setup` — Auto-create channel\n`start` `reroll` `end` `list`",
        inline=False
    )

    embed.add_field(
        name="📋 Applications `/apply`",
        value="`staff` — Submit staff application\n`staffsetup` — Auto-create apps channel",
        inline=False
    )

    embed.add_field(
        name="🎭 Auto-Role `/autorole`",
        value="`add` — Add auto-role\n`remove` — Remove auto-role\n`list` — View current auto-roles",
        inline=False
    )

    embed.add_field(
        name="🔧 Utility",
        value="`/ping` `/uptime` `/avatar` `/banner` `/userinfo` `/serverinfo`\n`/roleinfo` `/channelinfo` `/botinfo` `/membercount`\n`/roles` `/emojis` `/invite`",
        inline=False
    )

    embed.add_field(
        name="🎪 Fun",
        value="`/say` `/embed` `/poll` `/coinflip` `/dice` `/8ball` `/choose` `/random`",
        inline=False
    )

    embed.set_footer(text="Celestia • Help & Commands")
    await interaction.response.send_message(embed=embed, ephemeral=True)
