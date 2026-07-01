import discord
from tabulate import tabulate
import database

COLOR_BLUE = 0x00D2FF
COLOR_AMBER = 0xFF9F00
COLOR_GREEN = 0x00E676
COLOR_PURPLE = 0xD500F9
COLOR_GOLD = 0xFFD700
COLOR_RED = 0xFF1744
COLOR_DARK = 0x1A1A1A
COLOR_INFO = 0x7289DA
COLOR_SUCCESS = 0x43B581

def get_stage_color(stage: str) -> int:
    stage_colors = {
        "Setup": COLOR_DARK,
        "Registration": COLOR_BLUE,
        "Check-in": COLOR_AMBER,
        "Group Stage": COLOR_GREEN,
        "Qualifiers": COLOR_GREEN,
        "Semis": COLOR_PURPLE,
        "Finals": COLOR_PURPLE,
        "Ended": COLOR_GOLD
    }
    return stage_colors.get(stage, COLOR_DARK)

def tournament_hub_embed(tournament: dict, teams: list) -> discord.Embed:
    stage = tournament['stage']
    color = get_stage_color(stage)

    stage_labels = {
        "Registration": "📝 Registration Open",
        "Check-in": "⏱️ Check-in Active",
        "Group Stage": "⚔️ Group Stage",
        "Qualifiers": "🥊 Qualifiers",
        "Semis": "🔥 Semi Finals",
        "Finals": "👑 Grand Finals",
        "Ended": "🏆 Ended"
    }

    embed = discord.Embed(
        title=f"🏆 {tournament['name']}",
        description=stage_labels.get(stage, stage),
        color=color
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")

    embed.add_field(name="🎮 Mode", value=tournament['mode'], inline=True)
    embed.add_field(name="👥 Format", value=tournament['format'], inline=True)
    embed.add_field(name="📊 Teams", value=f"{len(teams)}/{tournament['max_teams']}", inline=True)
    embed.add_field(name="🎁 Prize", value=tournament['prize'] or 'Champion Role', inline=True)
    embed.add_field(name="👑 Host", value=f"<@{tournament['host_id']}>", inline=True)
    embed.add_field(name="📍 Stage", value=stage_labels.get(stage, stage), inline=True)

    rules = tournament['rules'] or (
        "• No Hacks / Cheats\n"
        "• No Ghosting / Stream Sniping\n"
        "• No Cross-Teaming\n"
        "• Respect Staff & Opponents\n"
        "• Submit match proof within 15 mins"
    )
    embed.add_field(name="📖 Rules", value=rules, inline=False)

    if stage in ("Registration", "Check-in") and teams:
        lines = []
        for idx, t in enumerate(teams):
            p_count = sum(1 for p in [t['captain_id'], t['player2_id'], t['player3_id'], t['player4_id']] if p)
            dot = "🟢" if t['status'] == "checked_in" else "⚪"
            lines.append(f"{dot} **{t['name']}** ({p_count}p)")
        value = "\n".join(lines[:20])
        if len(lines) > 20:
            value += f"\n*+{len(lines)-20} more*"
        embed.add_field(name=f"👥 Teams ({len(teams)})", value=value, inline=False)

    embed.set_footer(text="Celestia • Esports System")
    return embed

def bracket_embed(tournament: dict, matches: list, teams: list) -> discord.Embed:
    color = get_stage_color(tournament['stage'])
    embed = discord.Embed(
        title=f"📜 {tournament['name']} — Bracket",
        description=f"Type: **{tournament['type']}**",
        color=color
    )

    if not matches:
        embed.description = "No matches generated yet."
        return embed

    team_names = {t['id']: t['name'] for t in teams}
    team_names[None] = "BYE"
    stages = {}
    for m in matches:
        stages.setdefault(m['stage'], []).append(m)

    for st, st_matches in stages.items():
        lines = []
        for m in st_matches:
            t1 = team_names.get(m['team1_id'], "TBD")
            t2 = team_names.get(m['team2_id'], "TBD")
            if m['status'] == 'completed':
                w = m['winner_id']
                if w == m['team1_id']:
                    lines.append(f"🏆 **{t1}** vs ~~{t2}~~ (`{m['score1']}-{m['score2']}`)")
                else:
                    lines.append(f"~~{t1}~~ vs 🏆 **{t2}** (`{m['score1']}-{m['score2']}`)")
            elif m['status'] == 'active':
                lines.append(f"⚔️ **{t1}** vs **{t2}** — <#{m['match_room_channel_id']}>")
            else:
                g = f" (Grp {m['group_name']})" if m['group_name'] else ""
                lines.append(f"⚪ **{t1}** vs **{t2}**{g}")
        embed.add_field(name=st, value="\n".join(lines[:10]) or "No matches", inline=False)

    embed.set_footer(text="Use /t match to see your game")
    return embed

def standings_embed(tournament: dict, teams: list) -> discord.Embed:
    color = get_stage_color(tournament['stage'])
    embed = discord.Embed(
        title=f"📊 {tournament['name']} — Standings",
        color=color
    )

    if not teams:
        embed.description = "No teams registered yet."
        return embed

    sorted_teams = sorted(teams, key=lambda x: (x['points'], x['wins'], -x['losses']), reverse=True)
    lines = []
    for idx, t in enumerate(sorted_teams):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"{medal} **{t['name']}** — {t['wins']}W / {t['losses']}L — `{t['points']}pts`")
    embed.description = "\n".join(lines)

    embed.set_footer(text="Celestia • Updated live")
    return embed

