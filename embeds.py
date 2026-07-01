import discord
from tabulate import tabulate
import database

# --- Premium Brand Color System ---
COLOR_BLUE = 0x00D2FF      # Registration Stage
COLOR_AMBER = 0xFF9F00     # Check-in Stage
COLOR_GREEN = 0x00E676     # Group Stage / Running
COLOR_PURPLE = 0xD500F9    # Playoff / Semis / Finals
COLOR_GOLD = 0xFFD700      # Champion Announced / Ended
COLOR_RED = 0xFF1744       # Cancelled / DQ
COLOR_DARK = 0x1A1A1A      # Setup

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
    """Generates the main tournament status panel embed."""
    stage = tournament['stage']
    color = get_stage_color(stage)
    
    embed = discord.Embed(
        title="🏆 MCPE HUB CHAMPIONSHIP",
        description=f"Welcome to the official esports tournament portal for **{tournament['name']}**.\nUse the buttons below to interact with the tournament.",
        color=color
    )
    
    # Header Branding
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png") # Placeholder MCPE HUB logo
    
    # Meta Fields
    embed.add_field(name="🎮 Mode", value=f"`{tournament['mode']}`", inline=True)
    embed.add_field(name="👥 Format", value=f"`{tournament['format']}`", inline=True)
    embed.add_field(name="📊 Teams", value=f"`{len(teams)}/{tournament['max_teams']}`", inline=True)
    
    # Active Stage
    stage_emojis = {
        "Registration": "📝 Registration Open",
        "Check-in": "⏱️ Check-in Active",
        "Group Stage": "⚔️ Group Stage",
        "Qualifiers": "🥊 Qualifiers",
        "Semis": "🔥 Semi Finals",
        "Finals": "👑 Grand Finals",
        "Ended": "🏆 Ended"
    }
    embed.add_field(name="📍 Current Stage", value=f"**{stage_emojis.get(stage, stage)}**", inline=True)
    embed.add_field(name="🎁 Prize Pool", value=f"`{tournament['prize'] or 'Champion Role'}`", inline=True)
    embed.add_field(name="👑 Host", value=f"<@{tournament['host_id']}>", inline=True)
    
    # Rules
    rules_text = tournament['rules'] or (
        "- No Hacks / Cheats\n"
        "- No Ghosting / Stream Sniping\n"
        "- No Cross-Teaming\n"
        "- Respect Staff & Opponents\n"
        "- Submit match proof within 15 mins"
    )
    embed.add_field(name="📖 Rules & Guidelines", value=rules_text, inline=False)
    
    # List registered teams if in registration/check-in stage
    if stage in ("Registration", "Check-in") and teams:
        team_list = []
        for idx, t in enumerate(teams):
            p_count = sum(1 for p in [t['captain_id'], t['player2_id'], t['player3_id'], t['player4_id']] if p)
            status_dot = "🟢" if t['status'] == "checked_in" else "⚪"
            team_list.append(f"{idx+1}. {status_dot} **{t['name']}** ({p_count} players)")
        
        # Paginate list if too long
        team_list_str = "\n".join(team_list[:15])
        if len(team_list) > 15:
            team_list_str += f"\n*...and {len(team_list) - 15} more teams*"
        embed.add_field(name=f"👥 Registered Teams ({len(teams)})", value=team_list_str, inline=False)
        
    embed.set_footer(text="SELESTER TOURNEY V3 • Esports System Manager")
    return embed

