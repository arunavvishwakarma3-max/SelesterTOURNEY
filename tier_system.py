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

        database.save_guild_config_v3(interaction.guild_id, data)

        embed = embeds.tier_test_hub_embed()
        view = views.TierGamemodeSelect()
        msg = await tier_channel.send(embed=embed, view=view)
        bot_ref = interaction.client
        if hasattr(bot_ref, 'add_view') and callable(bot_ref.add_view):
            bot_ref.add_view(view, message_id=msg.id)

        success_embed = discord.Embed(
            title="✅ TIER SYSTEM ACTIVATED",
            description=(
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Tier system configured in your selected channels.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Tier Lobby:** {tier_channel.mention}\n"
                f"📌 **Results Channel:** {results_channel.mention}\n"
                f"📌 **Ticket Category:** {ticket_category.mention}\n"
                f"👤 **Staff Role:** {staff_role.mention}\n"
                f"{f'👤 **Tester Role:** {tester_role.mention}' if tester_role else ''}"
            ),
            color=embeds.COLOR_GREEN
        )
        success_embed.set_footer(text="SELESTER V3 • Tier System Online")
        await interaction.followup.send(embed=success_embed, ephemeral=True)

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
        note="Optional note from tester"
    )
    async def result(
        self,
        interaction: discord.Interaction,
        player: discord.Member,
        ign: str,
        previous_tier: str,
        new_tier: str,
        note: str = None
    ):
        await interaction.response.defer(ephemeral=True)

        database.save_tier_result(
            guild_id=interaction.guild_id,
            user_id=player.id,
            ign=ign,
            previous_tier=previous_tier,
            new_tier=new_tier,
            note=note or "No note",
            tester_id=interaction.user.id
        )

        result_data = {
            "user_id": player.id,
            "ign": ign,
            "previous_tier": previous_tier,
            "new_tier": new_tier,
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