def match_room_embed(match: dict, t1: dict, t2: dict) -> discord.Embed:
    embed = discord.Embed(
        title=f"⚔️ Match #{match['id']}",
        description="Coordinate with your opponent and play your match. Use the buttons below to submit proof.",
        color=COLOR_PURPLE
    )
    embed.add_field(name="🟦 Team 1", value=f"**{t1['name']}**\nCaptain: <@{t1['captain_id']}>", inline=True)
    embed.add_field(name="🟥 Team 2", value=f"**{t2['name']}**\nCaptain: <@{t2['captain_id']}>", inline=True)

    embed.set_footer(text="Screenshots required as proof")
    return embed

def player_stats_embed(player_id: int, stats: dict) -> discord.Embed:
    embed = discord.Embed(
        title="🎮 Player Profile",
        color=COLOR_BLUE
    )

    username = stats['username'] or "Unknown"
    embed.set_author(name=username, icon_url="https://i.imgur.com/g8o468o.png")

    wins = stats['wins']
    losses = stats['losses']
    rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

    embed.add_field(name="🏆 Championships", value=str(stats['championships_won']), inline=True)
    embed.add_field(name="🛡️ Played", value=str(stats['tournaments_played']), inline=True)
    embed.add_field(name="✨ MVP", value=str(stats['mvp_count']), inline=True)
    embed.add_field(name="⚔️ Wins", value=str(wins), inline=True)
    embed.add_field(name="💀 Losses", value=str(losses), inline=True)
    embed.add_field(name="📈 Win Rate", value=f"{rate:.1f}%", inline=True)
    embed.add_field(name="⭐ Season Points", value=f"**{stats['season_points']}**", inline=False)

    embed.set_footer(text="Celestia • Stats Portal")
    return embed

def champion_embed(tournament: dict, team: dict, runner_up: dict = None) -> discord.Embed:
    embed = discord.Embed(
        title="🏆 Tournament Champion!",
        description=f"**{team['name']}** wins **{tournament['name']}**!",
        color=COLOR_GOLD
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")

    players = []
    if team['captain_id']: players.append(f"👑 <@{team['captain_id']}> (Captain)")
    if team['player2_id']: players.append(f"👤 <@{team['player2_id']}>")
    if team['player3_id']: players.append(f"👤 <@{team['player3_id']}>")
    if team['player4_id']: players.append(f"👤 <@{team['player4_id']}>")
    embed.add_field(name="Champions", value="\n".join(players) or "No players", inline=False)

    if runner_up:
        embed.add_field(name="🥈 Runner-Up", value=runner_up['name'], inline=True)
    embed.add_field(name="🎮 Mode", value=tournament['mode'], inline=True)
    embed.add_field(name="👥 Format", value=tournament['format'], inline=True)

    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="Celestia • Hall of Fame")
    return embed

def history_embed(history_records: list) -> discord.Embed:
    embed = discord.Embed(
        title="📂 Hall of Fame",
        description="Previous tournament champions.",
        color=COLOR_GOLD
    )

    if not history_records:
        embed.description = "No previous tournaments recorded."
        return embed

    for rec in history_records[:5]:
        embed.add_field(
            name=f"🏆 {rec['name']} (S{rec['season']})",
            value=(
                f"🥇 **{rec['champion_team_name']}** — <@{rec['champion_captain_id']}>\n"
                f"🥈 {rec['runner_up_team_name']}\n"
                f"🎮 {rec['mode']} | {rec['format']} | 📅 {rec['date_ended']}"
            ),
            inline=False
        )

    embed.set_footer(text="Celestia • History")
    return embed