def bracket_embed(tournament: dict, matches: list, teams: list) -> discord.Embed:
    """Generates the live brackets progression embed."""
    stage = tournament['stage']
    color = get_stage_color(stage)
    
    embed = discord.Embed(
        title=f"📜 {tournament['name']} - Live Bracket",
        description=f"Current tournament bracket state for **{tournament['type']}** mode.",
        color=color
    )
    
    # If no matches, return warning
    if not matches:
        embed.description = "No matches have been generated yet. The bracket will appear once the tournament starts!"
        return embed
        
    # Group matches by stage
    stages_grouped = {}
    for m in matches:
        st = m['stage']
        if st not in stages_grouped:
            stages_grouped[st] = []
        stages_grouped[st].append(m)
        
    # Make a mapping of team ID to team Name
    team_names = {t['id']: t['name'] for t in teams}
    team_names[None] = "BYE"
    
    for st, st_matches in stages_grouped.items():
        match_lines = []
        for m in st_matches:
            t1 = team_names.get(m['team1_id'], "TBD")
            t2 = team_names.get(m['team2_id'], "TBD")
            
            # Format status or score
            if m['status'] == 'completed':
                winner_id = m['winner_id']
                if winner_id == m['team1_id']:
                    score_str = f"**{m['score1']}** - {m['score2']}"
                    t1_display = f"🏆 **{t1}**"
                    t2_display = f"~~{t2}~~"
                else:
                    score_str = f"{m['score1']} - **{m['score2']}**"
                    t1_display = f"~~{t1}~~"
                    t2_display = f"🏆 **{t2}**"
                match_lines.append(f"🔹 Match #{m['id']}: {t1_display} vs {t2_display} | `{score_str}`")
            elif m['status'] == 'active':
                match_lines.append(f"⚔️ Match #{m['id']}: **{t1}** vs **{t2}** | `RUNNING` <#{m['match_room_channel_id']}>")
            else:
                group_info = f" (Group {m['group_name']})" if m['group_name'] else ""
                match_lines.append(f"⚪ Match #{m['id']}: **{t1}** vs **{t2}** | `Pending` {group_info}")
                
        # Limit to 10 lines per stage in embeds to avoid exceeding field limits
        lines_str = "\n".join(match_lines[:10])
        if len(match_lines) > 10:
            lines_str += f"\n*...and {len(match_lines) - 10} more matches*"
            
        embed.add_field(name=f"📅 {st}", value=lines_str or "No matches.", inline=False)
        
    embed.set_footer(text="Updated live • Use /t match to check your specific game")
    return embed

def standings_embed(tournament: dict, teams: list) -> discord.Embed:
    """Generates a text table showing team wins, losses, and points."""
    stage = tournament['stage']
    color = get_stage_color(stage)
    
    embed = discord.Embed(
        title=f"📊 {tournament['name']} - Standings & Points",
        color=color
    )
    
    if not teams:
        embed.description = "No teams registered yet."
        return embed
        
    # Sort teams by points, then wins, then losses asc
    sorted_teams = sorted(teams, key=lambda x: (x['points'], x['wins'], -x['losses']), reverse=True)
    
    # We can separate by groups if in group stage
    # Let's check if there are group-stage matches to find which group they are in
    # (or just use their wins/losses/points for general standing)
    headers = ["Rank", "Team", "Wins", "Losses", "Points", "Status"]
    table_data = []
    
    for idx, t in enumerate(sorted_teams):
        status_display = t['status'].replace('_', ' ').capitalize()
        table_data.append([
            f"#{idx+1}",
            t['name'][:15], # limit length
            t['wins'],
            t['losses'],
            t['points'],
            status_display
        ])
        
    table_str = tabulate(table_data, headers=headers, tablefmt="simple")
    embed.description = f"```\n{table_str}\n```"
    
    embed.set_footer(text="SELESTER TOURNEY V3 • Updated live")
    return embed

def match_room_embed(match: dict, t1: dict, t2: dict) -> discord.Embed:
    """Generates the private room banner for paired opponents."""
    embed = discord.Embed(
        title=f"⚔️ Match Room #{match['id']} Generated",
        description=(
            f"Opponents have been paired! Prepare your game and coordinate timings.\n"
            f"Once done, upload proof using the **Submit Proof** button or an admin can record results."
        ),
        color=COLOR_PURPLE
    )
    
    embed.add_field(name="🟦 Team 1", value=f"**{t1['name']}**\nCaptain: <@{t1['captain_id']}>", inline=True)
    embed.add_field(name="🟥 Team 2", value=f"**{t2['name']}**\nCaptain: <@{t2['captain_id']}>", inline=True)
    
    embed.add_field(name="🕹️ Match Rules", value=(
        "- Agree on server details / gamertags.\n"
        "- Play the match according to tournament standards.\n"
        "- Record screenshots of the win screen or scoreboard as proof."
    ), inline=False)
    
    embed.set_footer(text="Players can use buttons below to confirm checkin or upload proof.")
    return embed

