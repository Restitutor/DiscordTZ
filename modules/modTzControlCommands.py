import datetime

import discord
import pytz
from discord.ext import commands

from modules.TZBot import TZBot
from shared.Timezones import checkList, timezones
from shell.Logger import Logger


async def getTimezones(ctx: discord.AutocompleteContext) -> list[str]:
    maxShowableResults = 25
    result: list[str] = []

    cityMatches = [f"{tz['area']}/{tz['city']}" for tz in timezones if str(tz.get("city", "")).lower().startswith(ctx.value.lower())]
    areaMatches = [f"{tz['area']}/{tz['city']}" for tz in timezones if str(tz.get("area", "")).lower().startswith(ctx.value.lower())]

    for choice in cityMatches[:maxShowableResults]:
        result.append(choice)  # noqa: PERF402

    if len(result) < maxShowableResults:
        for choice in areaMatches:
            if len(result) == maxShowableResults:
                break
            result.append(choice)

    return result


class TzCommands(commands.Cog):
    timezoneGroup = discord.SlashCommandGroup(name="timezone", description="Timezone related stuff")

    def __init__(this, client: TZBot) -> None:
        this.client = client

    @timezoneGroup.command(name="set", description="Sets your timezone to the correct one.")
    async def tzSet(
        this,
        ctx: discord.ApplicationContext,
        timezone: discord.Option(str, "The timezone you are in.", autocomplete=getTimezones),
        tzalias: discord.Option(str, "Alias with which other people will get your time.", required=False, default=None),
    ) -> None:
        if tzalias is None:
            tzalias = ctx.user.name

        if timezone not in checkList:
            Logger.error(f"{ctx.user} tried to set their timezone to {timezone}.")

            await ctx.response.send_message(
                "Invalid timezone. Use [this table](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for reference.", ephemeral=True
            )
            return

        if this.client.db.set(ctx.user.id, timezone, tzalias):
            successCpy = this.client.success.copy()
            successCpy.set_footer(text=ctx.user.name, icon_url=ctx.user.avatar.url)
            successCpy.timestamp = datetime.datetime.now()
            Logger.success(f"{ctx.user} set their timezone to {timezone}!")
            await ctx.response.send_message(embed=successCpy, ephemeral=True)
        else:
            failCpy = this.client.fail.copy()
            failCpy.set_footer(text=ctx.user.name, icon_url=ctx.user.avatar.url)
            failCpy.timestamp = datetime.datetime.now()

            await ctx.response.send_message(embed=failCpy, ephemeral=True)

    @timezoneGroup.command(name="show", description="Shows you timezone you set.")
    async def tzGet(this, ctx: discord.ApplicationContext) -> None:
        res: str | None = this.client.db.getTimeZone(ctx.user.id)

        if res is None:
            failCpy = this.client.fail
            failCpy.set_footer(text=ctx.user.name, icon_url=ctx.user.avatar.url)
            failCpy.timestamp = datetime.datetime.now()

            await ctx.response.send_message(embed=failCpy, ephemeral=True)
        else:
            await ctx.response.send_message(f"Your timezone is {res.replace('_', ' ')}", ephemeral=True)

    @timezoneGroup.command(name="alias", description="Alias when people want to know your time.")
    async def alias(this, ctx: discord.ApplicationContext, tzalias: discord.Option(str, "Alias with which other people will get your time.")) -> None:
        if " " in tzalias:
            await ctx.response.send_message("Aliases can't contain spaces!", ephemeral=True)
            return

        if this.client.db.setAlias(ctx.user.id, tzalias):
            successCpy = this.client.success.copy()
            successCpy.set_footer(text=ctx.user.name, icon_url=ctx.user.avatar.url)
            successCpy.timestamp = datetime.datetime.now()

            await ctx.response.send_message(embed=successCpy, ephemeral=True)
        else:
            failCpy = this.client.fail.copy()
            failCpy.set_footer(text=ctx.user.name, icon_url=ctx.user.avatar.url)
            failCpy.timestamp = datetime.datetime.now()
            failCpy.description = "A user already has this alias!"

            await ctx.response.send_message(embed=failCpy, ephemeral=True)

    @discord.slash_command(name="now", description="Shows person's time.")
    async def now(this, ctx: discord.ApplicationContext, person: discord.Option(discord.Member, "Who's time to display?")) -> None:
        try:
            zoneName = this.client.db.getTimeZone(person.id)
            timezone = pytz.timezone(zoneName)
        except pytz.exceptions.UnknownTimeZoneError:
            await ctx.response.send_message("This person hasn't registered with Timezone Bot yet.", ephemeral=True)
            return

        theirTime = datetime.datetime.now(timezone)

        utcOffset = theirTime.strftime("%z")
        formattedOffset = f"GMT{utcOffset[:3]}:{utcOffset[3:]}"
        timeFormatted = theirTime.strftime(
            f"{person.display_name}'s time: %A, %d.%m.%Y %H:%M | %m/%d/%Y %I:%M %p \
        ({formattedOffset} | {zoneName.replace('_', ' ')})\nYour time: <t:{int(theirTime.timestamp())}:F>"
        )

        await ctx.response.send_message(timeFormatted)

    @discord.slash_command(name="tznow", description="Shows the time in a certain timezone.")
    async def nowTz(this, ctx: discord.ApplicationContext, timezone: discord.Option(str, "Timezone to show", autocomplete=getTimezones)) -> None:
        if timezone not in checkList:
            await ctx.response.send_message(
                "Invalid timezone. Use [this table]\
            (https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for reference.",
                ephemeral=True,
            )

            return

        try:
            zone = pytz.timezone(timezone.replace(" ", "_"))
        except pytz.exceptions.UnknownTimeZoneError:
            await ctx.response.send_message("Timezone not found. Contact <@769924149648424990> for help.", ephemeral=True)
            return

        requestedTime = datetime.datetime.now(zone)
        utcOffset = requestedTime.strftime("%z")
        formattedOffset = f"GMT{utcOffset[:3]}:{utcOffset[3:]}"
        timeFormatted = requestedTime.strftime(
            f"Time in {timezone.split('/')[1].replace('_', ' ')}:\
         %A, %d.%m.%Y %H:%M | %m/%d/%Y %I:%M %p ({formattedOffset})\nYour time: <t:{int(requestedTime.timestamp())}:F>"
        )

        await ctx.response.send_message(timeFormatted)


def setup(client: TZBot) -> None:
    client.add_cog(TzCommands(client))
