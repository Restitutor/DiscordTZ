import os
from pathlib import Path

import tzlocal


def fetchTimezones() -> list[dict[str, str]]:
    parentDir: str = "/usr/share/zoneinfo/"
    files: list[dict[str, str]] = []
    for root, _dirs, filenames in os.walk(parentDir):
        if ("posix" in root or "right" in root):
            continue
        for filename in filenames:
            relativePath = os.path.relpath(Path(root, filename), parentDir)
            if ("/" in relativePath):
                files.append({"area": relativePath.split("/")[0], "city": relativePath.split("/")[-1].replace("_", " ")})
    return files


localTz = tzlocal.get_localzone().key
timezones: list[dict[str, str]] = fetchTimezones()
checkList: list[str] = [tz["area"] + "/" + tz["city"] for tz in timezones]