def player_stats_embed(player_id: int, stats: dict) -> discord.Embed:
    """Generates a player's statistics card."""
    embed = discord.Embed(
        title="🎮 PLAYER PROFILE",
        color=COLOR_BLUE
    )
    
    username = stats['username'] or "Unknown Player"
    embed.set_author(name=f"{username}", icon_url="https://i.imgur.com/g8o468o.png")
    
    played = stats['tournaments_played']
    wins = stats['wins']
    losses = stats['losses']
    rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    
    embed.add_field(name="🛡️ Tournaments Played", value=f"`{played}`", inline=True)
    embed.add_field(name="🏆 Championships Won", value=f"`{stats['championships_won']}`", inline=True)
    embed.add_field(name="✨ MVP Awards", value=f"`{stats['mvp_count']}`", inline=True)
    
    embed.add_field(name="⚔️ Match Wins", value=f"`{wins}`", inline=True)
    embed.add_field(name="💀 Match Losses", value=f"`{losses}`", inline=True)
    embed.add_field(name="📈 Win Rate", value=f"`{rate:.1f}%`", inline=True)
    
    embed.add_field(name="⭐ Season Points", value=f"**{stats['season_points']}** points", inline=False)
    
    embed.set_footer(text="MCPE HUB Statistics Portal")
    return embed

def champion_embed(tournament: dict, team: dict, runner_up: dict = None) -> discord.Embed:
    """Generates the grand championship announcement embed."""
    embed = discord.Embed(
        title="🏆 TOURNAMENT CHAMPION DECLARED!",
        description=f"Congratulations to the winners of the **{tournament['name']}**!",
        color=COLOR_GOLD
    )
    
    # Thumbnail/Logo
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png") # Placeholder
    
    # Champion details
    players = []
    if team['captain_id']: players.append(f"👑 Captain: <@{team['captain_id']}>")
    if team['player2_id']: players.append(f"👥 Player 2: <@{team['player2_id']}>")
    if team['player3_id']: players.append(f"👥 Player 3: <@{team['player3_id']}>")
    if team['player4_id']: players.append(f"👥 Player 4: <@{team['player4_id']}>")
    
    embed.add_field(
        name=f"👑 TEAM CHAMPION: {team['name']}",
        value="\n".join(players) or "No registered players.",
        inline=False
    )
    
    if runner_up:
        embed.add_field(
            name="🥈 Runner-Up",
            value=f"**{runner_up['name']}**",
            inline=True
        )
        
    embed.add_field(name="🎮 Mode", value=f"`{tournament['mode']}`", inline=True)
    embed.add_field(name="👥 Format", value=f"`{tournament['format']}`", inline=True)
    
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif") # Nice trophy GIF/image placeholder
    embed.set_footer(text="MCPE HUB Championship Hall of Fame")
    return embed

def history_embed(history_records: list) -> discord.Embed:
    """Generates the tournament history embed."""
    embed = discord.Embed(
        title="📂 TOURNAMENT HALL OF FAME",
        description="Here are the champions of previous MCPE HUB tournaments.",
        color=COLOR_GOLD
    )
    
    if not history_records:
        embed.description = "No previous tournament records found in the database."
        return embed
        
    for rec in history_records:
        embed.add_field(
            name=f"🏆 {rec['name']} (Season {rec['season']})",
            value=(
                f"🎮 Mode: `{rec['mode']}` | Format: `{rec['format']}`\n"
                f"🥇 Winner: **{rec['champion_team_name']}** (<@{rec['champion_captain_id']}>)\n"
                f"🥈 Runner-Up: **{rec['runner_up_team_name']}**\n"
                f"📅 Ended: *{rec['date_ended']}*"
            ),
            inline=False
        )
        
    embed.set_footer(text="MCPE HUB Historical Archive")
    return embed

