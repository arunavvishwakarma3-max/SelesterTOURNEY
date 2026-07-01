import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import database
import embeds

class TicketGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="ticket", description="Support ticket system commands")

    @app_commands.command(name="setup", description="Set up the ticket panel in an existing channel.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Existing channel for the ticket creation panel",
        ticket_category="Existing category where ticket channels will be created",
        support_role="Role that can see/claim tickets"
    )
    async def setup(self, interaction: discord.Interaction, channel: discord.TextChannel, ticket_category: discord.CategoryChannel, support_role: discord.Role):
        await interaction.response.defer(ephemeral=True)

        cfg = database.get_guild_config_v3(interaction.guild_id) or {}
        cfg['ticket_category_id'] = ticket_category.id
        cfg['ticket_support_role_id'] = support_role.id
        database.save_guild_config_v3(interaction.guild_id, cfg)

        embed = embeds.ticket_panel_embed()
        view = TicketPanelView()
        await channel.send(embed=embed, view=view)

        success_embed = discord.Embed(
            title="✅ TICKET SYSTEM ACTIVATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Ticket panel configured in your selected channel.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **Panel Channel:** {channel.mention}\n"
                f"📌 **Ticket Category:** {ticket_category.mention}\n"
                f"👤 **Support Role:** {support_role.mention}\n\n"
                "Users can now click the button in the panel to create tickets."
            ),
            color=embeds.COLOR_GREEN
        )
        success_embed.set_footer(text="SELESTER V3 • Ticket System Online")
        await interaction.followup.send(embed=success_embed, ephemeral=True)

    @app_commands.command(name="panel", description="Post the ticket creation panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = embeds.ticket_panel_embed()
        view = TicketPanelView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send("✅ Ticket panel posted!", ephemeral=True)

    @app_commands.command(name="close", description="Close a ticket channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def close(self, interaction: discord.Interaction):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        if ticket['status'] == 'closed':
            await interaction.response.send_message("❌ This ticket is already closed.", ephemeral=True)
            return
        database.close_general_ticket(ticket['id'])
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

    @app_commands.command(name="add", description="Add a user to the ticket.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(member="Member to add to the ticket")
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
        await interaction.response.send_message(f"✅ Added {member.mention} to this ticket.")

    @app_commands.command(name="remove", description="Remove a user from the ticket.")
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.describe(member="Member to remove from the ticket")
    async def remove(self, interaction: discord.Interaction, member: discord.Member):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(f"✅ Removed {member.mention} from this ticket.")

    @app_commands.command(name="claim", description="Claim a ticket.")
    async def claim(self, interaction: discord.Interaction):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        if ticket['status'] == 'claimed':
            await interaction.response.send_message("❌ This ticket is already claimed.", ephemeral=True)
            return
        database.claim_general_ticket(ticket['id'], interaction.user.id)
        embed = discord.Embed(
            title="✋ Ticket Claimed",
            description=f"{interaction.user.mention} is now handling this ticket.",
            color=embeds.COLOR_AMBER
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="subject", description="Set a subject for the ticket.")
    @app_commands.describe(subject="Ticket subject")
    async def subject(self, interaction: discord.Interaction, subject: str):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)
            return
        await interaction.channel.edit(name=f"ticket-{subject[:20]}")
        await interaction.response.send_message(f"✅ Subject set to: {subject}")

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, row=0, custom_id="create_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        cfg = database.get_guild_config_v3(interaction.guild_id)
        if not cfg or not cfg.get('ticket_category_id'):
            await interaction.followup.send("❌ Ticket system not fully set up.", ephemeral=True)
            return

        category = interaction.guild.get_channel(cfg['ticket_category_id'])
        if not category:
            await interaction.followup.send("❌ Ticket category not found.", ephemeral=True)
            return

        existing = database.get_general_ticket(interaction.channel.id)
        if existing and existing['status'] != 'closed':
            await interaction.followup.send("❌ You already have an open ticket.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if cfg.get('ticket_support_role_id'):
            sr = interaction.guild.get_role(cfg['ticket_support_role_id'])
            if sr:
                overwrites[sr] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        chan_name = f"ticket-{interaction.user.name}"
        clean = "".join(c if (c.isalnum() or c == "-") else "" for c in chan_name).lower()
        try:
            channel = await interaction.guild.create_text_channel(name=clean, category=category, overwrites=overwrites)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create ticket: {e}", ephemeral=True)
            return

        ticket_id = database.create_general_ticket(interaction.guild_id, channel.id, interaction.user.id, "Support")
        embed = discord.Embed(
            title="🎫 TICKET CREATED",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Thank you {interaction.user.mention}! Staff will be with you shortly.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=embeds.COLOR_GREEN
        )
        embed.set_thumbnail(url="https://i.imgur.com/g8o468o.png")
        embed.add_field(name="📝 Instructions", value="Please describe your issue in detail while you wait.", inline=False)
        embed.set_footer(text="SELESTER V3 • Support Ticket")
        view = TicketControlView(ticket_id)
        await channel.send(f"{interaction.user.mention} | <@&{cfg['ticket_support_role_id']}>" if cfg.get('ticket_support_role_id') else f"{interaction.user.mention}", embed=embed, view=view)
        await interaction.followup.send(f"✅ Ticket created! Check {channel.mention}", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_id: int):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, row=0, custom_id="gt_claim", emoji="✋")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket or ticket['status'] != 'open':
            await interaction.response.send_message("❌ This ticket is already claimed or closed.", ephemeral=True)
            return
        database.claim_general_ticket(self.ticket_id, interaction.user.id)
        embed = discord.Embed(title="✋ Ticket Claimed", description=f"{interaction.user.mention} is now handling this.", color=embeds.COLOR_AMBER)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, row=0, custom_id="gt_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket = database.get_general_ticket(interaction.channel.id)
        if not ticket or ticket['status'] == 'closed':
            await interaction.response.send_message("❌ Ticket already closed.", ephemeral=True)
            return
        database.close_general_ticket(self.ticket_id)
        await interaction.response.send_message("🔒 Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass
