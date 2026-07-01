import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import re

USER_MENTION_PATTERN = re.compile(r"<@!?(\d+)>")

# =====================================================================
# MODALS
# =====================================================================

class CompChallengeModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="⚔️ 1v1 Comp Challenge")

        self.opponent_ign = discord.ui.TextInput(
            label="Opponent IGN",
            placeholder="e.g. Naitik_123",
            min_length=2,
            max_length=32,
            required=True
        )
        self.add_item(self.opponent_ign)

        self.opponent_user = discord.ui.TextInput(
            label="Opponent Discord (name or @mention)",
            placeholder="e.g. @Naitik or Naitik#1234",
            min_length=2,
            max_length=64,
            required=True
        )
        self.add_item(self.opponent_user)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        challenger = interaction.user
        opp_ign = self.opponent_ign.value.strip()
        opp_raw = self.opponent_user.value.strip()

        opponent = None
        m = USER_MENTION_PATTERN.match(opp_raw)
        if m:
            opponent = guild.get_member(int(m.group(1)))
        else:
            name_lower = opp_raw.lower().replace("!", "")
            for member in guild.members:
                if member.display_name.lower() == name_lower or str(member).lower() == name_lower or member.name.lower() == name_lower:
                    opponent = member
                    break

        if not opponent:
            await interaction.followup.send("❌ Could not find that user in this server. Try using their @mention.", ephemeral=True)
            return

        if opponent.id == challenger.id:
            await interaction.followup.send("❌ You cannot challenge yourself!", ephemeral=True)
            return

        if opponent.bot:
            await interaction.followup.send("❌ You cannot challenge a bot!", ephemeral=True)
            return

        cfg = database.get_comp_config(guild.id)
        if not cfg or not cfg.get('channel_id'):
            await interaction.followup.send("❌ Comp system not set up. Ask an admin to run `/comp setup`.", ephemeral=True)
            return

        channel = guild.get_channel(cfg['channel_id'])
        if not channel:
            await interaction.followup.send("❌ Comp channel not found.", ephemeral=True)
            return

        challenger_ign = database.get_or_create_comp_player(challenger.id, guild.id, challenger.display_name).get('ign') or challenger.display_name

        match_id = database.create_comp_match(
            guild_id=guild.id,
            channel_id=channel.id,
            challenger_id=challenger.id,
            opponent_id=opponent.id,
            challenger_ign=challenger_ign,
            opponent_ign=opp_ign
        )

        embed = discord.Embed(
            title="⚔️ 1v1 COMP CHALLENGE!",
            description=(
                f"🔥 **{challenger.mention}** (`{challenger_ign}`) has challenged **{opponent.mention}** (`{opp_ign}`) for a 1v1 comp match!\n\n"
                f"📌 **Match ID:** `#{match_id}`\n\n"
                f"▸ Winner gets **+10 points** 🏆\n"
                f"▸ Loser gets **+1 point** 💪\n\n"
                f"**__Opponent__**, do you accept? 👇"
            ),
            color=0xe74c3c
        )
        embed.set_footer(text="Challenge expires in 5 minutes")
        view = ChallengeView(match_id, challenger.id, opponent.id)
        msg = await channel.send(embed=embed, view=view)
        view._channel_id = channel.id
        view._message_id = msg.id

        database.update_comp_match_status(match_id, 'pending')
        with database.get_db() as conn:
            conn.execute("UPDATE comp_matches SET message_id = ? WHERE id = ?", (msg.id, match_id))
            conn.commit()

        await interaction.followup.send(f"✅ Challenge sent to {opponent.mention} in {channel.mention}!", ephemeral=True)

# =====================================================================
# VIEWS
# =====================================================================

