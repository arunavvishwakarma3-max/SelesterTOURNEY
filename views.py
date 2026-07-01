import asyncio
import discord
import database
import tournament
import embeds

def resolve_member(guild: discord.Guild, text: str) -> discord.Member:
    """Helper to resolve a Discord member from mention, ID, or name."""
    text = text.strip()
    if not text:
        return None
    # Check if mention <@123456789>
    if text.startswith("<@") and text.endswith(">"):
        clean_id = text[2:-1].replace("!", "").replace("&", "")
        if clean_id.isdigit():
            return guild.get_member(int(clean_id))
    # Check if raw ID
    if text.isdigit():
        return guild.get_member(int(text))
    # Search by username / display name
    for member in guild.members:
        if member.name.lower() == text.lower() or member.display_name.lower() == text.lower():
            return member
    return None

class RegistrationModal(discord.ui.Modal):
    def __init__(self, tournament_id: int):
        t_data = database.get_tournament(tournament_id)
        title = f"Register - {t_data['name'][:40]}" if t_data else "Team Registration"
        super().__init__(title=title)
        self.tournament_id = tournament_id

        self.team_name_input = discord.ui.TextInput(
            label="Team Name",
            placeholder="Enter a unique team name",
            min_length=3,
            max_length=25,
            required=True
        )
        self.add_item(self.team_name_input)

        self.player2_input = discord.ui.TextInput(
            label="Player 2 (Mention / ID)",
            placeholder="Required for 2v2+. Leave blank for Solo.",
            required=False
        )
        self.add_item(self.player2_input)

        self.player3_input = discord.ui.TextInput(
            label="Player 3 (Mention / ID)",
            placeholder="Required for 3v3+. Leave blank if not needed.",
            required=False
        )
        self.add_item(self.player3_input)

        self.player4_input = discord.ui.TextInput(
            label="Player 4 (Mention / ID)",
            placeholder="Required for 4v4+. Leave blank if not needed.",
            required=False
        )
        self.add_item(self.player4_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.followup.send("❌ Tournament not found.", ephemeral=True)
            return

        if t_data['stage'] != "Registration":
            await interaction.followup.send("❌ Registration is closed or tournament has already started.", ephemeral=True)
            return

        team_name = self.team_name_input.value.strip()
        p2_text = self.player2_input.value.strip()
        p3_text = self.player3_input.value.strip()
        p4_text = self.player4_input.value.strip()

        captain_id = interaction.user.id
        p2_id = None
        p3_id = None
        p4_id = None

        teams = database.get_tournament_teams(self.tournament_id)
        if len(teams) >= t_data['max_teams']:
            await interaction.followup.send("❌ The tournament is full! Cannot register new teams.", ephemeral=True)
            return

        t_format = t_data['format']
        fmt_map = {"Solo (1v1)": 1, "Doubles (2v2)": 2, "Triples (3v3)": 3, "Squads (4v4)": 4, "Clan Tournament": 4}
        required_players = fmt_map.get(t_format, 1)

        def _resolve(text: str, field_name: str) -> int | None:
            if not text:
                return None
            member = resolve_member(interaction.guild, text)
            if not member:
                raise ValueError(f"Could not find {field_name}: `{text}`")
            if member.id == captain_id:
                raise ValueError(f"You cannot register yourself as {field_name}.")
            return member.id

        try:
            if required_players >= 2:
                if not p2_text:
                    await interaction.followup.send(f"❌ Format is `{t_format}`. Player 2 is required.", ephemeral=True)
                    return
                p2_id = _resolve(p2_text, "Player 2")
            elif p2_text:
                await interaction.followup.send("⚠️ Format is Solo (1v1). Player 2 will be ignored.", ephemeral=True)

            if required_players >= 3:
                if not p3_text:
                    await interaction.followup.send(f"❌ Format is `{t_format}`. Player 3 is required.", ephemeral=True)
                    return
                p3_id = _resolve(p3_text, "Player 3")

            if required_players >= 4:
                if not p4_text:
                    await interaction.followup.send(f"❌ Format is `{t_format}`. Player 4 is required.", ephemeral=True)
                    return
                p4_id = _resolve(p4_text, "Player 4")
        except ValueError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        try:
            database.register_team(
                tournament_id=self.tournament_id,
                name=team_name,
                captain_id=captain_id,
                p2=p2_id,
                p3=p3_id,
                p4=p4_id
            )
        except ValueError as e:
            await interaction.followup.send(f"❌ Registration failed: {str(e)}", ephemeral=True)
            return

        config = database.get_guild_config(interaction.guild.id)
        if config and config['participant_role_id']:
            role = interaction.guild.get_role(config['participant_role_id'])
            if role:
                members_to_role = [p for p in [interaction.user, interaction.guild.get_member(p2_id), interaction.guild.get_member(p3_id), interaction.guild.get_member(p4_id)] if p]
                for m in members_to_role:
                    try: await m.add_roles(role)
                    except: pass

        await update_main_embed(interaction.guild, t_data)

        registered_msg = f"✅ Team **{team_name}** registered successfully!"
        lines = [f"👑 Captain: <@{captain_id}>"]
        if p2_id: lines.append(f"👤 Player 2: <@{p2_id}>")
        if p3_id: lines.append(f"👤 Player 3: <@{p3_id}>")
        if p4_id: lines.append(f"👤 Player 4: <@{p4_id}>")
        await interaction.followup.send(f"{registered_msg}\n" + "\n".join(lines), ephemeral=True)

class TournamentHubView(discord.ui.View):
    def __init__(self, tournament_id: int):
        super().__init__(timeout=None)
        self.tournament_id = tournament_id
        self.add_item(discord.ui.Button(label="Website", style=discord.ButtonStyle.link, row=0, url="https://selestertourney.vercel.app"))

    @discord.ui.button(label="Enter", style=discord.ButtonStyle.success, row=0, custom_id="t_enter", emoji="🏆")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.response.send_message("❌ Tournament not found.", ephemeral=True)
            return
        if t_data['stage'] != "Registration":
            await interaction.response.send_message("❌ Registration is currently closed.", ephemeral=True)
            return
        await interaction.response.send_modal(RegistrationModal(self.tournament_id))

    @discord.ui.button(label="Rules", style=discord.ButtonStyle.secondary, row=1, custom_id="t_rules", emoji="📖")
    async def rules_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.response.send_message("❌ Tournament not found.", ephemeral=True)
            return
        rules = t_data['rules'] or "No specific rules set."
        embed = discord.Embed(title="📖 Tournament Rules", description=rules, color=embeds.COLOR_BLUE)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Standings", style=discord.ButtonStyle.secondary, row=1, custom_id="t_standings", emoji="📊")
    async def standings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.response.send_message("❌ Tournament not found.", ephemeral=True)
            return
        teams = database.get_tournament_teams(self.tournament_id)
        embed = embeds.standings_embed(t_data, teams)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Bracket", style=discord.ButtonStyle.secondary, row=1, custom_id="t_bracket", emoji="📜")
    async def bracket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.response.send_message("❌ Tournament not found.", ephemeral=True)
            return
        matches = database.get_tournament_matches(self.tournament_id)
        teams = database.get_tournament_teams(self.tournament_id)
        embed = embeds.bracket_embed(t_data, matches, teams)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.danger, row=2, custom_id="t_leave", emoji="❌")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_tournament(self.tournament_id)
        if not t_data:
            await interaction.followup.send("❌ Tournament not found.", ephemeral=True)
            return
        if t_data['stage'] != "Registration":
            await interaction.followup.send("❌ Cannot leave: tournament has already started or ended.", ephemeral=True)
            return
            
        team = database.get_team_by_player(self.tournament_id, interaction.user.id)
        if not team:
            await interaction.followup.send("❌ You are not registered in this tournament.", ephemeral=True)
            return
            
        # Remove team
        database.remove_team(self.tournament_id, team['id'])
        
        # Remove role if configured
        config = database.get_guild_config(interaction.guild.id)
        if config and config['participant_role_id']:
            role = interaction.guild.get_role(config['participant_role_id'])
            if role:
                try:
                    # Remove from captain
                    cap = interaction.guild.get_member(team['captain_id'])
                    if cap: await cap.remove_roles(role)
                    # Remove from player 2
                    if team['player2_id']:
                        p2 = interaction.guild.get_member(team['player2_id'])
                        if p2: await p2.remove_roles(role)
                except discord.Forbidden:
                    pass
                    
        await update_main_embed(interaction.guild, t_data)
        await interaction.followup.send(f"✅ Your team **{team['name']}** has been removed from the tournament.", ephemeral=True)

