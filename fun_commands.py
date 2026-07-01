import random
import discord
from discord import app_commands
from discord.ext import commands
import embeds

class FunGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="fun", description="Fun commands")

    @app_commands.command(name="say", description="Make the bot say something.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(message="Message to say")
    async def say(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message("✅ Message sent!", ephemeral=True)
        await interaction.channel.send(message)

    @app_commands.command(name="embed", description="Create a custom embed.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(title="Embed title", description="Embed description", color="Hex color (e.g. FF0000)")
    async def embed_cmd(self, interaction: discord.Interaction, title: str, description: str, color: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            clr = int(color, 16) if color else embeds.COLOR_PURPLE
        except:
            clr = embeds.COLOR_PURPLE
        embed = discord.Embed(title=title, description=description, color=clr)
        embed.set_footer(text=f"By {interaction.user.display_name}")
        await interaction.channel.send(embed=embed)
        await interaction.followup.send("✅ Embed sent!", ephemeral=True)

    @app_commands.command(name="poll", description="Create a poll with reactions.")
    @app_commands.describe(question="Poll question", option1="Option 1", option2="Option 2", option3="Option 3 (optional)", option4="Option 4 (optional)")
    async def poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        await interaction.response.defer(ephemeral=True)
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        options = [option1, option2]
        if option3: options.append(option3)
        if option4: options.append(option4)
        lines = [f"{emojis[i]} {opt}" for i, opt in enumerate(options)]
        embed = discord.Embed(title=f"📊 {question}", description="\n\n".join(lines), color=embeds.COLOR_BLUE)
        embed.set_footer(text=f"Poll by {interaction.user.display_name}")
        msg = await interaction.channel.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])
        await interaction.followup.send("✅ Poll created!", ephemeral=True)

    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        embed = discord.Embed(title="🪙 Coin Flip", description=f"You got **{result}**!", color=embeds.COLOR_GOLD)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Roll a dice.")
    @app_commands.describe(sides="Number of sides (default 6)")
    async def dice(self, interaction: discord.Interaction, sides: int = 6):
        if sides < 2 or sides > 100:
            await interaction.response.send_message("❌ Sides must be between 2 and 100.", ephemeral=True)
            return
        result = random.randint(1, sides)
        embed = discord.Embed(title="🎲 Dice Roll", description=f"You rolled a **{result}** (d{sides})!", color=embeds.COLOR_GREEN)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8ball a question.")
    @app_commands.describe(question="Your question")
    async def eightball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        embed = discord.Embed(
            title="🎱 Magic 8Ball",
            description=f"**Q:** {question}\n**A:** {random.choice(responses)}",
            color=embeds.COLOR_PURPLE
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="choose", description="Choose between options.")
    @app_commands.describe(options="Options separated by commas (e.g. pizza, pasta, salad)")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 options separated by commas.", ephemeral=True)
            return
        result = random.choice(choices)
        embed = discord.Embed(title="🤔 I Choose...", description=f"**{result}**", color=embeds.COLOR_GREEN)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="random", description="Get a random number.")
    @app_commands.describe(minimum="Minimum value (default 1)", maximum="Maximum value (default 100)")
    async def random_cmd(self, interaction: discord.Interaction, minimum: int = 1, maximum: int = 100):
        if minimum >= maximum:
            await interaction.response.send_message("❌ Minimum must be less than maximum.", ephemeral=True)
            return
        result = random.randint(minimum, maximum)
        embed = discord.Embed(title="🔢 Random Number", description=f"**{result}** ({minimum}-{maximum})", color=embeds.COLOR_BLUE)
        await interaction.response.send_message(embed=embed)
