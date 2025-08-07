import asyncio

import discord
from discord.ext import commands

from modules.TZBot import TZBot
from modules.ui.DecisionActionRow import DecisionActionRow
from modules.ui.TzApiRequestUI import TzApiRequestUI


class TzApiKeyManagement(commands.Cog):
    apiGroup = discord.SlashCommandGroup("tzapi", "TZBot API related commands")

    def __init__(this, client: TZBot) -> None:
        this.client = client
        asyncio.create_task(this.client.sync_commands())

    @apiGroup.command(name="requestkey", description="Request a Timezone API key")
    async def request(this, ctx: discord.ApplicationContext) -> None:
        view = TzApiRequestUI(this.client, ctx.user.id)
        await this.client.addOwner(ctx.user.id)

        embed: discord.Embed = discord.Embed(
            color=discord.Color.darker_grey(),
            title="**Terms of Service**",
            description='By using this service, you agree not to abuse request limits or functionality. \
            Any form of request abuse or misuse will result in a permanent ban from accessing the service.\n\
            API usage must remain within intended limits; API abuse is strictly prohibited.\n\
            API keys may be revoked at any time without prior notice or explanation.\n\
            We reserve the right to modify, suspend, or terminate service access at our sole discretion.\n\
            You will receive necessary notifications regarding significant updates, changes, or policy modifications.\n\
            Continued use of the service constitutes acceptance of the most recent TOS.\n\
            Violations may result in immediate suspension or termination of access.\n\
            By clicking "Submit!", I agree to these Terms of Service.',
        )

        await ctx.response.send_message(
            "We need some details about your app and its usage to approve it. Fill the options below.", view=view, embed=embed
        )


def setup(client: TZBot) -> None:
    client.add_view(DecisionActionRow(client))
    for dialogOwner in client.dialogOwners:
        client.add_view(TzApiRequestUI(client, dialogOwner))

    client.add_cog(TzApiKeyManagement(client))