# =====================================================================
# V3: TIER TEST EMBEDS
# =====================================================================

COLOR_TIER = 0x9B59B6
COLOR_TICKET = 0x3498DB
COLOR_RESULT = 0x2ECC71

def tier_test_hub_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎯 TIER TEST PORTAL",
        description=(
            "```js\n"
            "\"Prove your skills and earn your rank!\"\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Want to get your skills officially evaluated?**\n"
            "Select a gamemode below to start your tier test.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_TIER
    )
    embed.add_field(
        name="📋 RULES & REQUIREMENTS",
        value=(
            "```diff\n"
            "+ ✅ Stable internet connection is MANDATORY\n"
            "+ ✅ The tier given is FINAL — no arguments allowed\n"
            "+ ✅ Be respectful to the tier tester at all times\n"
            "- ❌ Inappropriate behavior = automatic fail\n"
            "- ❌ Do not spam or create multiple tickets\n"
            "```"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 AVAILABLE GAMEMODES",
        value=(
            "```\n"
            "🌌 Skywars    ⚔️ BUHC      🔥 FUHC\n"
            "🥊 Boxing     ⚡ Midfight  🛏️ Bedfight\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⬇️ **Select your gamemode below to begin**"
        ),
        inline=False
    )
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="SELESTER V3 • Tier Evaluation System")
    return embed

def tier_ticket_embed(user_id: int, gamemode: str) -> discord.Embed:
    embed = discord.Embed(
        title="🎟️ NEW TIER TEST TICKET",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**{gamemode}** tier test requested!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_TICKET
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="👤 Player", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="🎮 Gamemode", value=f"`{gamemode}`", inline=True)
    embed.add_field(name="📌 Status", value="```css\n[ Unclaimed ]\n```", inline=True)
    embed.add_field(name="📋 Instructions", value=(
        "▸ **Staff** — Click `Claim` to handle this test\n"
        "▸ **Tester** — Use `/tier result` after evaluating\n"
        "▸ **Player** — Wait patiently for a staff member"
    ), inline=False)
    embed.set_footer(text="SELESTER V3 • Tier Ticket System")
    return embed

def tier_result_embed(result: dict) -> discord.Embed:
    embed = discord.Embed(
        title="✅ TIER TEST COMPLETED",
        description=(
            "```ini\n"
            f"[ {result['ign']} has been officially tiered! ]\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_RESULT
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="👤 Player", value=f"<@{result['user_id']}>", inline=True)
    embed.add_field(name="🎮 IGN", value=f"`{result['ign']}`", inline=True)
    embed.add_field(name="⬅️ Previous Tier", value=f"```\n{result['previous_tier']}\n```", inline=True)
    embed.add_field(name="➡️ New Tier", value=f"```diff\n+ {result['new_tier']}\n```", inline=True)
    embed.add_field(name="📝 Tester Note", value=f"```{result['note'] or 'No note'}```", inline=False)
    embed.add_field(name="👨‍⚖️ Tested By", value=f"<@{result['tester_id']}>", inline=True)
    embed.set_footer(text="Thank you for your patience! • SELESTER V3 Tier System")
    return embed

# =====================================================================
# V3: RANKED EMBEDS
# =====================================================================

COLOR_RANKED = 0xE74C3C
COLOR_MATCH = 0xF39C12

def ranked_hub_embed(gamemode: str, queue_count: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"🏆 RANKED — {gamemode.upper()}",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Compete. Climb. Conquer.**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"```ml\nPlayers in queue : {queue_count}\n```"
        ),
        color=COLOR_RANKED
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="📋 COMPETITIVE RULES", value=(
        "```diff\n"
        "+ ✅ Fair Play — No hacking or cheating\n"
        "+ ✅ Respect opponents at all times\n"
        "- ❌ No intentional disconnecting\n"
        "```\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**📊 Point System:**\n"
        "▸ **Winner:** `+10 points`\n"
        "▸ **Loser:** `+1 point`\n"
        "▸ Check `/lb ranked` for leaderboard"
    ), inline=False)
    embed.set_footer(text="SELESTER V3 • Ranked Competitive System")
    return embed

