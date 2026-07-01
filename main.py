import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import database
import tournament
import embeds
import views
import datetime
import tier_system
import ranked_system
import server_commands
import welcome_system
import utility_commands
import fun_commands
import giveaway_system
import suggestion_system
import ticket_system
import music_system
import staff_application
import autorole_system
import comp_system
import help_system

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Setup Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

class TournamentBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # Register slash command groups
        self.tree.add_command(TournamentGroup(name="t", description="MCPE HUB Tournament Commands"))
        self.tree.add_command(tier_system.TierGroup())
        self.tree.add_command(ranked_system.RankedGroup())
        self.tree.add_command(ranked_system.LbGroup())
        self.tree.add_command(server_commands.ServerGroup())
        self.tree.add_command(welcome_system.WelcomeGroup())
        self.tree.add_command(utility_commands.UtilityGroup())
        self.tree.add_command(fun_commands.FunGroup())
        self.tree.add_command(giveaway_system.GiveawayGroup())
        self.tree.add_command(suggestion_system.SuggestionGroup())
        self.tree.add_command(suggestion_system.SuggestGroup())
        self.tree.add_command(ticket_system.TicketGroup())
        self.tree.add_command(music_system.MusicGroup())
        self.tree.add_command(staff_application.ApplyGroup())
        self.tree.add_command(autorole_system.AutoroleGroup())
        self.tree.add_command(comp_system.CompGroup())
        help_cmd = app_commands.Command(
            name="help",
            description="Show every bot command (Admin/Owner only)",
            callback=help_system.help_callback,
        )
        help_cmd.default_permissions = discord.Permissions(administrator=True)
        self.tree.add_command(help_cmd)

        # Connect Lavalink for music system
        try:
            await music_system.connect_lavalink(self)
            music_system.setup_events(self)
            print("Connected to Lavalink node.")
        except Exception as e:
            print(f"Lavalink connection failed (music disabled): {e}")

    async def on_ready(self):
        # Initialize Database
        database.init_db()
        utility_commands.set_start_time()

        print(f"Logged in as {self.user.name} ({self.user.id})")

        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"Made with ❤️ • {len(self.guilds)} servers"
            )
        )
        
        # Try to sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands globally.")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")
            
        # Hook persistent views
        for guild in self.guilds:
            t_data = database.get_active_tournament(guild.id)
            if t_data:
                self.add_view(views.TournamentHubView(t_data['id']), message_id=None)
                matches = database.get_tournament_matches(t_data['id'])
                for m in matches:
                    if m['status'] == 'active':
                        self.add_view(views.MatchRoomView(m['id']), message_id=None)
        # Register persistent V3 views
        self.add_view(views.TierGamemodeSelect())
        self.add_view(views.TierQueueView())
        self.add_view(views.RankedGamemodeSelect())
        self.add_view(ticket_system.TicketPanelView())
        self.add_view(comp_system.CompPanelView())
        print("Persistent views restored.")

    async def on_member_join(self, member: discord.Member):
        await welcome_system.send_welcome(member)
        await autorole_system.assign_autoroles(member)

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.user in message.mentions:
            embed = discord.Embed(
                title="👋 HEY THERE!",
                description=(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Hi {message.author.mention}! Need help?\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=0x9B59B6
            )
            embed.add_field(
                name="📋 QUICK COMMANDS",
                value=(
                    "▸ `/t create` — Start a tournament\n"
                    "▸ `/tier setup` — Tier test system\n"
                    "▸ `/ranked setup` — Ranked matches\n"
                    "▸ `/music playmusic <song>` — Play music\n"
                    "▸ `/server rules` — Server rules\n"
                    "▸ `/apply staff` — Staff application\n"
                    "▸ `/autorole add` — Auto-roles\n"
                    "▸ `/suggestion submit` — Suggest something"
                ),
                inline=False
            )
            embed.add_field(
                name="📌 FULL COMMAND LIST",
                value="Admins/Owners can use **`/help`** to see every command.",
                inline=False
            )
            embed.set_footer(text="SELESTER V3 • SelesterUHC Bot")
            await message.channel.send(embed=embed)

bot = TournamentBot()
server_commands.set_bot_ref(bot)

# Helper admin check
def is_admin_or_staff():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        config = database.get_guild_config(interaction.guild.id)
        if config:
            staff = interaction.guild.get_role(config['staff_role_id'])
            host = interaction.guild.get_role(config['host_role_id'])
            referee = interaction.guild.get_role(config['referee_role_id'])
            user_roles = interaction.user.roles
            if (staff and staff in user_roles) or (host and host in user_roles) or (referee and referee in user_roles):
                return True
        return False
    return app_commands.check(predicate)

# =====================================================================
# AUTOCOMPLETE HELPERS
# =====================================================================

async def autocomplete_teams(interaction: discord.Interaction, current: str):
    t_data = database.get_active_tournament(interaction.guild_id)
    if not t_data:
        return []
    teams = database.get_tournament_teams(t_data['id'])
    return [
        app_commands.Choice(name=t['name'], value=t['name'])
        for t in teams if current.lower() in t['name'].lower()
    ][:25]

async def autocomplete_matches(interaction: discord.Interaction, current: str):
    t_data = database.get_active_tournament(interaction.guild_id)
    if not t_data:
        return []
    matches = database.get_tournament_matches(t_data['id'])
    return [
        app_commands.Choice(name=f"#{m['id']} - T{m['team1_id']} vs T{m['team2_id']}" if m['team2_id'] else f"#{m['id']} - T{m['team1_id']} (BYE)", value=m['id'])
        for m in matches if current in str(m['id'])
    ][:25]

async def autocomplete_players(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=m.display_name, value=str(m.id))
        for m in interaction.guild.members if current.lower() in m.display_name.lower()
    ][:25]

