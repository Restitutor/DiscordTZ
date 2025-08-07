import discord
from discord.ext import commands

from modules.TZBot import TZBot


class TzLink(commands.Cog):
    def __init__(this, client: TZBot) -> None:
        this.client = client

    @discord.slash_command(name="link", description="Links you to your Minecraft account.")
    async def link(this, ctx: discord.ApplicationContext, code: discord.Option(str, "Code that was generated for you in Minecraft.")) -> None:
        if this.client.db.getUUIDByUserId(ctx.user.id) is not None:
            failCpy = this.client.fail.copy()
            failCpy.description = "Your account is already linked!"
            await ctx.response.send_message(embed=failCpy, ephemeral=True)
            return

        if code not in this.client.linkCodes:
            failCpy = this.client.fail.copy()
            failCpy.description = "There's no such code! Maybe it expired?"
            await ctx.response.send_message(embed=failCpy, ephemeral=True)
            return

        successCpy = this.client.success.copy()
        entry: tuple[str, str] = this.client.linkCodes.pop(code)
        successCpy.description = f"Your Discord account has been successfully linked with `{entry}`!"
        await ctx.response.send_message(embed=successCpy, ephemeral=True)

        this.client.db.assignUUIDToUserId(entry[0], ctx.user.id, entry[1], ctx.user.name.lower())

    @discord.slash_command(name="unlink", description="Unlinks your Minecraft account.")
    async def unlink(this, ctx: discord.ApplicationContext) -> None:
        if this.client.db.getUUIDByUserId(ctx.user.id) is None:
            failCpy = this.client.fail.copy()
            failCpy.description = "There's nothing to unlink!"
            await ctx.response.send_message(embed=failCpy, ephemeral=True)
            return

        successCpy = this.client.success.copy()
        successCpy.description = "Your Discord account has been successfully unlinked!"
        await ctx.response.send_message(embed=successCpy, ephemeral=True)

        this.client.db.unassignUUIDFromUserId(ctx.user.id)


def setup(client: TZBot) -> None:
    client.add_cog(TzLink(client))
