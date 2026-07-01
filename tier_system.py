import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds
import views

def is_tier_staff():
    async def predicate(interaction: discord.Interaction):
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg:
            return False
        if interaction.user.guild_permissions.administrator:
            return True
        roles = interaction.user.roles
        if cfg['tier_staff_role_id'] and interaction.guild.get_role(cfg['tier_staff_role_id']) in roles:
            return True
        if cfg['tier_tester_role_id'] and interaction.guild.get_role(cfg['tier_tester_role_id']) in roles:
            return True
        return False
    return app_commands.check(predicate)

class TierGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="tier", description="Tier test system commands")

    @app_commands.command(name="setup", description="Set up the tier test system in existing channels.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        tier_channel="Existing channel for tier test lobby",
        results_channel="Existing channel for tier results",
        ticket_category="Existing category where tier ticket channels will be created",
        staff_role="Role that can claim/close tier tickets",
        tester_role="Role for tier testers (optional)"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        tier_channel: discord.TextChannel,
        results_channel: discord.TextChannel,
        ticket_category: discord.CategoryChannel,
        staff_role: discord.Role,
        tester_role: discord.Role = None
    ):
        await interaction.response.defer(ephemeral=True)

        data = {
            "tier_channel_id": tier_channel.id,
            "tier_results_channel_id": results_channel.id,
            "ticket_category_id": ticket_category.id,
            "tier_staff_role_id": staff_role.id,
        }
        if tester_role:
            data["tier_tester_role_id"] = tester_role.id

        embed = embeds.tier_test_hub_embed()
        view = views.TierGamemodeSelect()
        msg = await tier_channel.send(embed=embed, view=view)
        data["tier_message_id"] = str(msg.id)

        database.save_guild_config_v3(interaction.guild_id, data)

        bot_ref = interaction.client
        if hasattr(bot_ref, 'add_view') and callable(bot_ref.add_view):
            bot_ref.add_view(view, message_id=msg.id)

        success = embeds.tiersetup_success_embed(tier_channel, results_channel, ticket_category, staff_role, tester_role)
        await interaction.followup.send(embed=success, ephemeral=True)

    @app_commands.command(name="remove", description="Delete the tier hub message and clear the channel config.")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('tier_channel_id'):
            await interaction.followup.send("❌ No tier system configured.", ephemeral=True)
            return
        tier_channel = interaction.guild.get_channel(cfg['tier_channel_id'])
        if tier_channel and cfg.get('tier_message_id'):
            try:
                msg = await tier_channel.fetch_message(int(cfg['tier_message_id']))
                await msg.delete()
            except:
                pass
        database.save_guild_config_v3(interaction.guild_id, {
            "tier_channel_id": None,
            "tier_results_channel_id": None,
            "ticket_category_id": None,
            "tier_message_id": None
        })
        embed = embeds.tier_remove_embed()
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setrole", description="Map a tier name to a role (auto-assigned on result).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(tier="Tier name (e.g. A, B, S)", role="Role to assign")
    async def setrole(self, interaction: discord.Interaction, tier: str, role: discord.Role):
        await interaction.response.defer(ephemeral=True)
        database.set_tier_role(interaction.guild_id, tier, role.id)
        embed = embeds.tier_role_embed(tier.upper(), role.mention)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unsetrole", description="Remove a tier-to-role mapping.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(tier="Tier name to remove mapping for")
    async def unsetrole(self, interaction: discord.Interaction, tier: str):
        await interaction.response.defer(ephemeral=True)
        database.unset_tier_role(interaction.guild_id, tier)
        embed = discord.Embed(
            title="✅ Mapping Removed",
            description=f"**{tier.upper()}** role mapping has been removed.",
            color=embeds.COLOR_INFO
        )
        embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
        embed.set_footer(text="Celestia")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="roles", description="List all tier-to-role mappings.")
    async def roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        mapping = database.get_tier_roles(interaction.guild_id)
        embed = embeds.tier_roles_list_embed(mapping)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="history", description="Show recent tier evaluation results.")
    async def history(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        results = database.get_tier_results(interaction.guild_id, limit=10)
        if not results:
            embed = discord.Embed(title="📋 Recent Evaluations", description="No results recorded yet.", color=embeds.COLOR_INFO)
            embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
            embed.set_footer(text="Celestia")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        embed = embeds.tier_history_embed(results)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="queue-setup", description="Post the tier test queue panel in a channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel where the queue panel will be posted")
    async def queue_setup(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        embed = embeds.tier_queue_main_embed(interaction.guild)
        view = views.TierQueueView()
        msg = await channel.send(embed=embed, view=view)
        bot_ref = interaction.client
        if hasattr(bot_ref, 'add_view') and callable(bot_ref.add_view):
            bot_ref.add_view(view, message_id=msg.id)
        database.save_guild_config_v3(interaction.guild_id, {
            "tier_queue_channel_id": channel.id,
            "tier_queue_message_id": msg.id
        })
        await interaction.followup.send(f"✅ Tier queue panel posted in {channel.mention}!", ephemeral=True)

    @app_commands.command(name="queue-remove", description="Remove the tier test queue panel and clear config.")
    @app_commands.checks.has_permissions(administrator=True)
    async def queue_remove(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get("tier_queue_channel_id") or not cfg.get("tier_queue_message_id"):
            await interaction.followup.send("❌ No queue panel is configured for this server.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(cfg["tier_queue_channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(cfg["tier_queue_message_id"])
                await msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass
        database.save_guild_config_v3(interaction.guild_id, {
            "tier_queue_channel_id": None,
            "tier_queue_message_id": None
        })
        await interaction.followup.send("✅ Queue panel removed and config cleared.", ephemeral=True)

    @app_commands.command(name="result", description="Submit a tier test result.")
    @is_tier_staff()
    @app_commands.describe(
        player="The player who was tested",
        ign="The player's in-game name",
        previous_tier="Their tier before the test",
        new_tier="Their tier after the test",
        gamemode="The gamemode tested",
        note="Optional note from tester"
    )
    async def result(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        ign: str,
        previous_tier: str,
        new_tier: str,
        gamemode: str = None,
        note: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        database.save_tier_result(
            guild_id=interaction.guild_id,
            user_id=player.id,
            ign=ign,
            previous_tier=previous_tier,
            new_tier=new_tier,
            gamemode=gamemode or '',
            note=note or "No note",
            tester_id=interaction.user.id
        )

        result_data = {
            "user_id": player.id,
            "ign": ign,
            "previous_tier": previous_tier,
            "new_tier": new_tier,
            "gamemode": gamemode or '',
            "note": note or "No note",
            "tester_id": interaction.user.id
        }
        embed = embeds.tier_result_embed(result_data)

        cfg = database.get_guild_config_v3(interaction.guild_id)
        if cfg and cfg['tier_results_channel_id']:
            chan = interaction.guild.get_channel(cfg['tier_results_channel_id'])
            if chan:
                await chan.send(embed=embed)

        await interaction.followup.send(f"✅ Tier result for **{player.display_name}** recorded!", ephemeral=True)

    @result.error
    async def result_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
