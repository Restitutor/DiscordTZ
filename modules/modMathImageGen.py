import asyncio
from pathlib import Path

import discord
from discord.ext import commands

from modules.TZBot import TZBot


class MathImageGen(commands.Cog):
    def __init__(this, client: TZBot) -> None:
        this.client = client

    @discord.slash_command(name="generate", description="Generate an image using math!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def generate(
        this,
        ctx: discord.ApplicationContext,
        r: discord.Option(str, "Math expression for red") = "0",
        g: discord.Option(str, "Math expression for green") = "0",
        b: discord.Option(str, "Math expression for blue") = "0",
    ) -> None:
        if not Path("BMPGen").is_file():
            await ctx.response.send_message("This feature is not available.", ephemeral=True)
            return

        process = await asyncio.create_subprocess_exec(
            "./BMPGen", "-r", f"{r}", "-g", f"{g}", "-b", f"{b}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        if process.returncode != 0:
            await ctx.response.send_message("There was a problem with your expression(s).", ephemeral=True)
            return

        await asyncio.create_subprocess_exec(
            "/usr/bin/magick",
            "output.bmp",
            "-define",
            "png:compression-level=9",
            "-define",
            "png:compression-strategy=1",
            "output.png",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        with open("output.png", "rb") as f:  # noqa: ASYNC230
            await ctx.response.send_message("Here's your picture!", file=discord.File(f))
            Path.unlink(Path("output.bmp"), missing_ok=True)
            Path.unlink(Path("output.png"), missing_ok=True)

    @generate.error
    async def generation_error(this, ctx: discord.ApplicationContext, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            embed = this.client.fail.copy()
            embed.description = "You can run this once every 10 seconds!"

            await ctx.response.send_message(embed=embed, ephemeral=True)


def setup(client: TZBot) -> None:
    client.add_cog(MathImageGen(client))