class MatchRoomView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=None) # Persistent
        self.match_id = match_id

    @discord.ui.button(label="Confirm Ready", style=discord.ButtonStyle.success, row=0, custom_id="match_ready", emoji="✅")
    async def confirm_ready(self, interaction: discord.Interaction, button: discord.ui.Button):
        match = database.get_match(self.match_id)
        t1 = database.get_team(match['team1_id'])
        t2 = database.get_team(match['team2_id'])
        
        if interaction.user.id == t1['captain_id']:
            await interaction.response.send_message(f"🟦 Team **{t1['name']}** is ready! ⚔️", ephemeral=False)
        elif t2 and interaction.user.id == t2['captain_id']:
            await interaction.response.send_message(f"🟥 Team **{t2['name']}** is ready! ⚔️", ephemeral=False)
        else:
            await interaction.response.send_message("❌ Only the team captains can confirm readiness.", ephemeral=True)

    @discord.ui.button(label="Submit Proof", style=discord.ButtonStyle.primary, row=0, custom_id="match_submit_proof", emoji="📸")
    async def submit_proof(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ProofModal(self.match_id))

    @discord.ui.button(label="Dispute", style=discord.ButtonStyle.danger, row=0, custom_id="match_dispute", emoji="⚠️")
    async def dispute_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        match = database.get_match(self.match_id)
        config = database.get_guild_config(interaction.guild.id)
        
        ping_role = ""
        if config and config['referee_role_id']:
            ping_role = f"<@&{config['referee_role_id']}>"
        else:
            ping_role = "@Staff"
            
        await interaction.response.send_message(
            f"⚠️ **DISPUTE OPENED!** {ping_role} has been notified. "
            f"Captains, please stay in the channel and present screenshots/recordings of the issue.",
            ephemeral=False
        )

