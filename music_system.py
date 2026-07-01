import discord
import wavelink
from discord import app_commands
from discord.ext import commands
import re
import datetime

LAVALINK_URI = "https://lavalink.jirayu.net:443"
LAVALINK_PASSWORD = "youshallnotpass"

COLOR_NOW = 0x1DB954
COLOR_ERR = 0xFF5555
COLOR_Q = 0x9B59B6

guild_data = {}

def get_gd(guild_id: int) -> dict:
    if guild_id not in guild_data:
        guild_data[guild_id] = {"text_channel_id": None, "loop": False}
    return guild_data[guild_id]

async def connect_lavalink(bot: commands.Bot):
    node = wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)
    await wavelink.Pool.connect(client=bot, nodes=[node])

def setup_events(bot: commands.Bot):

    @bot.listen()
    async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Lavalink ready — {payload.node.identifier}")

    @bot.listen()
    async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return
        gd = get_gd(player.guild.id)
        if gd.get("loop") and payload.track:
            await player.queue.put_wait(payload.track)
        if not player.queue.is_empty:
            next_track = player.queue.get()
            await player.play(next_track)
            ch = player.guild.get_channel(gd.get("text_channel_id"))
            if ch:
                await ch.send(embed=_np_embed(next_track, player), view=MusicControlView())

    @bot.listen()
    async def on_wavelink_track_stuck(payload: wavelink.TrackStuckEventPayload):
        player = payload.player
        if not player:
            return
        gd = get_gd(player.guild.id)
        ch = player.guild.get_channel(gd.get("text_channel_id"))
        if ch:
            await ch.send("⚠️ Track stuck — skipping...")
        if not player.queue.is_empty:
            await player.play(player.queue.get())

    @bot.listen()
    async def on_wavelink_track_exception(payload: wavelink.TrackExceptionEventPayload):
        player = payload.player
        if not player:
            print(f"⚠️ Track exception (no player): {payload.message}")
            return
        gd = get_gd(player.guild.id)
        ch = player.guild.get_channel(gd.get("text_channel_id"))
        if ch:
            await ch.send(f"❌ Playback error: `{payload.message}`")
        if not player.queue.is_empty:
            await player.play(player.queue.get())

def fmt_dur(ms: int) -> str:
    if ms <= 0:
        return "🔴 Live"
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def prog_bar(cur: int, total: int, length: int = 16) -> str:
    if total <= 0:
        return "`[━" + "━" * length + "]`"
    filled = round((cur / total) * length)
    bar = "▰" * filled + "▱" * (length - filled)
    pct = round((cur / total) * 100)
    return f"`[{bar}]` **{pct}%**"

def _np_embed(track: wavelink.tracks.Playable, player: wavelink.Player) -> discord.Embed:
    pos = player.position
    dur = track.length
    embed = discord.Embed(color=COLOR_NOW)
    embed.set_author(name="🎵 NOW PLAYING", icon_url="https://i.imgur.com/g8o468o.png")
    embed.set_thumbnail(url=getattr(track, "artwork", None) or "https://i.imgur.com/g8o468o.png")
    loop_emoji = "🔁" if get_gd(player.guild.id).get("loop") else ""
    embed.description = (
        f"**[{track.title}]({track.uri})**\n"
        f"`{track.author}`\n\n"
        f"{prog_bar(pos, dur)}\n"
        f"`{fmt_dur(pos)}` ─ `{fmt_dur(dur)}` {loop_emoji}"
    )
    embed.set_footer(text="SELESTER V3 • Lavalink Powered", icon_url="https://i.imgur.com/g8o468o.png")
    return embed

class MusicControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    def _player(self, i: discord.Interaction) -> wavelink.Player | None:
        return i.guild.voice_client

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary, row=0, custom_id="music_toggle")
    async def toggle_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._player(i)
        if not p:
            await i.response.send_message("❌ No player.", ephemeral=True)
            return
        if p.playing:
            await p.pause(True)
            b.emoji = "▶️"
        elif p.paused:
            await p.pause(False)
            b.emoji = "⏸️"
        else:
            await i.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        await i.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.primary, row=0, custom_id="music_skip_btn")
    async def skip_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._player(i)
        if not p or not p.playing:
            await i.response.send_message("❌ Nothing playing.", ephemeral=True)
            return
        await p.stop()
        await i.response.send_message("⏭️ Skipped", ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger, row=0, custom_id="music_stop_btn")
    async def stop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._player(i)
        if not p:
            await i.response.send_message("❌ Not in voice.", ephemeral=True)
            return
        gd = get_gd(i.guild_id)
        gd["loop"] = False
        p.queue.clear()
        await p.stop()
        await p.disconnect()
        await i.response.send_message("⏹️ Stopped & left.", ephemeral=True)

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.secondary, row=1, custom_id="music_loop_btn")
    async def loop_btn(self, i: discord.Interaction, b: discord.ui.Button):
        gd = get_gd(i.guild_id)
        gd["loop"] = not gd["loop"]
        b.style = discord.ButtonStyle.success if gd["loop"] else discord.ButtonStyle.secondary
        await i.response.edit_message(view=self)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary, row=1, custom_id="music_voldown")
    async def voldown_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._player(i)
        if not p:
            await i.response.send_message("❌ No player.", ephemeral=True)
            return
        vol = max(0, p.volume - 10)
        await p.set_volume(vol)
        await i.response.send_message(f"🔉 Volume **{vol}%**", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary, row=1, custom_id="music_volup")
    async def volup_btn(self, i: discord.Interaction, b: discord.ui.Button):
        p = self._player(i)
        if not p:
            await i.response.send_message("❌ No player.", ephemeral=True)
            return
        vol = min(100, p.volume + 10)
        await p.set_volume(vol)
        await i.response.send_message(f"🔊 Volume **{vol}%**", ephemeral=True)

class MusicGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="music", description="🎵 Music system commands")

    @app_commands.command(name="setup", description="Set up the music system in existing channels.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Existing channel for music commands",
        category="Existing category for the music system (optional)"
    )
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel, category: discord.CategoryChannel = None):
        await interaction.response.defer(ephemeral=True)
        import database
        guild = interaction.guild
        category = category or channel.category
        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg["music_channel_id"] = channel.id
        cfg["music_category_id"] = category.id if category else None
        database.save_guild_config_v3(interaction.guild_id, cfg)
        embed = discord.Embed(
            title="✅ MUSIC SYSTEM ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**Commands channel:** {channel.mention}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "`/music playmusic` — Search & play\n"
                "`/music stop` — Stop & leave\n"
                "`/music skip` — Skip current\n"
                "`/music queue` — View queue\n"
                "`/music pause` / `resume`\n"
                "`/music volume` — Set volume\n"
                "`/music nowplaying` — Current song\n"
                "`/music loop` — Toggle loop"
            ),
            color=COLOR_NOW
        )
        embed.set_footer(text="SELESTER V3 • Music System")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="playmusic", description="Search and play a song from YouTube.")
    @app_commands.describe(query="Song name or URL")
    async def playmusic(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not wavelink.Pool.nodes:
            await interaction.followup.send("❌ Lavalink not connected. Try again in a moment.", ephemeral=True)
            return

        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Join a voice channel first.", ephemeral=True)
            return

        vc = interaction.user.voice.channel

        if interaction.guild.voice_client:
            player: wavelink.Player = interaction.guild.voice_client
            if player.channel != vc:
                await player.move_to(vc)
        else:
            try:
                player = await vc.connect(cls=wavelink.Player)
            except Exception as e:
                await interaction.followup.send(f"❌ Can't connect: {e}", ephemeral=True)
                return

        gd = get_gd(interaction.guild_id)
        gd["text_channel_id"] = interaction.channel_id

        await interaction.followup.send(f"🔍 Searching `{query}`...")

        url_pat = re.compile(r"^https?://")
        search = query if url_pat.match(query) else f"ytsearch:{query}"

        try:
            result = await wavelink.Pool.fetch_tracks(search)
        except Exception as e:
            await interaction.channel.send(f"❌ Search failed: {e}")
            return

        if not result:
            await interaction.channel.send("❌ No results.")
            return

        if isinstance(result, wavelink.tracks.Playlist):
            tracks = list(result)
            first = tracks[0] if tracks else None
        else:
            tracks = result
            first = tracks[0]

        if not first:
            await interaction.channel.send("❌ No results.")
            return

        if player.playing or not player.queue.is_empty:
            pos = player.queue.put(first)
            embed = discord.Embed(
                title="📥 ADDED TO QUEUE",
                description=f"**[{first.title}]({first.uri})**\nPosition: `#{pos}`",
                color=COLOR_Q
            )
            embed.set_thumbnail(url=getattr(first, "artwork", None) or "https://i.imgur.com/g8o468o.png")
            await interaction.channel.send(embed=embed)
        else:
            await player.play(first)
            await interaction.channel.send(embed=_np_embed(first, player), view=MusicControlView())

    @app_commands.command(name="stop", description="Stop playback and leave voice.")
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.followup.send("❌ Not in a voice channel.", ephemeral=True)
            return
        player.queue.clear()
        gd = get_gd(interaction.guild_id)
        gd["loop"] = False
        await player.stop()
        await player.disconnect()
        embed = discord.Embed(title="⏹️ STOPPED", description="Cleared queue & left.", color=COLOR_ERR)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.followup.send("❌ Nothing playing.", ephemeral=True)
            return
        await player.stop()
        await interaction.followup.send(embed=discord.Embed(title="⏭️ SKIPPED", color=COLOR_NOW), ephemeral=True)

    @app_commands.command(name="queue", description="View the song queue.")
    async def queue_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.followup.send("❌ No player active.", ephemeral=True)
            return

        q = list(player.queue)
        embed = discord.Embed(title="🎵 MUSIC QUEUE", color=COLOR_Q)

        if player.current:
            t = player.current
            embed.add_field(
                name="▶️ NOW PLAYING",
                value=f"**[{t.title}]({t.uri})**\n`{t.author}` ─ `{fmt_dur(t.length)}`",
                inline=False
            )

        if q:
            lines = []
            for i, s in enumerate(q[:10], 1):
                lines.append(f"`#{i}` **{s.title}** — `{fmt_dur(s.length)}`")
            embed.add_field(name="📋 UP NEXT", value="\n".join(lines), inline=False)
            if len(q) > 10:
                embed.set_footer(text=f"+ {len(q) - 10} more songs")
        else:
            embed.add_field(name="📋 UP NEXT", value="Queue is empty.", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="pause", description="Pause playback.")
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.followup.send("❌ Nothing playing.", ephemeral=True)
            return
        await player.pause(True)
        embed = discord.Embed(title="⏸️ PAUSED", color=COLOR_ERR)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback.")
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.paused:
            await interaction.followup.send("❌ Nothing paused.", ephemeral=True)
            return
        await player.pause(False)
        embed = discord.Embed(title="▶️ RESUMED", color=COLOR_NOW)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="loop", description="Toggle queue looping.")
    async def loop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gd = get_gd(interaction.guild_id)
        gd["loop"] = not gd["loop"]
        status = "🔁 **Enabled**" if gd["loop"] else "➡️ **Disabled**"
        embed = discord.Embed(title="LOOP", description=status, color=COLOR_Q)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="volume", description="Set volume (0–100).")
    @app_commands.describe(level="Volume level 0–100")
    async def volume(self, interaction: discord.Interaction, level: int):
        await interaction.response.defer(ephemeral=True)
        if level < 0 or level > 100:
            await interaction.followup.send("❌ Must be 0–100.", ephemeral=True)
            return
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.followup.send("❌ Not connected.", ephemeral=True)
            return
        await player.set_volume(level)
        embed = discord.Embed(title="🔊 VOLUME", description=f"Set to **{level}%**", color=COLOR_NOW)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="nowplaying", description="Current song info.")
    async def nowplaying(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing or not player.current:
            await interaction.followup.send("❌ Nothing playing.", ephemeral=True)
            return
        embed = _np_embed(player.current, player)
        await interaction.followup.send(embed=embed, ephemeral=True)