class TournamentGroup(app_commands.Group):
    
    # =====================================================================
    # ADMIN COMMANDS
    # =====================================================================
    
    @app_commands.command(name="setup", description="Auto-create tournament channels and roles.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        # 1. Create Roles
        role_names = ["Tournament Host", "Tournament Staff", "Referee", "Participant", "Qualified Team", "Semi Finalist", "Finalist", "Champion"]
        created_roles = {}
        
        for name in role_names:
            role = discord.utils.get(guild.roles, name=name)
            if not role:
                try:
                    role = await guild.create_role(name=name, reason="MCPE Tournament Bot Setup")
                    created_roles[name] = role.id
                except Exception as e:
                    await interaction.followup.send(f"❌ Failed to create role '{name}': {e}", ephemeral=True)
                    return
            else:
                created_roles[name] = role.id
                
        # 2. Create Channels
        channel_names = [
            ("tournament-announcements", discord.ChannelType.text),
            ("tournament-registration", discord.ChannelType.text),
            ("tournament-chat", discord.ChannelType.text),
            ("tournament-results", discord.ChannelType.text),
            ("tournament-standings", discord.ChannelType.text),
            ("tournament-history", discord.ChannelType.text),
            ("staff-logs", discord.ChannelType.text),
            ("bot-config", discord.ChannelType.text)
        ]
        
        created_chans = {}
        for name, c_type in channel_names:
            chan = discord.utils.get(guild.channels, name=name)
            if not chan:
                try:
                    # Make staff logs and bot config private to staff
                    overwrites = {}
                    if name in ("staff-logs", "bot-config"):
                        staff_role = guild.get_role(created_roles["Tournament Staff"])
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            guild.me: discord.PermissionOverwrite(read_messages=True)
                        }
                        if staff_role:
                            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True)
                            
                    chan = await guild.create_text_channel(name=name, overwrites=overwrites, reason="MCPE Tournament Bot Setup")
                    created_chans[name] = chan.id
                except Exception as e:
                    await interaction.followup.send(f"❌ Failed to create channel '{name}': {e}", ephemeral=True)
                    return
            else:
                created_chans[name] = chan.id
                
        # Save to database
        db_data = {
            "announcements_channel_id": created_chans["tournament-announcements"],
            "registration_channel_id": created_chans["tournament-registration"],
            "chat_channel_id": created_chans["tournament-chat"],
            "results_channel_id": created_chans["tournament-results"],
            "standings_channel_id": created_chans["tournament-standings"],
            "history_channel_id": created_chans["tournament-history"],
            "staff_logs_channel_id": created_chans["staff-logs"],
            "bot_config_channel_id": created_chans["bot-config"],
            "host_role_id": created_roles["Tournament Host"],
            "staff_role_id": created_roles["Tournament Staff"],
            "referee_role_id": created_roles["Referee"],
            "participant_role_id": created_roles["Participant"],
            "qualified_role_id": created_roles["Qualified Team"],
            "semi_role_id": created_roles["Semi Finalist"],
            "final_role_id": created_roles["Finalist"],
            "champion_role_id": created_roles["Champion"]
        }
        database.save_guild_config(guild.id, db_data)
        
        await interaction.followup.send("✅ **Setup Complete!** All roles and channels have been initialized and saved to the config database.", ephemeral=True)

    @app_commands.command(name="create", description="Create a new tournament.")
    @is_admin_or_staff()
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="BUHC", value="BUHC"),
            app_commands.Choice(name="FUHC", value="FUHC"),
            app_commands.Choice(name="Skywars", value="Skywars"),
            app_commands.Choice(name="Bedwars", value="Bedwars"),
            app_commands.Choice(name="Boxing", value="Boxing"),
            app_commands.Choice(name="Midfight", value="Midfight"),
            app_commands.Choice(name="Sumo", value="Sumo"),
            app_commands.Choice(name="Nodebuff", value="Nodebuff"),
            app_commands.Choice(name="Bridge", value="Bridge"),
            app_commands.Choice(name="Combo", value="Combo")
        ],
        format_str=[
            app_commands.Choice(name="Solo (1v1)", value="Solo (1v1)"),
            app_commands.Choice(name="Doubles (2v2)", value="Doubles (2v2)"),
            app_commands.Choice(name="Triples (3v3)", value="Triples (3v3)"),
            app_commands.Choice(name="Squads (4v4)", value="Squads (4v4)"),
            app_commands.Choice(name="Clan Tournament", value="Clan Tournament")
        ],
        type_str=[
            app_commands.Choice(name="Single Elimination", value="Single Elimination"),
            app_commands.Choice(name="Double Elimination", value="Double Elimination"),
            app_commands.Choice(name="Round Robin", value="Round Robin"),
            app_commands.Choice(name="Swiss Format", value="Swiss Format"),
            app_commands.Choice(name="Group Stage + Playoffs", value="Group Stage + Playoffs")
        ]
    )
    @app_commands.describe(
        name="Tournament name",
        mode="Gamemode",
        format_str="Team format",
        type_str="Bracket type",
        prize="Prize description",
        max_teams="Max teams (4-128)",
        rules="Tournament rules text",
        description="Short description for the hub embed",
        server_ip="Server IP for matches (optional)",
        server_port="Server port (optional)"
    )
    async def create(self, interaction: discord.Interaction, name: str, mode: str, format_str: str, type_str: str, prize: str = "Champion Role", max_teams: int = 16, rules: str = None, description: str = None, server_ip: str = None, server_port: str = None):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        if max_teams < 2 or max_teams > 128:
            await interaction.followup.send("❌ max_teams must be between 2 and 128.", ephemeral=True)
            return

        config = database.get_guild_config(guild.id)
        if not config:
            await interaction.followup.send("❌ Guild config not found. Please run `/t setup` first.", ephemeral=True)
            return

        active = database.get_active_tournament(guild.id)
        if active:
            await interaction.followup.send(f"❌ There is already an active tournament: **{active['name']}** (Stage: {active['stage']}). Please end or reset it first.", ephemeral=True)
            return

        full_rules = rules or ""
        if server_ip:
            full_rules += f"\n\n**Server:** `{server_ip}"
            if server_port:
                full_rules += f":{server_port}"
            full_rules += "`"

        t_id = database.create_tournament(
            guild_id=guild.id,
            name=name,
            mode=mode,
            format_str=format_str,
            type_str=type_str,
            prize=prize,
            host_id=interaction.user.id,
            max_teams=max_teams,
            rules=full_rules
        )

        t_data = database.get_tournament(t_id)
        if description:
            t_data['description'] = description

        reg_chan = guild.get_channel(config['registration_channel_id'])
        if reg_chan:
            embed = embeds.tournament_hub_embed(t_data, [])
            view = views.TournamentHubView(t_id)
            msg = await reg_chan.send(embed=embed, view=view)
            bot.add_view(view, message_id=msg.id)

        await interaction.followup.send(f"✅ Tournament **{name}** created successfully! ID: `{t_id}`", ephemeral=True)

    @app_commands.command(name="start", description="Transition tournament from Registration to Check-in or start matchmaking.")
    @is_admin_or_staff()
    async def start_tournament(self, interaction: discord.Interaction, skip_checkin: bool = False):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament found.", ephemeral=True)
            return
            
        if t_data['stage'] != "Registration":
            await interaction.followup.send(f"❌ Cannot start: tournament is currently in `{t_data['stage']}` stage.", ephemeral=True)
            return
            
        teams = database.get_tournament_teams(t_data['id'])
        if len(teams) < 2:
            await interaction.followup.send("❌ Cannot start tournament with fewer than 2 registered teams.", ephemeral=True)
            return
            
        config = database.get_guild_config(interaction.guild.id)
        ann_chan = interaction.guild.get_channel(config['announcements_channel_id']) if config else None
        
        if not skip_checkin:
            # Advance to Check-in
            database.update_tournament_stage(t_data['id'], "Check-in")
            t_updated = database.get_tournament(t_data['id'])
            await views.update_main_embed(interaction.guild, t_updated)
            
            if ann_chan:
                embed = discord.Embed(
                    title="⏰ TOURNAMENT CHECK-IN STARTED",
                    description=f"Check-in is now open for **{t_data['name']}**!\nCaptains, please use the `/t checkin` command to confirm attendance.",
                    color=embeds.COLOR_AMBER
                )
                await ann_chan.send(embed=embed)
                
            await interaction.followup.send("✅ Tournament transitioned to Check-in stage. Announcements posted.", ephemeral=True)
        else:
            # Set all checked-in automatically
            for t in teams:
                database.update_team_status(t['id'], 'checked_in')
            # Generate Brackets
            tournament.generate_initial_bracket(t_data['id'])
            t_updated = database.get_tournament(t_data['id'])
            
            if ann_chan:
                embed = discord.Embed(
                    title="⚔️ TOURNAMENT MATCHES GENERATED",
                    description=f"The brackets for **{t_data['name']}** are live! Check the brackets and prepare for your matches.",
                    color=embeds.COLOR_GREEN
                )
                await ann_chan.send(embed=embed)
                
            # Create match channels for Qualifiers
            matches = database.get_tournament_matches(t_data['id'], stage="Qualifiers")
            for m in matches:
                if m['status'] == 'pending' and m['team1_id'] and m['team2_id']:
                    await views.create_match_room_channel(interaction.guild, m)
                    
            await views.update_main_embed(interaction.guild, t_updated)
            await interaction.followup.send("✅ Tournament started! Matches generated and rooms initialized.", ephemeral=True)

    @app_commands.command(name="checkin_end", description="End check-in, disqualify no-shows, and generate brackets.")
    @is_admin_or_staff()
    async def checkin_end(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data or t_data['stage'] != "Check-in":
            await interaction.followup.send("❌ Tournament must be in 'Check-in' stage to finalize check-in.", ephemeral=True)
            return
            
        teams = database.get_tournament_teams(t_data['id'])
        checked_in = [t for t in teams if t['status'] == 'checked_in']
        no_shows = [t for t in teams if t['status'] != 'checked_in']
        
        # Disqualify no-shows
        for t in no_shows:
            database.update_team_status(t['id'], 'eliminated')
            
        if len(checked_in) < 2:
            # Revert or cancel
            await interaction.followup.send("❌ Fewer than 2 teams checked in. Cannot generate brackets. Please reset/cancel or wait for check-ins.", ephemeral=True)
            return
            
        # Generate brackets
        tournament.generate_initial_bracket(t_data['id'])
        t_updated = database.get_tournament(t_data['id'])
        
        config = database.get_guild_config(interaction.guild.id)
        ann_chan = interaction.guild.get_channel(config['announcements_channel_id']) if config else None
        
        if ann_chan:
            embed = discord.Embed(
                title="⚔️ TOURNAMENT ACTIVE - BRACKETS GENERATED",
                description=f"Check-in ended. **{len(no_shows)}** teams disqualified for no-show.\n**{len(checked_in)}** teams progressing. Match channels are being initialized!",
                color=embeds.COLOR_GREEN
            )
            await ann_chan.send(embed=embed)
            
        # Create match channels for Qualifiers/Group Stage
        start_stage = "Group Stage" if t_data['type'] in ("Round Robin", "Group Stage + Playoffs") else "Qualifiers"
        matches = database.get_tournament_matches(t_data['id'], stage=start_stage)
        for m in matches:
            if m['status'] == 'pending' and m['team1_id'] and m['team2_id']:
                await views.create_match_room_channel(interaction.guild, m)
                
        await views.update_main_embed(interaction.guild, t_updated)
        await interaction.followup.send("✅ Check-in ended. Active bracket matches generated.", ephemeral=True)

    @app_commands.command(name="result", description="Manually input match results.")
    @is_admin_or_staff()
    @app_commands.autocomplete(match_id=autocomplete_matches)
    @app_commands.autocomplete(winner_team_name=autocomplete_teams)
    async def result(self, interaction: discord.Interaction, match_id: int, score1: int, score2: int, winner_team_name: str):
        await interaction.response.defer(ephemeral=True)
        match = database.get_match(match_id)
        if not match:
            await interaction.followup.send("❌ Match not found.", ephemeral=True)
            return
            
        t1 = database.get_team(match['team1_id'])
        t2 = database.get_team(match['team2_id'])
        
        winner_id = None
        if t1['name'].lower() == winner_team_name.lower():
            winner_id = t1['id']
        elif t2 and t2['name'].lower() == winner_team_name.lower():
            winner_id = t2['id']
        else:
            await interaction.followup.send(f"❌ '{winner_team_name}' does not match Team 1 ({t1['name']}) or Team 2 ({t2['name'] if t2 else 'None'}).", ephemeral=True)
            return
            
        database.update_match_result(
            match_id=match_id,
            score1=score1,
            score2=score2,
            winner_id=winner_id,
            status='completed',
            proof_url="Staff Input"
        )
        
        await interaction.followup.send(f"✅ Match #{match_id} result updated. Winner: **{winner_team_name}**.", ephemeral=True)
        
        # Log to results
        config = database.get_guild_config(interaction.guild.id)
        if config and config['results_channel_id']:
            res_chan = interaction.guild.get_channel(config['results_channel_id'])
            if res_chan:
                await res_chan.send(f"🏆 **Match #{match_id} resolved by Staff.** Winner: **{winner_team_name}** (`{score1}-{score2}`).")
                
        # Channel Cleanup
        if match['match_room_channel_id']:
            m_chan = interaction.guild.get_channel(match['match_room_channel_id'])
            if m_chan:
                try: await m_chan.delete(reason="Match completed")
                except: pass
                
        # Advance stage check
        res = tournament.check_and_advance_stage(match['tournament_id'])
        if res:
            await views.handle_stage_advancement(interaction.guild, match['tournament_id'], res)

    @app_commands.command(name="dq", description="Disqualify a team.")
    @is_admin_or_staff()
    @app_commands.autocomplete(team_name=autocomplete_teams)
    async def disqualify(self, interaction: discord.Interaction, team_name: str):
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.response.send_message("❌ No active tournament.", ephemeral=True)
            return

        teams = database.get_tournament_teams(t_data['id'])
        target_team = None
        for t in teams:
            if t['name'].lower() == team_name.lower():
                target_team = t
                break

        if not target_team:
            await interaction.response.send_message(f"❌ Team '{team_name}' not found.", ephemeral=True)
            return

        confirm = views.ConfirmView()
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to DQ **{target_team['name']}**? This will resolve all their matches.",
            view=confirm, ephemeral=True
        )
        await confirm.wait()
        if not confirm.value:
            return

        await interaction.edit_original_response(content="Processing disqualification...", view=None)

        database.update_team_status(target_team['id'], 'eliminated')

        config = database.get_guild_config(interaction.guild.id)
        if config and config['staff_logs_channel_id']:
            staff_chan = interaction.guild.get_channel(config['staff_logs_channel_id'])
            if staff_chan:
                await staff_chan.send(f"🔴 Team **{target_team['name']}** has been disqualified by staff.")

        matches = database.get_tournament_matches(t_data['id'])
        for m in matches:
            if m['status'] in ('pending', 'active') and (m['team1_id'] == target_team['id'] or m['team2_id'] == target_team['id']):
                opponent_id = m['team2_id'] if m['team1_id'] == target_team['id'] else m['team1_id']
                opp_team = database.get_team(opponent_id) if opponent_id else None

                database.update_match_result(
                    match_id=m['id'],
                    score1=0 if m['team1_id'] == target_team['id'] else 1,
                    score2=1 if m['team1_id'] == target_team['id'] else 0,
                    winner_id=opponent_id,
                    status='completed',
                    proof_url="DQ Resolution"
                )

                if m['match_room_channel_id']:
                    chan = interaction.guild.get_channel(m['match_room_channel_id'])
                    if chan:
                        try: await chan.delete()
                        except: pass

        res = tournament.check_and_advance_stage(t_data['id'])
        if res:
            await views.handle_stage_advancement(interaction.guild, t_data['id'], res)

        await interaction.followup.send(f"✅ Team **{target_team['name']}** has been disqualified.", ephemeral=True)

    @app_commands.command(name="removeteam", description="Remove a team from registration.")
    @is_admin_or_staff()
    @app_commands.autocomplete(team_name=autocomplete_teams)
    async def removeteam(self, interaction: discord.Interaction, team_name: str):
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.response.send_message("❌ No active tournament.", ephemeral=True)
            return

        if t_data['stage'] != "Registration":
            await interaction.response.send_message("❌ Registration has already closed. Use DQ command instead.", ephemeral=True)
            return

        teams = database.get_tournament_teams(t_data['id'])
        target_team = None
        for t in teams:
            if t['name'].lower() == team_name.lower():
                target_team = t
                break

        if not target_team:
            await interaction.response.send_message(f"❌ Team '{team_name}' not found.", ephemeral=True)
            return

        confirm = views.ConfirmView()
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to remove **{target_team['name']}** from registration?",
            view=confirm, ephemeral=True
        )
        await confirm.wait()
        if not confirm.value:
            return

        await interaction.edit_original_response(content="Removing team...", view=None)

        database.remove_team(t_data['id'], target_team['id'])
        await views.update_main_embed(interaction.guild, t_data)
        await interaction.followup.send(f"✅ Team **{target_team['name']}** removed from registration.", ephemeral=True)

    @app_commands.command(name="reset", description="Wipe current active tournament (Force Clean).")
    @is_admin_or_staff()
    async def reset_bot(self, interaction: discord.Interaction):
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.response.send_message("⚠️ No active tournament found to reset.", ephemeral=True)
            return

        confirm = views.ConfirmView()
        await interaction.response.send_message(
            "🚨 **This will permanently delete the active tournament and all data.** Are you sure?",
            view=confirm, ephemeral=True
        )
        await confirm.wait()
        if not confirm.value:
            return

        await interaction.edit_original_response(content="Wiping tournament data...", view=None)

        database.delete_tournament(t_data['id'])
        await interaction.followup.send("🚨 **Active tournament has been wiped from database.**", ephemeral=True)

    @app_commands.command(name="refresh", description="Re-post all system embeds with the new look.")
    @is_admin_or_staff()
    async def refresh_embeds(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        config = database.get_guild_config(guild.id)
        config_v3 = database.get_guild_config_v3(guild.id)

        refreshed = []

        # Refresh tournament hub
        t_data = database.get_active_tournament(guild.id)
        if t_data and config:
            await views.update_main_embed(guild, t_data)
            refreshed.append("Tournament Hub")

        # Refresh tier portal
        if config_v3 and config_v3.get('tier_channel_id'):
            chan = guild.get_channel(config_v3['tier_channel_id'])
            if chan:
                await chan.purge(limit=10)
                embed = embeds.tier_test_hub_embed()
                await chan.send(embed=embed, view=views.TierGamemodeSelect())
                if config_v3.get('tier_queue_channel_id'):
                    qchan = guild.get_channel(config_v3['tier_queue_channel_id'])
                    if qchan:
                        await qchan.purge(limit=10)
                        qembed = embeds.tier_queue_main_embed(guild)
                        await qchan.send(embed=qembed, view=views.TierQueueView())
                refreshed.append("Tier Portal")

        # Refresh ranked hub
        if config_v3 and config_v3.get('ranked_queue_channel_id'):
            chan = guild.get_channel(config_v3['ranked_queue_channel_id'])
            if chan:
                await chan.purge(limit=10)
                embed = embeds.ranked_hub_embed("Skywars", 0)
                await chan.send(embed=embed, view=views.RankedGamemodeSelect())
                refreshed.append("Ranked Hub")

        # Refresh ticket panel
        if config_v3 and config_v3.get('ticket_category_id'):
            tc = database.get_guild_config_v3(guild.id)
            # find the ticket panel channel (usually bot-config or a dedicated channel)
            if config and config.get('bot_config_channel_id'):
                chan = guild.get_channel(config['bot_config_channel_id'])
                if chan:
                    await chan.purge(limit=10)
                    embed = embeds.ticket_panel_embed()
                    await chan.send(embed=embed, view=ticket_system.TicketPanelView())
                    refreshed.append("Ticket Panel")

        # Refresh comp panel
        comp_cfg = database.get_comp_config(guild.id)
        if comp_cfg and comp_cfg.get('channel_id'):
            chan = guild.get_channel(comp_cfg['channel_id'])
            if chan:
                await chan.purge(limit=10)
                embed = discord.Embed(title="⚔️ Competitive 1v1", description="Challenge other players!", color=embeds.COLOR_PURPLE)
                await chan.send(embed=embed, view=comp_system.CompPanelView())
                refreshed.append("Comp Panel")

        msg = "✅ Refreshed: " + ", ".join(refreshed) if refreshed else "No system embeds found to refresh."
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="setstage", description="Manually override the current stage.")
    @is_admin_or_staff()
    @app_commands.choices(
        stage=[
            app_commands.Choice(name="Registration", value="Registration"),
            app_commands.Choice(name="Check-in", value="Check-in"),
            app_commands.Choice(name="Group Stage", value="Group Stage"),
            app_commands.Choice(name="Qualifiers", value="Qualifiers"),
            app_commands.Choice(name="Semis", value="Semis"),
            app_commands.Choice(name="Finals", value="Finals"),
            app_commands.Choice(name="Ended", value="Ended")
        ]
    )
    async def set_stage(self, interaction: discord.Interaction, stage: str):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
        database.update_tournament_stage(t_data['id'], stage)
        t_updated = database.get_tournament(t_data['id'])
        await views.update_main_embed(interaction.guild, t_updated)
        await interaction.followup.send(f"✅ Stage manually set to **{stage}**.", ephemeral=True)

    @app_commands.command(name="seed", description="Set bracket seeding order for teams.")
    @is_admin_or_staff()
    @app_commands.autocomplete(team_name=autocomplete_teams)
    async def seed(self, interaction: discord.Interaction, team_name: str, seed_number: int):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return

        teams = database.get_tournament_teams(t_data['id'])
        target = None
        for t in teams:
            if t['name'].lower() == team_name.lower():
                target = t
                break

        if not target:
            await interaction.followup.send(f"❌ Team '{team_name}' not found.", ephemeral=True)
            return

        database.update_team_seed(target['id'], seed_number)
        await interaction.followup.send(f"✅ **{target['name']}** seeded at position **#{seed_number}**.", ephemeral=True)

    @app_commands.command(name="schedule", description="Schedule a match for a specific date/time.")
    @is_admin_or_staff()
    @app_commands.autocomplete(match_id=autocomplete_matches)
    async def schedule(self, interaction: discord.Interaction, match_id: int, date_time: str):
        await interaction.response.defer(ephemeral=True)
        match = database.get_match(match_id)
        if not match:
            await interaction.followup.send("❌ Match not found.", ephemeral=True)
            return

        database.update_match_schedule(match_id, date_time)
        await interaction.followup.send(f"✅ Match #{match_id} scheduled for **{date_time}**.", ephemeral=True)

    @app_commands.command(name="listteams", description="List all registered teams.")
    async def listteams(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return

        teams = database.get_tournament_teams(t_data['id'])
        if not teams:
            await interaction.followup.send("📭 No teams registered yet.", ephemeral=True)
            return

        per_page = 10
        embeds = []
        for i in range(0, len(teams), per_page):
            chunk = teams[i:i + per_page]
            desc_lines = []
            for t in chunk:
                desc_lines.append(f"**{t['name']}** — Captain: <@{t['captain_id']}> | Status: `{t['status']}`")
            embed = discord.Embed(
                title=f"📋 Registered Teams — {t_data['name']}",
                description="\n".join(desc_lines),
                color=embeds.COLOR_BLUE if hasattr(embeds, 'COLOR_BLUE') else 0x3498db
            )
            embeds.append(embed)

        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            await interaction.followup.send(embed=embeds[0], view=views.PaginationView(embeds), ephemeral=True)

    # =====================================================================
    # PLAYER COMMANDS
    # =====================================================================
    
    @app_commands.command(name="enter", description="Register your team for the active tournament.")
    async def enter(self, interaction: discord.Interaction):
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.response.send_message("❌ No active tournament found.", ephemeral=True)
            return
        if t_data['stage'] != "Registration":
            await interaction.response.send_message("❌ Registration is closed.", ephemeral=True)
            return
        # Launch modal
        await interaction.response.send_modal(views.RegistrationModal(t_data['id']))

    @app_commands.command(name="leave", description="Withdraw your team from the active tournament.")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament found.", ephemeral=True)
            return
        if t_data['stage'] != "Registration":
            await interaction.followup.send("❌ Cannot leave: tournament registration is closed.", ephemeral=True)
            return
            
        team = database.get_team_by_player(t_data['id'], interaction.user.id)
        if not team:
            await interaction.followup.send("❌ You are not registered in this tournament.", ephemeral=True)
            return
            
        database.remove_team(t_data['id'], team['id'])
        await views.update_main_embed(interaction.guild, t_data)
        await interaction.followup.send(f"✅ Your team **{team['name']}** has been withdrawn.", ephemeral=True)

    @app_commands.command(name="checkin", description="Confirm attendance for the tournament.")
    async def checkin(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
        if t_data['stage'] != "Check-in":
            await interaction.followup.send("❌ Tournament is not in Check-in stage.", ephemeral=True)
            return
            
        team = database.get_team_by_player(t_data['id'], interaction.user.id)
        if not team:
            await interaction.followup.send("❌ You are not registered in this tournament.", ephemeral=True)
            return
            
        if team['status'] == 'checked_in':
            await interaction.followup.send("🟢 Your team is already checked in.", ephemeral=True)
            return
            
        database.update_team_status(team['id'], 'checked_in')
        await views.update_main_embed(interaction.guild, t_data)
        await interaction.followup.send(f"🟢 **{team['name']}** checked in successfully!", ephemeral=True)

    @app_commands.command(name="match", description="Show details of your current match.")
    async def show_match(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
            
        team = database.get_team_by_player(t_data['id'], interaction.user.id)
        if not team:
            await interaction.followup.send("❌ You are not registered in this tournament.", ephemeral=True)
            return
            
        # Find active match
        matches = database.get_tournament_matches(t_data['id'])
        active_match = None
        for m in matches:
            if m['status'] in ('pending', 'active') and (m['team1_id'] == team['id'] or m['team2_id'] == team['id']):
                active_match = m
                break
                
        if not active_match:
            await interaction.followup.send("⚪ You do not have any active or pending matches currently.", ephemeral=True)
            return
            
        opp_id = active_match['team2_id'] if active_match['team1_id'] == team['id'] else active_match['team1_id']
        opp_team = database.get_team(opp_id) if opp_id else None
        
        embed = discord.Embed(
            title=f"⚔️ Match #{active_match['id']} details",
            color=embeds.COLOR_PURPLE
        )
        embed.add_field(name="Your Team", value=f"**{team['name']}**", inline=True)
        embed.add_field(name="Opponent", value=f"**{opp_team['name'] if opp_team else 'BYE'}**", inline=True)
        if active_match['match_room_channel_id']:
            embed.add_field(name="Channel", value=f"<#{active_match['match_room_channel_id']}>", inline=False)
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="bracket", description="Show the current live bracket.")
    async def bracket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
        matches = database.get_tournament_matches(t_data['id'])
        teams = database.get_tournament_teams(t_data['id'])
        if not matches:
            embed = embeds.bracket_embed(t_data, matches, teams)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        team_names = {t['id']: t['name'] for t in teams}
        team_names[None] = "BYE"
        stages_grouped = {}
        for m in matches:
            st = m['stage']
            stages_grouped.setdefault(st, []).append(m)

        embeds_list = []
        for st, st_matches in stages_grouped.items():
            e = discord.Embed(title=f"📜 {t_data['name']} — {st}", color=embeds.get_stage_color(t_data['stage']) if hasattr(embeds, 'get_stage_color') else 0x2ecc71)
            lines = []
            for m in st_matches:
                t1 = team_names.get(m['team1_id'], "TBD")
                t2 = team_names.get(m['team2_id'], "TBD")
                if m['status'] == 'completed':
                    lines.append(f"~~#{m['id']}: {t1} vs {t2}~~ ✅")
                elif m['status'] == 'active':
                    lines.append(f"⚔️ #{m['id']}: **{t1}** vs **{t2}** <#{m['match_room_channel_id']}>")
                else:
                    lines.append(f"⚪ #{m['id']}: **{t1}** vs **{t2}**")
            e.description = "\n".join(lines)
            e.set_footer(text=f"Page {len(embeds_list) + 1}/{len(stages_grouped)}")
            embeds_list.append(e)

        if len(embeds_list) == 1:
            await interaction.followup.send(embed=embeds_list[0], ephemeral=True)
        else:
            await interaction.followup.send(embed=embeds_list[0], view=views.PaginationView(embeds_list), ephemeral=True)

    @app_commands.command(name="standings", description="Show the current rankings (paginated).")
    async def standings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
        teams = database.get_tournament_teams(t_data['id'])
        if not teams:
            await interaction.followup.send("📭 No teams registered yet.", ephemeral=True)
            return

        sorted_teams = sorted(teams, key=lambda x: (x['points'], x['wins'], -x['losses']), reverse=True)
        per_page = 15
        embeds_list = []
        for i in range(0, len(sorted_teams), per_page):
            chunk = sorted_teams[i:i + per_page]
            desc_lines = []
            for idx, t in enumerate(chunk, start=i + 1):
                desc_lines.append(f"#{idx} **{t['name']}** — {t['wins']}W/{t['losses']}L | {t['points']}pts | `{t['status']}`")
            embed = discord.Embed(
                title=f"📊 {t_data['name']} — Standings",
                description="\n".join(desc_lines),
                color=0x3498db
            )
            embed.set_footer(text=f"Page {len(embeds_list) + 1}/{(len(sorted_teams) + per_page - 1) // per_page}")
            embeds_list.append(embed)

        if len(embeds_list) == 1:
            await interaction.followup.send(embed=embeds_list[0], ephemeral=True)
        else:
            await interaction.followup.send(embed=embeds_list[0], view=views.PaginationView(embeds_list), ephemeral=True)

    @app_commands.command(name="stats", description="Show team or player stats.")
    @app_commands.autocomplete(team_name=autocomplete_teams)
    async def stats(self, interaction: discord.Interaction, player: discord.Member = None, team_name: str = None):
        await interaction.response.defer(ephemeral=True)
        
        # If user queried a team name
        if team_name:
            t_data = database.get_active_tournament(interaction.guild.id)
            if not t_data:
                await interaction.followup.send("❌ No active tournament.", ephemeral=True)
                return
            teams = database.get_tournament_teams(t_data['id'])
            target = None
            for t in teams:
                if t['name'].lower() == team_name.lower():
                    target = t
                    break
            if not target:
                await interaction.followup.send(f"❌ Team '{team_name}' not found.", ephemeral=True)
                return
                
            embed = discord.Embed(title=f"👥 Team Stats - {target['name']}", color=embeds.COLOR_BLUE)
            embed.add_field(name="Captain", value=f"<@{target['captain_id']}>", inline=True)
            if target['player2_id']:
                embed.add_field(name="Player 2", value=f"<@{target['player2_id']}>", inline=True)
            embed.add_field(name="Wins", value=f"`{target['wins']}`", inline=True)
            embed.add_field(name="Losses", value=f"`{target['losses']}`", inline=True)
            embed.add_field(name="Points", value=f"`{target['points']}`", inline=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        # Else queried player (default is author)
        target_player = player or interaction.user
        p_stats = database.get_player_stats(target_player.id)
        if not p_stats:
            # Build default empty record
            p_stats = {
                "user_id": target_player.id,
                "username": target_player.name,
                "wins": 0,
                "losses": 0,
                "tournaments_played": 0,
                "championships_won": 0,
                "mvp_count": 0,
                "season_points": 0
            }
            # Save it
            database.update_player_stat(target_player.id, target_player.name)
            
        embed = embeds.player_stats_embed(target_player.id, p_stats)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="history", description="Show champions history (paginated).")
    async def history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        records = database.get_history(limit=100)
        if not records:
            embed = embeds.history_embed([])
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        per_page = 5
        embeds_list = []
        for i in range(0, len(records), per_page):
            chunk = records[i:i + per_page]
            e = discord.Embed(title="📂 TOURNAMENT HALL OF FAME", color=0xf1c40f)
            for rec in chunk:
                e.add_field(
                    name=f"🏆 {rec['name']} (Season {rec['season']})",
                    value=(
                        f"🎮 Mode: `{rec['mode']}` | Format: `{rec['format']}`\n"
                        f"🥇 Winner: **{rec['champion_team_name']}** (<@{rec['champion_captain_id']}>)\n"
                        f"🥈 Runner-Up: **{rec['runner_up_team_name']}**\n"
                        f"📅 Ended: *{rec['date_ended']}*"
                    ),
                    inline=False
                )
            e.set_footer(text=f"Page {len(embeds_list) + 1}/{(len(records) + per_page - 1) // per_page}")
            embeds_list.append(e)

        if len(embeds_list) == 1:
            await interaction.followup.send(embed=embeds_list[0], ephemeral=True)
        else:
            await interaction.followup.send(embed=embeds_list[0], view=views.PaginationView(embeds_list), ephemeral=True)

    @app_commands.command(name="rules", description="Show tournament rules.")
    async def rules(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        t_data = database.get_active_tournament(interaction.guild.id)
        if not t_data:
            await interaction.followup.send("❌ No active tournament.", ephemeral=True)
            return
        embed = discord.Embed(title="📖 Tournament Rules", description=t_data['rules'] or "No specific rules set.", color=embeds.COLOR_BLUE)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="season", description="Show season points leaderboard.")
    async def season_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        leaders = database.get_season_leaderboard(limit=10)
        
        embed = discord.Embed(
            title="⭐ SEASON LEADERBOARD",
            description="Overall player rankings by season points.",
            color=embeds.COLOR_GOLD
        )
        
        if not leaders:
            embed.description = "No players have scored season points yet."
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
            
        lines = []
        for idx, leader in enumerate(leaders):
            lines.append(f"#{idx+1} <@{leader['user_id']}> - **{leader['season_points']}** pts | 🏆 `{leader['championships_won']}` Wins")
            
        embed.description = "\n".join(lines)
        await interaction.followup.send(embed=embed, ephemeral=True)

# =====================================================================
# WEB SERVER FOR RENDER HEALTH CHECKS
# =====================================================================
import aiohttp
from aiohttp import web

async def health_check(request):
    return web.Response(text="OK", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health check server running on port {port}")

async def main():
    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    if TOKEN and TOKEN != "your_discord_token_here":
        import asyncio
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            pass
    else:
        print("⚠️ Warning: DISCORD_TOKEN is not configured in .env. Bot is running in offline validation mode.")