class ProofModal(discord.ui.Modal):
    def __init__(self, match_id: int):
        super().__init__(title="Submit Match Proof")
        self.match_id = match_id
        
        self.winner_input = discord.ui.TextInput(
            label="Winner Team Name",
            placeholder="Type your exact team name here",
            required=True
        )
        self.add_item(self.winner_input)
        
        self.proof_url_input = discord.ui.TextInput(
            label="Proof Link (Imgur / Discord attachment url)",
            placeholder="https://i.imgur.com/... or media.discordapp.net/...",
            required=True
        )
        self.add_item(self.proof_url_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        match = database.get_match(self.match_id)
        if not match or match['status'] == 'completed':
            await interaction.followup.send("❌ Match not found or already completed.", ephemeral=True)
            return
            
        winner_name = self.winner_input.value.strip()
        proof_url = self.proof_url_input.value.strip()
        
        t1 = database.get_team(match['team1_id'])
        t2 = database.get_team(match['team2_id'])
        
        # Verify winner name match
        winner_id = None
        loser_id = None
        score1 = 0
        score2 = 0
        
        if t1['name'].lower() == winner_name.lower():
            winner_id = t1['id']
            loser_id = t2['id'] if t2 else None
            score1 = 1
            score2 = 0
        elif t2 and t2['name'].lower() == winner_name.lower():
            winner_id = t2['id']
            loser_id = t1['id']
            score1 = 0
            score2 = 1
        else:
            await interaction.followup.send(f"❌ Entered team '{winner_name}' does not match either team in this match ({t1['name']} or {t2['name'] if t2 else 'None'}).", ephemeral=True)
            return
            
        # Update match in DB
        database.update_match_result(
            match_id=self.match_id,
            score1=score1,
            score2=score2,
            winner_id=winner_id,
            status='completed',
            proof_url=proof_url
        )
        
        # Notify match channel
        await interaction.followup.send("✅ Proof submitted successfully! The match has been auto-resolved.", ephemeral=True)
        await interaction.channel.send(
            f"🏆 **Match Resolved!**\n"
            f"Winner: **{winner_name}**\n"
            f"Proof: {proof_url}\n"
            f"This channel will be archived shortly."
        )
        
        # Log to results and staff channels
        config = database.get_guild_config(interaction.guild.id)
        if config:
            # Results Log
            if config['results_channel_id']:
                res_chan = interaction.guild.get_channel(config['results_channel_id'])
                if res_chan:
                    embed = discord.Embed(
                        title=f"🥊 Match #{self.match_id} Results",
                        description=f"**{t1['name']}** vs **{t2['name'] if t2 else 'BYE'}**",
                        color=embeds.COLOR_GREEN
                    )
                    embed.add_field(name="Winner", value=f"🏆 **{winner_name}**", inline=True)
                    embed.add_field(name="Proof", value=f"[View Proof]({proof_url})", inline=True)
                    await res_chan.send(embed=embed)
                    
            # Staff Log
            if config['staff_logs_channel_id']:
                staff_chan = interaction.guild.get_channel(config['staff_logs_channel_id'])
                if staff_chan:
                    await staff_chan.send(f"📝 Match #{self.match_id} resolved by captain {interaction.user.name}. Winner: {winner_name}. Proof: {proof_url}")

        # Check for tournament bracket progression
        res = tournament.check_and_advance_stage(match['tournament_id'])
        if res:
            await handle_stage_advancement(interaction.guild, match['tournament_id'], res)

async def update_main_embed(guild: discord.Guild, tournament_data: dict):
    """Helper to update the primary tournament panel embed in the registration channel."""
    config = database.get_guild_config(guild.id)
    if not config or not config['registration_channel_id']:
        return
        
    channel = guild.get_channel(config['registration_channel_id'])
    if not channel:
        return
        
    teams = database.get_tournament_teams(tournament_data['id'])
    embed = embeds.tournament_hub_embed(tournament_data, teams)
    view = TournamentHubView(tournament_data['id'])
    
    # We should search for the bot's pin or last message in the registration channel to update it,
    # or just send a new message if it doesn't exist.
    # To keep it simple, we can search the channel history for a message with the tournament title
    async for msg in channel.history(limit=50):
        if msg.author.id == guild.me.id and msg.embeds and msg.embeds[0].title == "🏆 MCPE HUB CHAMPIONSHIP":
            await msg.edit(embed=embed, view=view)
            return
            
    # If not found, send new
    await channel.send(embed=embed, view=view)

async def handle_stage_advancement(guild: discord.Guild, tournament_id: int, adv_result: dict):
    """Helper to process tournament stage change notifications, roles, channels, and logs."""
    t_data = database.get_tournament(tournament_id)
    config = database.get_guild_config(guild.id)
    if not config:
        return
        
    ann_chan = guild.get_channel(config['announcements_channel_id']) if config['announcements_channel_id'] else None
    
    action = adv_result['action']
    
    if action == "stage_advanced":
        new_stage = adv_result['stage']
        
        # Announcement
        if ann_chan:
            embed = discord.Embed(
                title="📢 TOURNAMENT STAGE ADVANCED",
                description=f"The tournament **{t_data['name']}** has progressed to **{new_stage}** stage!",
                color=embeds.COLOR_PURPLE
            )
            await ann_chan.send(embed=embed)
            
        # Create private match rooms for the new stage
        matches = database.get_tournament_matches(tournament_id, stage=new_stage)
        for m in matches:
            if m['status'] == 'pending' and m['team1_id'] and m['team2_id']:
                await create_match_room_channel(guild, m)
                
        # Role updates based on new stage
        await run_auto_role_updates(guild, tournament_id, new_stage)
        
    elif action == "swiss_next_round":
        round_num = adv_result['round']
        if ann_chan:
            await ann_chan.send(f"📢 **Swiss Round {round_num} Started!** Check the bracket/match list for pairings.")
            
        matches = database.get_tournament_matches(tournament_id, stage="Qualifiers", round_num=round_num)
        for m in matches:
            if m['status'] == 'pending' and m['team1_id'] and m['team2_id']:
                await create_match_room_channel(guild, m)
                
    elif action == "bracket_reset":
        if ann_chan:
            await ann_chan.send("📢 **Bracket Reset!** The Loser's Champ won the Grand Finals. A final bracket reset match is starting now!")
        matches = database.get_tournament_matches(tournament_id, stage="Finals")
        for m in matches:
            if m['status'] == 'pending' and m['team1_id'] and m['team2_id']:
                await create_match_room_channel(guild, m)
                
    elif action == "tournament_ended":
        champ = adv_result['champion_team']
        ru = adv_result['runner_up_team']
        
        # Champion Role update
        if champ and config['champion_role_id']:
            role = guild.get_role(config['champion_role_id'])
            if role:
                for pid in [champ['captain_id'], champ['player2_id'], champ['player3_id'], champ['player4_id']]:
                    if pid:
                        mem = guild.get_member(pid)
                        if mem:
                            try: await mem.add_roles(role)
                            except: pass
                            
        # Announcement
        if ann_chan:
            embed = embeds.champion_embed(t_data, champ, ru)
            await ann_chan.send(embed=embed)
            
        # Post standings in standings channel
        if config['standings_channel_id']:
            st_chan = guild.get_channel(config['standings_channel_id'])
            if st_chan:
                teams = database.get_tournament_teams(tournament_id)
                embed = embeds.standings_embed(t_data, teams)
                await st_chan.send(embed=embed)
                
        # Log to history channel
        if config['history_channel_id']:
            hist_chan = guild.get_channel(config['history_channel_id'])
            if hist_chan:
                history_records = database.get_history(limit=5)
                embed = embeds.history_embed(history_records)
                await hist_chan.send(embed=embed)
                
    # Update registration panel
    await update_main_embed(guild, t_data)

async def create_match_room_channel(guild: discord.Guild, match: dict):
    """Creates a temporary private channel for two paired opponents to communicate."""
    config = database.get_guild_config(guild.id)
    
    t1 = database.get_team(match['team1_id'])
    t2 = database.get_team(match['team2_id'])
    
    # Overwrites
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }
    
    # Captain 1
    c1_mem = guild.get_member(t1['captain_id'])
    if c1_mem: overwrites[c1_mem] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if t1['player2_id']:
        p2_mem = guild.get_member(t1['player2_id'])
        if p2_mem: overwrites[p2_mem] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
    # Captain 2
    if t2:
        c2_mem = guild.get_member(t2['captain_id'])
        if c2_mem: overwrites[c2_mem] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if t2['player2_id']:
            p2_mem = guild.get_member(t2['player2_id'])
            if p2_mem: overwrites[p2_mem] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
    # Referee Role Overwrites
    if config and config['referee_role_id']:
        ref_role = guild.get_role(config['referee_role_id'])
        if ref_role:
            overwrites[ref_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
    # Create text channel
    chan_name = f"match-{match['id']}-{t1['name'][:10]}-vs-{t2['name'][:10] if t2 else 'bye'}"
    # Keep lowercase alphanumeric with hyphens
    clean_name = "".join(c if (c.isalnum() or c == "-") else "" for c in chan_name).lower()
    
    try:
        channel = await guild.create_text_channel(name=clean_name, overwrites=overwrites)
        database.update_match_channel(match['id'], channel.id)
        
        # Send room banner and controller buttons
        embed = embeds.match_room_embed(match, t1, t2)
        view = MatchRoomView(match['id'])
        await channel.send(f"<@{t1['captain_id']}> vs <@{t2['captain_id'] if t2 else 0}>", embed=embed, view=view)
    except Exception as e:
        # If we fail, log to staff log
        if config and config['staff_logs_channel_id']:
            staff_chan = guild.get_channel(config['staff_logs_channel_id'])
            if staff_chan:
                await staff_chan.send(f"❌ Failed to create match room for Match #{match['id']}: {str(e)}")

async def run_auto_role_updates(guild: discord.Guild, tournament_id: int, new_stage: str):
    """Updates team roles automatically as they progress through tournament stages."""
    config = database.get_guild_config(guild.id)
    if not config:
        return
        
    teams = database.get_tournament_teams(tournament_id)
    
    # Map stages to role IDs
    stage_roles = {
        "Qualifiers": config['qualified_role_id'],
        "Semis": config['semi_role_id'],
        "Finals": config['final_role_id']
    }
    
    target_role_id = stage_roles.get(new_stage)
    if not target_role_id:
        return
        
    role = guild.get_role(target_role_id)
    if not role:
        return
        
    for t in teams:
        # Check if team is still qualified/active
        if t['status'] in ('registered', 'checked_in', 'qualified'):
            players = [t['captain_id'], t['player2_id'], t['player3_id'], t['player4_id']]
            for pid in players:
                if pid:
                    mem = guild.get_member(pid)
                    if mem:
                        try: await mem.add_roles(role)
                        except: pass

# =====================================================================
# V3: TIER TEST VIEWS
# =====================================================================

class TierGamemodeSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Skywars", emoji="🌌", style=discord.ButtonStyle.primary, row=0, custom_id="tier_gm_skywars")
    async def btn_skywars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Skywars")

    @discord.ui.button(label="BUHC", emoji="⚔️", style=discord.ButtonStyle.danger, row=0, custom_id="tier_gm_buhc")
    async def btn_buhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "BUHC")

    @discord.ui.button(label="FUHC", emoji="🔥", style=discord.ButtonStyle.success, row=0, custom_id="tier_gm_fuhc")
    async def btn_fuhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "FUHC")

    @discord.ui.button(label="Boxing", emoji="🥊", style=discord.ButtonStyle.primary, row=1, custom_id="tier_gm_boxing")
    async def btn_boxing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Boxing")

    @discord.ui.button(label="Midfight", emoji="⚡", style=discord.ButtonStyle.success, row=1, custom_id="tier_gm_midfight")
    async def btn_midfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Midfight")

    @discord.ui.button(label="Bedfight", emoji="🛏️", style=discord.ButtonStyle.danger, row=1, custom_id="tier_gm_bedfight")
    async def btn_bedfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Bedfight")

    async def _create_ticket(self, interaction: discord.Interaction, gamemode: str):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg['ticket_category_id']:
            await interaction.followup.send("❌ Tier system not fully set up. Contact staff.", ephemeral=True)
            return

        category = interaction.guild.get_channel(cfg['ticket_category_id'])
        if not category:
            await interaction.followup.send("❌ Ticket category not found.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if cfg['tier_tester_role_id']:
            tester_role = interaction.guild.get_role(cfg['tier_tester_role_id'])
            if tester_role:
                overwrites[tester_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        if cfg['tier_staff_role_id']:
            staff_role = interaction.guild.get_role(cfg['tier_staff_role_id'])
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        chan_name = f"tier-{interaction.user.name}-{gamemode.lower()}"
        clean = "".join(c if (c.isalnum() or c == "-") else "" for c in chan_name).lower()

        try:
            channel = await interaction.guild.create_text_channel(
                name=clean, category=category, overwrites=overwrites
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create ticket: {e}", ephemeral=True)
            return

        ticket_id = database.create_tier_ticket(interaction.guild_id, channel.id, interaction.user.id, gamemode)

        embed = embeds.tier_ticket_embed(interaction.user.id, gamemode)
        view = TierTicketView(ticket_id, interaction.user.id, gamemode)
        await channel.send(f"<@{interaction.user.id}> | <@&{cfg['tier_staff_role_id']}>" if cfg['tier_staff_role_id'] else f"<@{interaction.user.id}>", embed=embed, view=view)

        await interaction.followup.send(f"✅ Ticket created! Check {channel.mention}", ephemeral=True)

class TierTicketView(discord.ui.View):
    def __init__(self, ticket_id: int, user_id: int, gamemode: str):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.user_id = user_id
        self.gamemode = gamemode

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, row=0, custom_id="tier_claim", emoji="✋")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = database.get_tier_ticket(interaction.channel.id)
        if not ticket or ticket['status'] != 'open':
            await interaction.response.send_message("❌ Ticket already claimed or closed.", ephemeral=True)
            return

        database.claim_tier_ticket(self.ticket_id, interaction.user.id)

        embed = discord.Embed(
            title="✋ TICKET CLAIMED",
            description=f"<@{interaction.user.id}> is now handling this tier test!",
            color=embeds.COLOR_AMBER
        )
        embed.add_field(name="🎮 Gamemode", value=f"`{self.gamemode}`", inline=True)
        embed.add_field(name="👤 Player", value=f"<@{self.user_id}>", inline=True)
        await interaction.response.send_message(embed=embed)

        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, row=0, custom_id="tier_close", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = database.get_tier_ticket(interaction.channel.id)
        if not ticket or ticket['status'] == 'closed':
            await interaction.response.send_message("❌ Ticket already closed.", ephemeral=True)
            return

        database.close_tier_ticket(self.ticket_id)
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

# =====================================================================
# V3: RANKED VIEWS
# =====================================================================

class RankedGamemodeSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Skywars", emoji="🌌", style=discord.ButtonStyle.primary, row=0, custom_id="ranked_gm_skywars")
    async def btn_skywars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Skywars")

    @discord.ui.button(label="BUHC", emoji="⚔️", style=discord.ButtonStyle.danger, row=0, custom_id="ranked_gm_buhc")
    async def btn_buhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "BUHC")

    @discord.ui.button(label="FUHC", emoji="🔥", style=discord.ButtonStyle.success, row=0, custom_id="ranked_gm_fuhc")
    async def btn_fuhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "FUHC")

    @discord.ui.button(label="Boxing", emoji="🥊", style=discord.ButtonStyle.primary, row=1, custom_id="ranked_gm_boxing")
    async def btn_boxing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Boxing")

    @discord.ui.button(label="Midfight", emoji="⚡", style=discord.ButtonStyle.success, row=1, custom_id="ranked_gm_midfight")
    async def btn_midfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Midfight")

    @discord.ui.button(label="Bedfight", emoji="🛏️", style=discord.ButtonStyle.danger, row=1, custom_id="ranked_gm_bedfight")
    async def btn_bedfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Bedfight")

    async def _show_gamemode(self, interaction: discord.Interaction, gamemode: str):
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg['ranked_queue_channel_id']:
            await interaction.response.send_message("❌ Ranked system not fully set up.", ephemeral=True)
            return

        queue_count = database.get_ranked_queue_count(interaction.guild_id, gamemode)
        embed = embeds.ranked_hub_embed(gamemode, queue_count)
        view = RankedQueueView(gamemode)
        await interaction.response.edit_message(embed=embed, view=view)

