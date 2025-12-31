import asyncio
import copy
import io
import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Final

import discord
from dataclasses_json import dataclass_json
from discord.ext import bridge
from discord.ext import commands

from database.stats.StatsDatabase import collectCommandStats
from modules.TZBot import TZBot
from shell.Logger import Logger


@dataclass_json
@dataclass
class Profile:
    presence: str = "online"
    activityType: int = -1
    activityName: str = ""


class BotProfile(commands.Cog):
    client: TZBot

    PROFILE_GROUP = discord.SlashCommandGroup(name="profile", description="[Bot Owner] Bot's profile related stuff", checks=[commands.is_owner()])

    PROFILE_FILE: Final[Path] = Path("state/profile.json")
    ACTIVITY_TYPES: Final[list[str]] = ["unknown", "playing", "streaming", "listening", "watching"]
    PRESENCE_TYPES: Final[list[str]] = ["Online", "Offline", "Idle", "DND", "Invisible", "Streaming"]
    PFP_CONTENT_TYPES: Final[set[str]] = {"image/gif", "image/png", "image/jpeg", "image/webp"}

    currentProfile: Profile
    permanentProfile: Profile

    def __init__(this, bot: TZBot):
        if not this.PROFILE_FILE.exists():
            Logger.warning(f"{this.PROFILE_FILE.name} doesn't exist!")
            Logger.log("Falling back to defaults...")
            this.currentProfile = Profile()
            asyncio.create_task(this.saveStatus())
        else:
            with this.PROFILE_FILE.open("r") as f:
                try:
                    this.currentProfile = Profile.schema().loads(f.read())
                except JSONDecodeError as e:
                    Logger.warning(f"Failed to decode {this.PROFILE_FILE.name}: {e}")
                    Logger.log("Falling back to defaults...")
                    this.currentProfile = Profile()

        this.permanentProfile = copy.deepcopy(this.currentProfile)
        this.client = bot

        asyncio.create_task(this.asyncInit())

    async def asyncInit(this):
        await this.reloadPresence()

    async def saveStatus(this):
        with this.PROFILE_FILE.open("w") as f:
            f.write(json.dumps(this.permanentProfile.__dict__))

    async def reloadPresence(this):
        await this.client.change_presence(status=discord.Status(this.currentProfile.presence), activity=discord.Activity(type=discord.ActivityType(this.currentProfile.activityType), name=this.currentProfile.activityName))

    @commands.is_owner()
    @PROFILE_GROUP.command(name="presence", description="[Bot Owner] Change the bot's presence!")
    @collectCommandStats
    async def changePresence(this, ctx: discord.ApplicationContext, presence: discord.Option(str, "Presence to set for the bot", choices=PRESENCE_TYPES), persistent: discord.Option(bool, "If the status stays after restart/cog reload", required=False, default=False)) -> bool:
        presence: str
        if persistent:
            this.permanentProfile.presence = presence.lower()

        this.currentProfile.presence = presence.lower()
        await this.saveStatus()

        await this.reloadPresence()
        await ctx.respond(f"Presence set to {presence}!", ephemeral=True)
        return True

    @commands.is_owner()
    @PROFILE_GROUP.command(name="activity", description="[Bot Owner] Change the bot's activity!")
    @collectCommandStats
    async def changeActivity(this, ctx: discord.ApplicationContext, activitytype: discord.Option(str, "Activity type for the bot", choices=ACTIVITY_TYPES, required=False, default=None), title: discord.Option(str, "The activity body", required=False, default=None), persistent: discord.Option(bool, "If the status stays after restart/cog reload", required=False, default=False)) -> bool:
        if not activitytype and not title:
            await ctx.respond("Either the activity type or the activity title has to be set!")
            return False

        if activitytype:
            if persistent:
                this.permanentProfile.activityType = this.ACTIVITY_TYPES.index(activitytype) - 1
            this.currentProfile.activityType = this.ACTIVITY_TYPES.index(activitytype) - 1

        if title:
            if persistent:
                this.permanentProfile.activityName = title
            this.currentProfile.activityName = title

        await this.saveStatus()
        await this.reloadPresence()
        await ctx.respond(f"Activity set!", ephemeral=True)
        return True

def setup(bot: TZBot):
    bot.add_cog(BotProfile(bot))