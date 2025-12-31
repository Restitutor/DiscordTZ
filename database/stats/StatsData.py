import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Self

import aiofiles
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class StatsData:
    successfulRequestCount: int = 0
    failedRequestCount: int = 0
    requestCountries: dict[str, int] = field(default_factory=dict)
    establishedKnownRequestTypes: dict[str, int] = field(default_factory=dict)
    protocols: dict[str, int] = field(default_factory=dict)
    receivedDataBandwidth: int = 0
    sentDataBandwidth: int = 0

    successfulCommandExecutionCount: int = 0
    failedCommandExecutionCount: int = 0
    ranCommandNames: dict[str, int] = field(default_factory=dict)

    @classmethod
    async def createAll(cls, file: Path) -> tuple[Self, Path]:
        file.parent.mkdir(parents=True, exist_ok=True)

        instance = cls()

        async with aiofiles.open(file, "w") as f:
            await f.write(json.dumps(instance.__dict__))

        return instance, file

    @classmethod
    async def loadStatsAtDate(cls, date: datetime) -> tuple[Self, Path, datetime]:
        statsDir = Path("stats")
        date = date.replace(minute=0, second=0, microsecond=0)
        dateDir = statsDir / f"stats-{date.strftime('%Y-%m-%d')}"
        file = dateDir / f"stats-{date.strftime('%H:00')}.json"

        if not (dateDir.is_dir() and file.is_file()):
            instance, f = await cls.createAll(file)
            return instance, f, date

        async with aiofiles.open(file, "r") as f:
            content = await f.read()
            await f.close()

        if not content.strip():
            instance, f = await cls.createAll(file)
            return instance, f, date

        return cls.schema().loads(content), file, date


    @classmethod
    async def loadBulk(cls, startDate: datetime | None = None, endDate: datetime | None = None) -> list[tuple[datetime, Self]]:
        statsDir = Path("stats")
        batchSize = 50

        if not statsDir.is_dir():
            return []

        if not (startDate or endDate):
            statFileNamePattern = re.compile(r"^stats-(\d{2}:00)\.json$")
            parentDirNamePattern = re.compile(r"^stats-(\d{4}-\d{2}-\d{2})$")

            fileTimeList = []
            for path in statsDir.rglob("*"):
                if (fileMatch := statFileNamePattern.match(path.name)) and (parentMatch := parentDirNamePattern.match(path.parent.name)):
                    fileTimeList.append(datetime.strptime(f"{parentMatch.group(1)} {fileMatch.group(1)}", "%Y-%m-%d %H:%M"))

            timesSorted = sorted(fileTimeList)
            if not startDate:
                startDate = timesSorted[0]
            if not endDate:
                endDate = timesSorted[-1]


        tasks = []
        endDate = endDate.replace(minute=0, second=0, microsecond=0)
        now = startDate.replace(minute=0, second=0, microsecond=0)

        while now <= endDate:
            tasks.append(cls.loadStatsAtDate(now))
            now = now + timedelta(hours=1)

        if len(tasks) > batchSize:
            allResults: list[tuple[Self, Path, datetime]] = []
            for i in range(0, len(tasks), batchSize):
                batch = tasks[i:i + batchSize]
                result = await asyncio.gather(*batch, return_exceptions=False)
                allResults.extend(result)

            returnValue = [(time, data) for data, _, time in allResults]

        else:
            results: list[tuple[Self, Path, datetime]] = await asyncio.gather(*tasks, return_exceptions=False)
            returnValue = [(time, data) for data, _, time in results]

        return sorted(returnValue, key=lambda item: item[0])