class RankedQueueView(discord.ui.View):
    def __init__(self, gamemode: str):
        super().__init__(timeout=None)
        self.gamemode = gamemode

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.success, row=0, custom_id="ranked_join", emoji="🎮")
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        gamemode = self.gamemode
        added = database.add_to_ranked_queue(interaction.guild_id, interaction.user.id, gamemode)
        if not added:
            await interaction.response.send_message("❌ You're already in the queue!", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ You joined the **{gamemode}** queue! Waiting for opponent...", ephemeral=True)

        opponent = database.find_ranked_match(interaction.guild_id, gamemode, interaction.user.id)
        if opponent:
            database.remove_from_ranked_queue(interaction.guild_id, interaction.user.id, gamemode)
            database.remove_from_ranked_queue(interaction.guild_id, opponent['user_id'], gamemode)

            match_id = database.create_ranked_match(interaction.guild_id, interaction.user.id, opponent['user_id'], gamemode)

            embed = embeds.ranked_match_found_embed(match_id, interaction.user.id, opponent['user_id'], gamemode)
            view = RankedMatchView(match_id, interaction.user.id, opponent['user_id'], gamemode)

            cfg = database.get_guild_config_v3(interaction.guild_id)
            if cfg and cfg['ranked_queue_channel_id']:
                chan = interaction.guild.get_channel(cfg['ranked_queue_channel_id'])
                if chan:
                    await chan.send(f"<@{interaction.user.id}> <@{opponent['user_id']}>", embed=embed, view=view)

            try:
                await interaction.user.send(f"⚔️ **Ranked match found!** Check <#{cfg['ranked_queue_channel_id']}>")
            except:
                pass
            try:
                opponent_mem = await interaction.guild.fetch_member(opponent['user_id'])
                if opponent_mem:
                    await opponent_mem.send(f"⚔️ **Ranked match found!** Check <#{cfg['ranked_queue_channel_id']}>")
            except:
                pass

        queue_count = database.get_ranked_queue_count(interaction.guild_id, gamemode)
        embed = embeds.ranked_hub_embed(gamemode, queue_count)
        await interaction.message.edit(embed=embed)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, row=0, custom_id="ranked_leave", emoji="🚪")
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        database.remove_from_ranked_queue(interaction.guild_id, interaction.user.id, self.gamemode)
        await interaction.response.send_message("❌ You left the queue.", ephemeral=True)

        queue_count = database.get_ranked_queue_count(interaction.guild_id, self.gamemode)
        embed = embeds.ranked_hub_embed(self.gamemode, queue_count)
        await interaction.message.edit(embed=embed)