class ChallengeView(discord.ui.View):
    def __init__(self, match_id: int, challenger_id: int, opponent_id: int):
        super().__init__(timeout=300)
        self.match_id = match_id
        self.challenger_id = challenger_id
        self.opponent_id = opponent_id
        self._channel_id = None
        self._message_id = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="✅", row=0)
    async def accept_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This challenge is not for you.", ephemeral=True)
            return

        database.update_comp_match_status(self.match_id, 'accepted')

        embed = discord.Embed(
            title="✅ CHALLENGE ACCEPTED!",
            description=(
                f"🎮 Match #{self.match_id} is now **active**!\n\n"
                f"**Players:**\n"
                f"🔴 <@{self.challenger_id}>\n"
                f"🔵 <@{self.opponent_id}>\n\n"
                f"Once you've played, report the winner below 👇"
            ),
            color=0x2ecc71
        )
        await interaction.response.edit_message(embed=embed, view=CompResultView(self.match_id, self.challenger_id, self.opponent_id))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌", row=0)
    async def decline_challenge(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent_id:
            await interaction.response.send_message("❌ This challenge is not for you.", ephemeral=True)
            return

        database.update_comp_match_status(self.match_id, 'declined')

        embed = discord.Embed(
            title="❌ CHALLENGE DECLINED",
            description=f"<@{self.opponent_id}> declined the challenge from <@{self.challenger_id}>.",
            color=0x95a5a6
        )
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        match = database.get_comp_match(self.match_id)
        if match and match['status'] == 'pending':
            database.update_comp_match_status(self.match_id, 'expired')

class CompResultView(discord.ui.View):
    def __init__(self, match_id: int, player1_id: int, player2_id: int):
        super().__init__(timeout=300)
        self.match_id = match_id
        self.player1_id = player1_id
        self.player2_id = player2_id

    @discord.ui.button(label="Player 1 Won", style=discord.ButtonStyle.primary, emoji="🏆", row=0)
    async def player1_wins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._report_winner(interaction, self.player1_id)

    @discord.ui.button(label="Player 2 Won", style=discord.ButtonStyle.primary, emoji="🏆", row=0)
    async def player2_wins(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._report_winner(interaction, self.player2_id)

    @discord.ui.button(label="Cancel Match", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def cancel_match(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.player1_id, self.player2_id):
            await interaction.response.send_message("❌ Only match participants can cancel.", ephemeral=True)
            return

        database.update_comp_match_status(self.match_id, 'cancelled')
        embed = discord.Embed(
            title="🗑️ MATCH CANCELLED",
            description=f"The match between <@{self.player1_id}> and <@{self.player2_id}> was cancelled.",
            color=0x95a5a6
        )
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    async def _report_winner(self, interaction: discord.Interaction, winner_id: int):
        if interaction.user.id not in (self.player1_id, self.player2_id):
            await interaction.response.send_message("❌ Only match participants can report the result.", ephemeral=True)
            return

        loser_id = self.player2_id if winner_id == self.player1_id else self.player1_id

        guild = interaction.guild
        database.update_comp_match_status(self.match_id, 'completed', winner_id)

        winner_ign = database.get_or_create_comp_player(winner_id, guild.id).get('ign') or interaction.guild.get_member(winner_id).display_name
        loser_ign = database.get_or_create_comp_player(loser_id, guild.id).get('ign') or interaction.guild.get_member(loser_id).display_name

        database.award_comp_points(winner_id, guild.id, 10, winner_ign)
        database.award_comp_points(loser_id, guild.id, 1, loser_ign)
        database.record_comp_win(winner_id, guild.id, winner_ign)
        database.record_comp_loss(loser_id, guild.id, loser_ign)

        embed = discord.Embed(
            title="🏆 MATCH COMPLETE!",
            description=(
                f"**Winner:** <@{winner_id}> (`{winner_ign}`) — 🎉 **+10 points**\n"
                f"**Loser:** <@{loser_id}> (`{loser_ign}`) — 💪 **+1 point**\n\n"
                f"GGs to both players! 👏"
            ),
            color=0xf1c40f
        )
        embed.set_footer(text=f"Match #{self.match_id}")

        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

        # Playful random emoji reaction
        fun_emojis = ["👑", "🔥", "💀", "😱", "👏", "🎉", "🤝", "⚡", "💯"]
        import random
        try:
            await interaction.message.add_reaction(random.choice(fun_emojis))
        except:
            pass

class CompPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Comp Challenge", style=discord.ButtonStyle.danger, emoji="⚔️", row=0, custom_id="comp_panel_challenge")
    async def challenge_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CompChallengeModal())

# =====================================================================
# COMMAND GROUP
# =====================================================================

class CompGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="comp", description="1v1 Comp Challenge system")

    @app_commands.command(name="setup", description="Set up the comp challenge panel in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Existing channel for comp challenges")
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        database.set_comp_channel(guild.id, channel.id)

        embed = discord.Embed(
            title="⚔️ COMP CHALLENGES",
            description=(
                "```css\n\"Step up and prove who's the best!\"\n```\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "**Challenge someone to a 1v1!**\n"
                "▸ Click the button below to challenge another player\n"
                "▸ Winner gets **+10 points** 🏆\n"
                "▸ Loser gets **+1 point** 💪\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Use `/comp leaderboard` to see rankings!"
            ),
            color=0xe74c3c
        )
        embed.set_footer(text="Celestia • Comp System Online")

        view = CompPanelView()
        msg = await channel.send(embed=embed, view=view)
        bot_ref = interaction.client
        if hasattr(bot_ref, 'add_view') and callable(bot_ref.add_view):
            bot_ref.add_view(view, message_id=msg.id)

        await interaction.followup.send(f"✅ Comp system activated! Channel: {channel.mention}", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the comp points leaderboard.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        players = database.get_comp_leaderboard(interaction.guild_id, limit=20)
        if not players:
            await interaction.followup.send("📭 No comp matches played yet.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚔️ COMP LEADERBOARD",
            description="Top players ranked by comp points.",
            color=0xf1c40f
        )

        lines = []
        for idx, p in enumerate(players[:20]):
            badge = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉" if idx == 2 else f"#{idx+1}"
            ign_display = f" (`{p['ign']}`)" if p['ign'] else ""
            lines.append(
                f"{badge} <@{p['user_id']}>{ign_display}\n"
                f"> Points: **{p['points']}** | W: {p['wins']} L: {p['losses']} | Matches: {p['matches_played']}"
            )

        embed.description = "\n\n".join(lines)
        embed.set_footer(text="Celestia • Comp System")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="stats", description="Show your or another player's comp stats.")
    @app_commands.describe(player="Player to check (defaults to you)")
    async def stats(self, interaction: discord.Interaction, player: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        target = player or interaction.user

        p = database.get_comp_player(target.id, interaction.guild_id)
        if not p:
            await interaction.followup.send(f"📭 {target.display_name} hasn't played any comp matches yet.", ephemeral=True)
            return

        win_rate = round((p['wins'] / max(p['matches_played'], 1)) * 100)

        embed = discord.Embed(
            title=f"⚔️ Comp Stats — {target.display_name}",
            color=0x3498db
        )
        embed.add_field(name="IGN", value=f"`{p['ign'] or 'Not set'}`", inline=True)
        embed.add_field(name="Points", value=f"**{p['points']}**", inline=True)
        embed.add_field(name="Matches", value=f"{p['matches_played']}", inline=True)
        embed.add_field(name="Wins", value=f"🏆 {p['wins']}", inline=True)
        embed.add_field(name="Losses", value=f"💔 {p['losses']}", inline=True)
        embed.add_field(name="Win Rate", value=f"{win_rate}%", inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setign", description="Set your in-game name for comp challenges.")
    @app_commands.describe(ign="Your in-game name")
    async def setign(self, interaction: discord.Interaction, ign: str):
        await interaction.response.defer(ephemeral=True)

        if len(ign) < 2 or len(ign) > 32:
            await interaction.followup.send("❌ IGN must be between 2-32 characters.", ephemeral=True)
            return

        database.get_or_create_comp_player(interaction.user.id, interaction.guild_id, ign)
        database.update_comp_player_ign(interaction.user.id, interaction.guild_id, ign)
        await interaction.followup.send(f"✅ Your IGN has been set to `{ign}`.", ephemeral=True)