def ranked_match_found_embed(match_id: int, player1_id: int, player2_id: int, gamemode: str) -> discord.Embed:
    embed = discord.Embed(
        title="⚔️ RANKED MATCH FOUND!",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"A **{gamemode}** opponent has been found!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MATCH
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(name="🟦 Player 1", value=f"<@{player1_id}>", inline=True)
    embed.add_field(name="🟥 Player 2", value=f"<@{player2_id}>", inline=True)
    embed.add_field(name="🎮 Gamemode", value=f"`{gamemode}`", inline=True)
    embed.add_field(name="📌 Status", value="```css\n[ Awaiting Players ]\n```", inline=True)
    embed.add_field(name="⚡ Action Required", value="Both players must click **Start Match** to begin!\nWinner gets **+10 pts**, Loser gets **+1 pt**.", inline=False)
    embed.set_footer(text="SELESTER V3 • Ranked Competitive • GL HF!")
    return embed

def ranked_leaderboard_embed(entries: list, gamemode: str = None) -> discord.Embed:
    title = "🏆 RANKED LEADERBOARD"
    if gamemode:
        title += f" — {gamemode.upper()}"
    embed = discord.Embed(title=title, color=COLOR_GOLD)

    if not entries:
        embed.description = "```\nNo ranked matches played yet. Be the first!\n```"
        return embed

    header = "```\n#   Player                 Pts    W    L\n" + "─" * 45 + "\n"
    lines = []
    for idx, entry in enumerate(entries[:15]):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"#{idx+1:02d}"
        name = f"<@{entry['user_id']}>"
        lines.append(
            f"{medal} {name} — **{entry['points']}pts** (W:{entry['wins']} L:{entry['losses']})"
        )
    embed.description = "\n".join(lines)
    embed.set_footer(text="SELESTER V3 • Ranked System")
    return embed

# =====================================================================
# V3: WELCOME / SERVER EMBEDS
# =====================================================================

COLOR_WELCOME = 0x1ABC9C

def welcome_embed(member: discord.Member, member_count: int) -> discord.Embed:
    embed = discord.Embed(
        title="🌟 WELCOME TO THE SERVER!",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**{member.mention}** just joined **{member.guild.name}**!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_WELCOME
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="📋 GETTING STARTED",
        value=(
            "```css\n"
            f"[ Welcome #{member_count} ]\n"
            "```\n"
            "▸ **Read** the rules channel\n"
            "▸ **Check** `/tier` to get ranked\n"
            "▸ **Compete** in `/ranked` matches\n"
            "▸ **Enjoy** your stay!"
        ),
        inline=False
    )
    embed.add_field(
        name="👤 MEMBER INFO",
        value=f"**User:** {member.mention}\n**Joined:** <t:{int(member.joined_at.timestamp())}:R>",
        inline=False
    )
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text=f"SELESTER V3 • Member #{member_count}")
    return embed

def suggestion_embed(suggestion_id: int, author: discord.Member, content: str) -> discord.Embed:
    embed = discord.Embed(
        title="💡 NEW SUGGESTION",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{content}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_BLUE
    )
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.add_field(name="📌 Status", value="```css\n[ Pending Review ]\n```", inline=False)
    embed.add_field(name="🎯 Vote", value="React ✅ to **approve** or ❌ to **deny**", inline=False)
    embed.set_footer(text=f"Suggestion #{suggestion_id} • SELESTER V3")
    return embed

def ticket_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="🎫 SUPPORT TICKET",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Need help? Create a ticket and staff will assist you!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_BLUE
    )
    embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
    embed.add_field(
        name="📋 GUIDELINES",
        value=(
            "```diff\n"
            "+ ✅ Be patient while waiting for a response\n"
            "+ ✅ Provide as much detail as possible\n"
            "- ❌ Do not create multiple tickets for the same issue\n"
            "- ❌ Do not abuse the ticket system\n"
            "```"
        ),
        inline=False
    )
    embed.add_field(
        name="🎯 HOW TO CREATE",
        value="⬇️ Click the **Create Ticket** button below to open a ticket.",
        inline=False
    )
    embed.set_footer(text="SELESTER V3 • Support Ticket System")
    return embed