class RankedMatchView(discord.ui.View):
    def __init__(self, match_id: int, player1_id: int, player2_id: int, gamemode: str):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.gamemode = gamemode
        self.p1_ready = False
        self.p2_ready = False

    @discord.ui.button(label="Start Match", style=discord.ButtonStyle.success, row=0, custom_id="ranked_start", emoji="⚔️")
    async def start_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.player1_id:
            self.p1_ready = True
            await interaction.response.send_message(f"🟦 <@{self.player1_id}> is ready!", ephemeral=False)
        elif interaction.user.id == self.player2_id:
            self.p2_ready = True
            await interaction.response.send_message(f"🟥 <@{self.player2_id}> is ready!", ephemeral=False)
        else:
            await interaction.response.send_message("❌ You're not part of this match.", ephemeral=True)
            return

        if self.p1_ready and self.p2_ready:
            embed = discord.Embed(
                title="✅ MATCH STARTED!",
                description=f"**{self.gamemode}** match between <@{self.player1_id}> and <@{self.player2_id}> is now live!\n\n"
                            "Play your match and report the result using the buttons below.",
                color=embeds.COLOR_GREEN
            )
            await interaction.message.edit(embed=embed)
            await interaction.channel.send(f"⚔️ **MATCH STARTED!** <@{self.player1_id}> vs <@{self.player2_id}> — GL HF!")

    @discord.ui.button(label="Report Win", style=discord.ButtonStyle.primary, row=0, custom_id="ranked_win", emoji="🏆")
    async def report_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.player1_id, self.player2_id):
            await interaction.response.send_message("❌ You're not part of this match.", ephemeral=True)
            return

        winner_id = interaction.user.id
        loser_id = self.player2_id if winner_id == self.player1_id else self.player1_id

        database.complete_ranked_match(self.match_id, winner_id, 1, 0)
        database.update_ranked_stats(interaction.guild_id, winner_id, self.gamemode, 10, win=True)
        database.update_ranked_stats(interaction.guild_id, loser_id, self.gamemode, 1, win=False)

        embed = discord.Embed(
            title="🏆 MATCH COMPLETED!",
            description=f"<@{winner_id}> defeated <@{loser_id}> in **{self.gamemode}**!",
            color=embeds.COLOR_GOLD
        )
        embed.add_field(name="🥇 Winner", value=f"<@{winner_id}> (+10 pts)", inline=True)
        embed.add_field(name="💀 Loser", value=f"<@{loser_id}> (+1 pt)", inline=True)

        await interaction.response.send_message(embed=embed)

        for btn in self.children:
            btn.disabled = True
        await interaction.message.edit(view=self)