# =====================================================================
# V3: TIER TEST EMBEDS
# =====================================================================

COLOR_TIER = 0x9B59B6
COLOR_TICKET = 0x3498DB
COLOR_RESULT = 0x2ECC71

def tier_test_hub_embed(bot_avatar_url: str = None) -> discord.Embed:
    embed = discord.Embed(
        title="🎯 Tier Test Portal",
        description="Select a gamemode below to get your skills officially ranked.",
        color=COLOR_TIER
    )
    embed.set_thumbnail(url=bot_avatar_url or "https://i.imgur.com/g8o468o.png")
    embed.add_field(
        name="📋 Rules",
        value=(
            "• Stable internet is mandatory\n"
            "• Tier given is final — no arguments\n"
            "• Be respectful to the tester\n"
            "• No spamming multiple tickets"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Available Gamemodes",
        value="🌌 Skywars  ⚔️ BUHC  🔥 FUHC\n🥊 Boxing  ⚡ Midfight  🛏️ Bedfight",
        inline=False
    )
    embed.set_footer(text="Celestia • Tier System")
    return embed

def tier_ticket_embed(user_id: int, gamemode: str, ign: str, time: str) -> discord.Embed:
    embed = discord.Embed(
        title="🎟️ New Tier Test",
        description=f"<@{user_id}> requested a **{gamemode}** evaluation",
        color=COLOR_TICKET
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="IGN", value=ign, inline=True)
    embed.add_field(name="Availability", value=time, inline=True)
    embed.add_field(name="Status", value="Unclaimed", inline=True)
    embed.add_field(
        name="Actions",
        value="• **Claim** — handle this request\n• **Result** — submit evaluation\n• **Close** — delete channel",
        inline=False
    )
    embed.set_footer(text="Celestia • Tier Ticket")
    return embed

def tier_claim_embed(user_id: int, gamemode: str, ign: str, time: str, claimed_by: int) -> discord.Embed:
    embed = discord.Embed(
        title="✋ Request Claimed",
        description=f"<@{claimed_by}> is handling the **{gamemode}** evaluation for <@{user_id}>.",
        color=COLOR_GOLD
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="IGN", value=ign, inline=True)
    embed.add_field(name="Availability", value=time, inline=True)
    embed.set_footer(text="Celestia • Evaluation in progress")
    return embed

def tier_history_embed(results: list) -> discord.Embed:
    embed = discord.Embed(
        title="📋 Recent Evaluations",
        color=COLOR_INFO
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    for r in results:
        gm = r.get('gamemode', '')
        label = f"{r['ign']} — {r['previous_tier']} ➜ {r['new_tier']}"
        if gm:
            label += f" ({gm})"
        embed.add_field(
            name=label,
            value=f"Player: <@{r['user_id']}> • Tester: <@{r['tester_id']}>",
            inline=False
        )
    embed.set_footer(text="Celestia • Latest results")
    return embed

def tier_role_embed(tier_name: str, role_mention: str) -> discord.Embed:
    embed = discord.Embed(
        title="✅ Role Mapping Added",
        description=f"**{tier_name}** ➜ {role_mention}",
        color=COLOR_SUCCESS
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.set_footer(text="Celestia")
    return embed

def tier_roles_list_embed(mapping: dict) -> discord.Embed:
    lines = "\n".join(f"• **{t}** ➜ <@&{r}>" for t, r in mapping.items())
    embed = discord.Embed(
        title="📋 Tier Role Mappings",
        description=lines or "No mappings configured.",
        color=COLOR_TIER
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.set_footer(text="Celestia • Use /tier setrole to add")
    return embed

def tiersetup_success_embed(tier_channel, results_channel, ticket_category, staff_role, tester_role=None) -> discord.Embed:
    desc = (
        f"• **Tier Channel:** {tier_channel.mention}\n"
        f"• **Results Channel:** {results_channel.mention}\n"
        f"• **Ticket Category:** {ticket_category.mention}\n"
        f"• **Staff Role:** {staff_role.mention}\n"
    )
    if tester_role:
        desc += f"• **Tester Role:** {tester_role.mention}"
    embed = discord.Embed(
        title="✅ System Ready",
        description=desc,
        color=COLOR_SUCCESS
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.set_footer(text="Celestia • Tier system configured")
    return embed

def tier_remove_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🗑️ System Removed",
        description="The tier hub has been deleted. Run **/tier setup** to reconfigure.",
        color=COLOR_INFO
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.set_footer(text="Celestia")
    return embed

def tier_result_embed(result: dict) -> discord.Embed:
    embed = discord.Embed(
        title="✅ Tier Test Completed",
        description=f"**{result['ign']}** has been officially ranked!",
        color=COLOR_RESULT
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="🎮 Gamemode", value=result.get('gamemode', 'N/A'), inline=True)
    embed.add_field(name="👤 Player", value=f"<@{result['user_id']}>", inline=True)
    embed.add_field(name="🎮 IGN", value=result['ign'], inline=True)
    embed.add_field(name="Previous Tier", value=result['previous_tier'] or "None", inline=True)
    embed.add_field(name="➡️ New Tier", value=f"**{result['new_tier']}**", inline=True)
    embed.add_field(name="👨‍⚖️ Tester", value=f"<@{result['tester_id']}>", inline=True)
    embed.add_field(name="📝 Note", value=result['note'] or "No note", inline=False)
    embed.set_footer(text="Celestia • Tier System")
    return embed

# =====================================================================
# V3: RANKED EMBEDS
# =====================================================================

COLOR_RANKED = 0xE74C3C
COLOR_MATCH = 0xF39C12

def ranked_hub_embed(gamemode: str, queue_count: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏆 Ranked — {gamemode}",
        description=f"**{queue_count}** player{'' if queue_count == 1 else 's'} in queue",
        color=COLOR_RANKED
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(
        name="📋 Rules",
        value="• No hacking or cheating\n• Respect opponents\n• No intentional disconnecting",
        inline=False
    )
    embed.add_field(
        name="📊 Points",
        value="Winner: **+10** | Loser: **+1**\nUse `/lb ranked` for leaderboard",
        inline=False
    )
    embed.set_footer(text="Celestia • Ranked System")
    return embed

def ranked_match_found_embed(match_id: int, player1_id: int, player2_id: int, gamemode: str) -> discord.Embed:
    embed = discord.Embed(
        title="⚔️ Match Found!",
        description=f"A **{gamemode}** opponent has been found for you!",
        color=COLOR_MATCH
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="🟦 Player 1", value=f"<@{player1_id}>", inline=True)
    embed.add_field(name="🟥 Player 2", value=f"<@{player2_id}>", inline=True)
    embed.add_field(name="🎮 Gamemode", value=gamemode, inline=True)
    embed.add_field(
        name="⚡ Action",
        value="Both players click **Start Match** to begin!\nWinner: +10 pts | Loser: +1 pt",
        inline=False
    )
    embed.set_footer(text="Celestia • GL HF!")
    return embed

def ranked_leaderboard_embed(entries: list, gamemode: str = None) -> discord.Embed:
    title = "🏆 Ranked Leaderboard"
    if gamemode:
        title += f" — {gamemode}"
    embed = discord.Embed(title=title, color=COLOR_GOLD)

    if not entries:
        embed.description = "No matches played yet. Be the first!"
        return embed

    lines = []
    for idx, entry in enumerate(entries[:15]):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"#{idx+1:02d}"
        lines.append(f"{medal} <@{entry['user_id']}> — **{entry['points']}pts** (W:{entry['wins']} L:{entry['losses']})")
    embed.description = "\n".join(lines)
    embed.set_footer(text="Celestia • Ranked System")
    return embed

# =====================================================================
# V3: WELCOME / SERVER EMBEDS
# =====================================================================

COLOR_WELCOME = 0x1ABC9C

def welcome_embed(member: discord.Member, member_count: int) -> discord.Embed:
    bot_avatar = member.guild.me.display_avatar.url if member.guild.me else None
    embed = discord.Embed(
        title="🌟 Welcome!",
        description=f"{member.mention} joined **{member.guild.name}** — Member **#{member_count}**",
        color=COLOR_WELCOME
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_image(url=bot_avatar)
    embed.add_field(
        name="📋 Getting Started",
        value=(
            "• Read the rules\n"
            "• Check `/tier` to get ranked\n"
            "• Compete in `/ranked`\n"
            "• Enjoy your stay!"
        ),
        inline=False
    )
    embed.add_field(
        name="👤 Info",
        value=f"Joined: <t:{int(member.joined_at.timestamp())}:R>",
        inline=False
    )
    embed.set_footer(text=f"Celestia • Member #{member_count}")
    return embed

def suggestion_embed(suggestion_id: int, author: discord.Member, content: str) -> discord.Embed:
    embed = discord.Embed(
        title="💡 New Suggestion",
        description=content,
        color=COLOR_BLUE
    )
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.add_field(name="Status", value="Pending Review", inline=True)
    embed.add_field(name="Vote", value="React ✅ to approve or ❌ to deny", inline=True)
    embed.set_footer(text=f"Suggestion #{suggestion_id} • Celestia")
    return embed

def ticket_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Need help? Click below to create a ticket and staff will assist you.",
        color=COLOR_BLUE
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(
        name="📋 Guidelines",
        value=(
            "• Be patient while waiting\n"
            "• Provide as much detail as possible\n"
            "• Don't create multiple tickets for the same issue\n"
            "• Don't abuse the ticket system"
        ),
        inline=False
    )
    embed.set_footer(text="Celestia • Support System")
    return embed

def rules_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="📜 Server Rules",
        description="Please follow these rules to maintain a great community.",
        color=COLOR_DARK
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "https://i.imgur.com/g8o468o.png")
    embed.add_field(name="1️⃣ Respect Everyone", value="Treat others how you want to be treated.", inline=False)
    embed.add_field(name="2️⃣ No Hacking / Cheating", value="Cheating in tournaments/ranked = permanent ban.", inline=False)
    embed.add_field(name="3️⃣ No Spamming", value="Don't spam messages, mentions, or commands.", inline=False)
    embed.add_field(name="4️⃣ Follow Staff", value="Staff decisions are final.", inline=False)
    embed.add_field(name="5️⃣ No Toxicity", value="Racism, hate speech, harassment = immediate ban.", inline=False)
    embed.add_field(name="6️⃣ Use Proper Channels", value="Keep conversations in their designated channels.", inline=False)
    embed.add_field(name="7️⃣ No NSFW", value="Safe-for-work community only.", inline=False)
    embed.add_field(name="8️⃣ Have Fun!", value="Enjoy your time here and make friends!", inline=False)
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="Celestia • Server Rules")
    return embed

def premium_announcement_embed(title: str, message: str, color: int = COLOR_PURPLE) -> discord.Embed:
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=color
    )
    embed.set_footer(text="Celestia • Announcement")
    return embed

# =====================================================================
# TIER QUEUE EMBEDS
# =====================================================================

GAMEMODE_EMOJIS = {
    "Skywars": "🌌", "BUHC": "⚔️", "FUHC": "🔥",
    "Boxing": "🥊", "Midfight": "⚡", "Bedfight": "🛏️"
}

def tier_queue_main_embed(guild: discord.Guild) -> discord.Embed:
    summary = database.get_tier_ticket_summary(guild.id)
    total = database.get_open_tier_tickets_count(guild.id)

    embed = discord.Embed(
        title="🎯 Tier Test Tickets",
        description=f"**{total}** open ticket{'s' if total != 1 else ''} waiting for evaluation",
        color=COLOR_TIER
    )

    gamemodes = ["Skywars", "BUHC", "FUHC", "Boxing", "Midfight", "Bedfight"]
    for gm in gamemodes:
        count = summary.get(gm, 0) if summary else 0
        emoji = GAMEMODE_EMOJIS.get(gm, "🎮")
        label = f"`{count}`" if count else "`0`"
        embed.add_field(name=f"{emoji} {gm}", value=label, inline=True)

    embed.add_field(
        name="Info",
        value="Click a gamemode to see waiting players.",
        inline=False
    )
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="Celestia • Tier Queue")
    return embed

def tier_gamemode_queue_embed(guild: discord.Guild, gamemode: str) -> discord.Embed:
    tickets = database.get_tier_tickets_by_gamemode(guild.id, gamemode)
    emoji = GAMEMODE_EMOJIS.get(gamemode, "🎮")

    embed = discord.Embed(
        title=f"{emoji} {gamemode} — Open Tickets",
        color=COLOR_TIER
    )

    if tickets:
        lines = []
        for i, t in enumerate(tickets, 1):
            member = guild.get_member(t['user_id'])
            name = member.display_name if member else f"<@{t['user_id']}>"
            lines.append(f"`#{i:02d}` {name}")
        embed.description = "\n".join(lines)
    else:
        embed.description = "No open tickets for this gamemode."

    embed.set_footer(text="Celestia • Tier Queue")
    return embed
