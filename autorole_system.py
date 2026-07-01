import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

class AutoroleGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="autorole", description="Auto-role system commands")

    @app_commands.command(name="add", description="Auto-assign a role to new members on join.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to auto-assign")
    async def add(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)

        if role >= interaction.guild.me.top_role:
            await interaction.followup.send(f"❌ `{role.name}` is higher than my top role — I can't assign it.", ephemeral=True)
            return

        current = database.get_autorole_ids(interaction.guild_id)
        if role.id in current:
            await interaction.followup.send(f"⚠️ `{role.name}` is already an auto-role.", ephemeral=True)
            return

        current.append(role.id)
        database.save_autorole_ids(interaction.guild_id, current)

        embed = discord.Embed(
            title="✅ AUTO-ROLE ADDED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**{role.name}** will now be assigned to new members.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_footer(text="SELESTER V3 • Auto-Role System")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="remove", description="Stop auto-assigning a role to new members.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(role="Role to remove from auto-assign")
    async def remove(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)

        current = database.get_autorole_ids(interaction.guild_id)
        if role.id not in current:
            await interaction.followup.send(f"⚠️ `{role.name}` is not an auto-role.", ephemeral=True)
            return

        current.remove(role.id)
        database.save_autorole_ids(interaction.guild_id, current)

        embed = discord.Embed(
            title="✅ AUTO-ROLE REMOVED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**{role.name}** will no longer be auto-assigned.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=embeds.COLOR_AMBER
        )
        embed.set_footer(text="SELESTER V3 • Auto-Role System")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="List all auto-roles for this server.")
    async def list_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        role_ids = database.get_autorole_ids(interaction.guild_id)
        if not role_ids:
            embed = discord.Embed(
                title="📋 AUTO-ROLES",
                description="```\nNo auto-roles configured.\n```\nUse `/autorole add <role>` to add one.",
                color=embeds.COLOR_DARK
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = []
        for rid in role_ids:
            r = interaction.guild.get_role(rid)
            if r:
                lines.append(f"▸ {r.mention} (`{r.name}`)")
            else:
                lines.append(f"▸ `{rid}` (deleted)")

        embed = discord.Embed(
            title="📋 AUTO-ROLES",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━\n" + "\n".join(lines) + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=embeds.COLOR_BLUE
        )
        embed.set_footer(text="SELESTER V3 • Auto-Role System")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def assign_autoroles(member: discord.Member):
    role_ids = database.get_autorole_ids(member.guild.id)
    if not role_ids:
        return

    roles_to_add = []
    for rid in role_ids:
        r = member.guild.get_role(rid)
        if r and r < member.guild.me.top_role:
            roles_to_add.append(r)

    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason="Auto-role on join")
        except:
            pass