# =====================================================================
# PAGINATION VIEW (generic)
# =====================================================================

class PaginationView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current = 0
        self.max_page = len(embeds) - 1
        self._update_buttons()

    def _update_buttons(self):
        self.first_page.disabled = self.current == 0
        self.prev_page.disabled = self.current == 0
        self.next_page.disabled = self.current >= self.max_page
        self.last_page.disabled = self.current >= self.max_page
        self.page_label.label = f"Page {self.current + 1}/{self.max_page + 1}"

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary, row=0, custom_id="page_first")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary, row=0, custom_id="page_prev")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = max(0, self.current - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, row=0, disabled=True, custom_id="page_label")
    async def page_label(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary, row=0, custom_id="page_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = min(self.max_page, self.current + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary, row=0, custom_id="page_last")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = self.max_page
        self._update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

# =====================================================================
# CONFIRMATION VIEW
# =====================================================================

class ConfirmView(discord.ui.View):
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, row=0, emoji="✅", custom_id="confirm_yes")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=0, emoji="❌", custom_id="confirm_no")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

# =====================================================================
# V3: TIER TICKET VIEWER
# =====================================================================

class TierQueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Skywars", emoji="🌌", style=discord.ButtonStyle.primary, row=0, custom_id="tq_skywars")
    async def btn_skywars(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Skywars")

    @discord.ui.button(label="BUHC", emoji="⚔️", style=discord.ButtonStyle.danger, row=0, custom_id="tq_buhc")
    async def btn_buhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "BUHC")

    @discord.ui.button(label="FUHC", emoji="🔥", style=discord.ButtonStyle.success, row=0, custom_id="tq_fuhc")
    async def btn_fuhc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "FUHC")

    @discord.ui.button(label="Boxing", emoji="🥊", style=discord.ButtonStyle.primary, row=1, custom_id="tq_boxing")
    async def btn_boxing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Boxing")

    @discord.ui.button(label="Midfight", emoji="⚡", style=discord.ButtonStyle.success, row=1, custom_id="tq_midfight")
    async def btn_midfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Midfight")

    @discord.ui.button(label="Bedfight", emoji="🛏️", style=discord.ButtonStyle.danger, row=1, custom_id="tq_bedfight")
    async def btn_bedfight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._show_gamemode(interaction, "Bedfight")

    async def _show_gamemode(self, interaction: discord.Interaction, gamemode: str):
        embed = embeds.tier_gamemode_queue_embed(interaction.guild, gamemode)
        view = TierGamemodeView(gamemode)
        await interaction.response.edit_message(embed=embed, view=view)


class TierGamemodeView(discord.ui.View):
    def __init__(self, gamemode: str):
        super().__init__(timeout=None)
        self.gamemode = gamemode

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", row=0, custom_id="tgv_refresh")
    async def refresh_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = embeds.tier_gamemode_queue_embed(interaction.guild, self.gamemode)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="🔙", row=0, custom_id="tgv_back")
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = embeds.tier_queue_main_embed(interaction.guild)
        view = TierQueueView()
        await interaction.response.edit_message(embed=embed, view=view)