def rules_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(
        title="📜 SERVER RULES",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**Please read and follow these rules to maintain order.**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_DARK
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "https://i.imgur.com/g8o468o.png")
    embed.add_field(
        name="1️⃣ Respect Everyone",
        value="Treat others how you want to be treated. Harassment = ban.",
        inline=False
    )
    embed.add_field(
        name="2️⃣ No Hacking / Cheating",
        value="Any form of cheating in tournaments/ranked = permanent ban.",
        inline=False
    )
    embed.add_field(
        name="3️⃣ No Spamming",
        value="Do not spam messages, mentions, reactions, or commands.",
        inline=False
    )
    embed.add_field(
        name="4️⃣ Follow Staff Instructions",
        value="Staff decisions are final. Respect their authority.",
        inline=False
    )
    embed.add_field(
        name="5️⃣ No Toxic Behavior",
        value="Racism, hate speech, harassment, or toxicity = immediate ban.",
        inline=False
    )
    embed.add_field(
        name="6️⃣ Use Appropriate Channels",
        value="Keep conversations in their designated channels.",
        inline=False
    )
    embed.add_field(
        name="7️⃣ No NSFW Content",
        value="This is a safe-for-work community. NSFW = ban.",
        inline=False
    )
    embed.add_field(
        name="8️⃣ Have Fun!",
        value="Enjoy your time here and make friends! 🎮",
        inline=False
    )
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="SELESTER V3 • Server Rules")
    return embed

def premium_announcement_embed(title: str, message: str, color: int = COLOR_PURPLE) -> discord.Embed:
    embed = discord.Embed(
        title=f"📢 {title}",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{message}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=color
    )
    embed.set_footer(text="SELESTER V3 • Server Announcement")
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
        title="🎯 TIER TEST TICKETS",
        description=(
            "```js\n"
            "\"Players waiting for tier evaluation\"\n"
            "```\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**👥 Open Tickets:** `{total}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_TIER
    )

    gamemodes = ["Skywars", "BUHC", "FUHC", "Boxing", "Midfight", "Bedfight"]
    for gm in gamemodes:
        count = summary.get(gm, 0) if summary else 0
        emoji = GAMEMODE_EMOJIS.get(gm, "🎮")
        embed.add_field(
            name=f"{emoji} {gm}",
            value=f"`{count}` ticket{'s' if count != 1 else ''}" if count else "`Empty`",
            inline=True
        )

    embed.add_field(
        name="📋 INFO",
        value=(
            "Click a gamemode below to see which players are waiting for testing."
        ),
        inline=False
    )
    embed.set_image(url="https://i.imgur.com/f04T8Yn.gif")
    embed.set_footer(text="SELESTER V3 • Tier Ticket Viewer")
    return embed

def tier_gamemode_queue_embed(guild: discord.Guild, gamemode: str) -> discord.Embed:
    tickets = database.get_tier_tickets_by_gamemode(guild.id, gamemode)
    emoji = GAMEMODE_EMOJIS.get(gamemode, "🎮")

    embed = discord.Embed(
        title=f"{emoji} {gamemode} — Open Tickets",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Players waiting for {gamemode} testing:**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_TIER
    )

    if tickets:
        lines = []
        for i, t in enumerate(tickets, 1):
            member = guild.get_member(t['user_id'])
            name = member.display_name if member else f"<@{t['user_id']}>"
            lines.append(f"`#{i:02d}` {name}")
        embed.add_field(
            name=f"👥 Players ({len(tickets)})",
            value="\n".join(lines),
            inline=False
        )
    else:
        embed.add_field(
            name="👥 Players",
            value="```\nNo open tickets\n```",
            inline=False
        )

    embed.set_footer(text="SELESTER V3 • Tier Ticket Viewer")
    return embed
